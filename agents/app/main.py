"""Main FastAPI application for HireCJ - Unified API server."""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import settings
from shared.logging_config import setup_logging
from app.models import ConversationRequest, ConversationResponse
from app.services.session_manager import SessionManager
from app.services.message_processor import MessageProcessor
from app.services.conversation_storage import ConversationStorage
from app.prompts import PromptLoader
from app.scenarios import ScenarioLoader
from app.cache_config import setup_litellm_cache, get_cache_info
from app.cache_warming import warm_cache_on_startup
from app.platforms.manager import PlatformManager
from app.platforms.web import WebPlatform
from app.api.routes import catalog as catalog_router
from app.api.routes import universe
from app.api.routes import conversations
from app.api.routes import internal as internal_router
from app.constants import HTTPStatus, WebSocketCloseCodes

# Initialize logging
setup_logging(service_name="agents", level=settings.log_level, log_dir=settings.logs_dir)

# Set environment variables for litellm if they're not already set
if settings.openai_api_key and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.anthropic_api_key and not os.getenv("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="HireCJ API Server",
    description="Unified API for synthetic conversation generation and live chat",
    version="1.0.0",
)

# Build allowed origins from configuration
allowed_origins = [
    settings.frontend_url,
    settings.homepage_url,  # Add homepage_url which is set by tunnel detector
    settings.auth_url,
    # Always allow localhost for development
    "http://localhost:3456",
    "http://localhost:8000", 
    "http://localhost:8103",
    "http://localhost:8002",
]

# Add public URLs if configured
if settings.public_url:
    allowed_origins.append(settings.public_url)

# Add reserved domains if detected
if "hirecj.ai" in settings.frontend_url:
    allowed_origins.extend([
        "https://amir.hirecj.ai",
        "https://amir-auth.hirecj.ai",
    ])

# Also check homepage_url which is set by tunnel detector
if settings.homepage_url and "hirecj.ai" in settings.homepage_url:
    allowed_origins.extend([
        "https://amir.hirecj.ai",
        "https://amir-auth.hirecj.ai",
    ])

# Remove duplicates and empty strings
allowed_origins = list(set(filter(None, allowed_origins)))

# Log CORS configuration for debugging
logger.info("🔧 CORS Configuration:")
logger.info(f"  Frontend URL: {settings.frontend_url}")
logger.info(f"  Homepage URL: {settings.homepage_url}")
logger.info(f"  Public URL: {settings.public_url}")
logger.info(f"  Allowed origins: {allowed_origins}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add user loading middleware (after CORS)
from app.middleware.load_user import LoadUser
app.add_middleware(LoadUser)

# Initialize loaders
prompt_loader = PromptLoader()
scenario_loader = ScenarioLoader()

# Global variables for WebSocket functionality
platform_manager: Optional[PlatformManager] = None
web_platform: Optional[WebPlatform] = None


def validate_critical_resources():
    """Validate that all critical resources exist at startup.
    
    Fails fast with clear error messages if any required resources are missing.
    """
    logger.info("🔍 Validating critical resources...")
    errors = []
    
    # Validate CJ prompt version exists
    try:
        cj_version = settings.default_cj_version
        prompt_loader.load_cj_prompt(cj_version)
        logger.info(f"✅ CJ prompt version '{cj_version}' found")
    except FileNotFoundError as e:
        errors.append(f"CJ prompt missing: {e}")
    except Exception as e:
        errors.append(f"CJ prompt error: {e}")
    
    # Validate fact extraction prompts exist
    fact_prompt_v1_path = Path(settings.prompts_dir) / "fact_extraction.yaml"
    fact_prompt_v2_path = Path(settings.prompts_dir) / "fact_extraction_v2_dedup.yaml"
    
    if not fact_prompt_v1_path.exists():
        errors.append(f"Fact extraction prompt v1 missing: {fact_prompt_v1_path}")
    else:
        logger.info("✅ Fact extraction prompt v1 found")
        
    if not fact_prompt_v2_path.exists():
        errors.append(f"Fact extraction prompt v2 missing: {fact_prompt_v2_path}")
    else:
        logger.info("✅ Fact extraction prompt v2 found")
    
    # Validate merchant personas directory exists
    personas_dir = Path(settings.prompts_dir) / "merchants" / "personas"
    if not personas_dir.exists():
        errors.append(f"Merchant personas directory missing: {personas_dir}")
    else:
        personas = prompt_loader.list_merchant_personas()
        logger.info(f"✅ Found {len(personas)} merchant personas")
    
    # Validate scenarios exist
    scenario_files = [
        Path(settings.prompts_dir) / "scenarios" / "business_scenarios.yaml",
        Path(settings.prompts_dir) / "scenarios" / "normal_business_scenarios.yaml",
    ]
    scenarios_found = False
    for scenario_file in scenario_files:
        if scenario_file.exists():
            scenarios_found = True
            logger.info(f"✅ Scenario file found: {scenario_file.name}")
    
    if not scenarios_found:
        errors.append(f"No scenario files found in {Path(settings.prompts_dir) / 'scenarios'}")
    
    # Validate conversation directory exists
    conversations_dir = Path(settings.conversations_dir)
    if not conversations_dir.exists():
        try:
            conversations_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created conversations directory: {conversations_dir}")
        except Exception as e:
            errors.append(f"Failed to create conversations directory: {e}")
    else:
        logger.info("✅ Conversations directory found")
    
    # Check for required API keys
    if not settings.anthropic_api_key and not settings.openai_api_key:
        errors.append("No LLM API keys configured (need ANTHROPIC_API_KEY or OPENAI_API_KEY)")
    else:
        logger.info("✅ LLM API keys configured")
    
    # If any errors, fail fast
    if errors:
        logger.error("❌ Critical resource validation failed!")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("\nPlease fix these issues before starting the server.")
        raise RuntimeError("Critical resources missing. Server cannot start.")
    
    logger.info("✅ All critical resources validated!")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Initializing HireCJ services...")
    
    # Validate critical resources first
    validate_critical_resources()

    # Setup cache
    setup_litellm_cache()
    cache_info = get_cache_info()
    logger.info(f"📦 Cache configuration: {cache_info}")

    # Initialize WebSocket services
    await initialize_websocket_services()

    # Cache warming
    if settings.enable_cache_warming:
        logger.info("🔥 Starting cache warming...")
        try:
            await warm_cache_on_startup()
        except Exception as e:
            logger.warning(f"Cache warming failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global platform_manager
    if platform_manager:
        await platform_manager.stop_all()


async def initialize_websocket_services():
    """Initialize WebSocket platform manager"""
    global platform_manager, web_platform

    if platform_manager is not None:
        return

    logger.info("Initializing WebSocket services...")

    # Initialize platform manager
    platform_manager = PlatformManager()

    # Setup web platform
    web_config = {
        "max_message_length": settings.max_message_length,
        "session_timeout": settings.session_cleanup_timeout,
    }
    web_platform = WebPlatform(web_config)
    platform_manager.register_platform(web_platform)

    # Connect platform
    await platform_manager.start_all()
    logger.info("WebSocket services initialized")


# ============== Original Conversation Generation Endpoints ==============


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "HireCJ API Server",
        "version": "1.0.0",
        "endpoints": {
            "conversation_generation": "/api/v1/conversations/generate",
            "websocket_chat": "/ws/chat",
            "health": "/health",
            "api_docs": "/docs",
        },
    }


@app.get("/api/v1/test-cors")
async def test_cors():
    """Test endpoint to verify CORS is working"""
    return {
        "status": "ok",
        "message": "CORS is working correctly",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/conversations/generate", response_model=ConversationResponse)
async def generate_conversation(request: ConversationRequest):
    """Generate a synthetic conversation between merchant and CJ"""
    try:
        # Initialize services
        session_manager = SessionManager(
            prompt_loader=prompt_loader, scenario_loader=scenario_loader
        )

        message_processor = MessageProcessor()
        conversation_storage = ConversationStorage()

        # Create session
        session = await session_manager.create_session(
            merchant_name=request.merchant_name,
            scenario_name=request.scenario_name,
            workflow=request.workflow,
            cj_version=request.cj_version,
            merchant_config=request.merchant_config,
            universe_id=request.universe_id,
        )

        # Generate conversation
        messages = []
        for i in range(request.num_turns):
            # Get next message
            message = await message_processor.get_next_message(session)
            messages.append(message)

            # Update session
            await session_manager.update_session(session.session_id, message)

        # Store conversation
        conversation_id = await conversation_storage.store_conversation(
            session=session, messages=messages, metadata=request.metadata
        )

        return ConversationResponse(
            conversation_id=conversation_id,
            messages=messages,
            metadata={
                "merchant": request.merchant_name,
                "scenario": request.scenario_name,
                "workflow": request.workflow,
                "generated_at": datetime.now().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Error generating conversation: {str(e)}")
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/scenarios")
async def list_scenarios():
    """List available scenarios"""
    try:
        scenarios = scenario_loader.list_scenarios()
        return {"scenarios": scenarios, "count": len(scenarios)}
    except Exception as e:
        logger.error(f"Error listing scenarios: {str(e)}")
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/merchants")
async def list_merchants():
    """List available merchants"""
    try:
        # This would typically come from a database or config
        merchants = ["zoe_martinez", "marcus_thompson", "sarah_chen"]
        return {"merchants": merchants, "count": len(merchants)}
    except Exception as e:
        logger.error(f"Error listing merchants: {str(e)}")
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/universes")
async def list_universes():
    """List available universes"""
    try:
        from app.universe.loader import UniverseLoader

        loader = UniverseLoader()
        universes = []

        # Get all universe files
        import os

        universe_dir = "data/universes"
        if os.path.exists(universe_dir):
            for file in os.listdir(universe_dir):
                if file.endswith(".yaml"):
                    universe_id = file.replace(".yaml", "")
                    try:
                        universe = loader.load(universe_id)
                        metadata = universe.get("metadata", {})
                        universes.append(
                            {
                                "id": universe_id,
                                "merchant": metadata.get("merchant_name", "unknown"),
                                "scenario": metadata.get("scenario_name", "unknown"),
                                "created_at": metadata.get("created_at", "unknown"),
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load universe {universe_id}: {e}")

        return {"universes": universes, "count": len(universes)}
    except Exception as e:
        logger.error(f"Error listing universes: {str(e)}")
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/cj-versions")
async def list_cj_versions():
    """List available CJ versions"""
    return {
        "versions": ["v6.0.1", "v6.0.0", "v5.0.0", "v4.0.0"],
        "default": settings.default_cj_version,
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "cache": get_cache_info(),
            "conversation_generation": "operational",
            "websocket_chat": (
                "operational"
                if web_platform and web_platform.is_connected
                else "not_connected"
            ),
        },
    }


# ============== WebSocket Chat Endpoints ==============


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for live chat"""
    logger.info("New WebSocket connection")

    await websocket.accept()

    # Use the web platform to handle the connection
    global web_platform
    if web_platform:
        await web_platform.handle_websocket_connection(websocket)
    else:
        await websocket.close(
            code=WebSocketCloseCodes.INTERNAL_ERROR, reason="Service unavailable"
        )


@app.get("/ws-test")
async def websocket_test_page():
    """Serve WebSocket test page"""
    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html>
<head>
    <title>HireCJ WebSocket Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .section { margin: 20px 0; padding: 10px; border: 1px solid #ddd; }
        .log { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; background: #f5f5f5; font-family: monospace; font-size: 12px; }
        button { margin: 5px; padding: 5px 10px; }
        input, select { margin: 5px; padding: 5px; }
        .connected { color: green; }
        .disconnected { color: red; }
        .message { margin: 5px 0; padding: 5px; }
        .sent { background: #e3f2fd; }
        .received { background: #f1f8e9; }
        .error { background: #ffebee; color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h1>HireCJ WebSocket Test</h1>

        <div class="section">
            <h2>Connection</h2>
            <p>Status: <span id="status" class="disconnected">Disconnected</span></p>
            <button onclick="connect()">Connect</button>
            <button onclick="disconnect()">Disconnect</button>
        </div>

        <div class="section">
            <h2>Start Conversation</h2>
            <select id="merchantId">
                <option value="zoe_martinez">Zoe Martinez</option>
                <option value="marcus_thompson">Marcus Thompson</option>
            </select>
            <select id="scenario">
                <option value="memorial_day_weekend">Memorial Day Weekend</option>
                <option value="steady_operations">Steady Operations</option>
                <option value="growth_stall">Growth Stall</option>
                <option value="churn_spike">Churn Spike</option>
            </select>
            <select id="workflow">
                <option value="daily_briefing">Daily Briefing</option>
                <option value="weekly_review">Weekly Review</option>
                <option value="ad_hoc_support">Ad Hoc Support</option>
            </select>
            <button onclick="startConversation()">Start Conversation</button>
        </div>

        <div class="section">
            <h2>Send Message</h2>
            <input type="text" id="messageText" placeholder="Type your message" style="width: 400px;">
            <button onclick="sendMessage()">Send Message</button>
        </div>

        <div class="section">
            <h2>Fact Check</h2>
            <input type="number" id="messageIndex" placeholder="Message Index" value="0">
            <button onclick="sendFactCheck()">Request Fact Check</button>
        </div>

        <div class="section">
            <h2>Message Log</h2>
            <button onclick="clearLog()">Clear Log</button>
            <div id="log" class="log"></div>
        </div>
    </div>

    <script>
        let ws = null;
        let messageCount = 0;

        function log(message, type = 'info') {
            const logDiv = document.getElementById('log');
            const timestamp = new Date().toLocaleTimeString();
            const div = document.createElement('div');
            div.className = `message ${type}`;
            div.innerHTML = `[${timestamp}] ${message}`;
            logDiv.appendChild(div);
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function clearLog() {
            document.getElementById('log').innerHTML = '';
            messageCount = 0;
        }

        function updateStatus(connected) {
            const status = document.getElementById('status');
            status.textContent = connected ? 'Connected' : 'Disconnected';
            status.className = connected ? 'connected' : 'disconnected';
        }

        function connect() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                log('Already connected', 'error');
                return;
            }

            const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/chat`;

            log(`Connecting to ${wsUrl}...`, 'sent');
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                log('WebSocket connected', 'received');
                updateStatus(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    log(`Received: ${JSON.stringify(data, null, 2)}`, 'received');

                    // Handle specific message types
                    if (data.type === 'cj_message' && data.message) {
                        messageCount++;
                        log(`CJ Message #${messageCount}: ${data.message.substring(0, 200)}...`, 'received');
                    }
                } catch (e) {
                    log(`Raw message: ${event.data}`, 'received');
                }
            };

            ws.onerror = (error) => {
                log(`WebSocket error: ${error}`, 'error');
            };

            ws.onclose = (event) => {
                log(`WebSocket closed: Code ${event.code}, Reason: ${event.reason}`, 'error');
                updateStatus(false);
                ws = null;
            };
        }

        function disconnect() {
            if (ws) {
                ws.close();
                ws = null;
            }
        }

        function startConversation() {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                log('Not connected', 'error');
                return;
            }

            const data = {
                type: 'start_conversation',
                data: {
                    merchant_id: document.getElementById('merchantId').value,
                    scenario: document.getElementById('scenario').value,
                    workflow: document.getElementById('workflow').value
                }
            };

            log(`Sending: ${JSON.stringify(data, null, 2)}`, 'sent');
            ws.send(JSON.stringify(data));
        }

        function sendMessage() {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                log('Not connected', 'error');
                return;
            }

            const text = document.getElementById('messageText').value;
            if (!text) {
                log('Please enter a message', 'error');
                return;
            }

            const data = {
                type: 'message',
                text: text
            };

            log(`Sending: ${JSON.stringify(data, null, 2)}`, 'sent');
            ws.send(JSON.stringify(data));
            document.getElementById('messageText').value = '';
        }

        function sendFactCheck() {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                log('Not connected', 'error');
                return;
            }

            const messageIndex = parseInt(document.getElementById('messageIndex').value);
            const data = {
                type: 'fact_check',
                data: { messageIndex: messageIndex }
            };

            log(`Sending: ${JSON.stringify(data, null, 2)}`, 'sent');
            ws.send(JSON.stringify(data));
        }

        // Enter key sends message
        document.getElementById('messageText').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
    """
    )


# ============== API Routes ==============

# Include route modules
app.include_router(catalog_router.router)
app.include_router(universe.router)
app.include_router(conversations.router)
app.include_router(internal_router.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
