# HireCJ Agents

FastAPI backend for HireCJ - the AI customer support agent with intelligent conversation management and merchant memory.

## 🏗️ Architecture Overview

This service implements a sophisticated agent architecture with two distinct usage patterns:

### 1. Direct CJ Agent (Internal Server)
- **Module**: `app.agents.cj_agent`
- **Used by**: Server components (MessageProcessor)
- **Purpose**: Actual CJ agent implementation using CrewAI
- **Features**: Full agent capabilities, tool access, merchant memory integration

### 2. API Adapter (External Clients)
- **Module**: `app.agents.api_adapter`
- **Used by**: Scripts, demos, external clients
- **Purpose**: CrewAI-compatible interface that routes through WebSocket API
- **Benefits**: Centralized session management, persistence, consistent behavior

### Message Flow Architecture

```
External Clients (scripts/web/demos)
    ↓
API Adapter (mimics CrewAI interface)
    ↓
WebSocket Connection (/ws/chat/{conversation_id})
    ↓
API Server (WebPlatform)
    ↓
SessionManager (loads universe data & merchant memory)
    ↓
MessageProcessor
    ↓
Direct CJ Agent (actual implementation)
    ↓
Response via WebSocket
```

### Key Design Decisions

1. **Separation of Concerns**: External clients never directly instantiate CJ agents
2. **Session Management**: All state (including merchant memory) managed server-side
3. **Backward Compatibility**: Scripts using CrewAI interface work unchanged
4. **Single Source of Truth**: One session, one state, managed by the server
5. **Prompt Transparency**: No runtime prompt mutations - all behavior visible in static YAML files

## 🔐 User Identity Management

**CRITICAL: Backend is the SOLE AUTHORITY for user identity generation**

### The Pattern
1. **Frontend**: Sends only raw data (`shop_domain`, `merchant_id`)
2. **Backend**: Generates user IDs using `shared.user_identity.get_or_create_user()`
3. **Format**: All user IDs follow pattern `usr_xxxxxxxx` (8-char hex from SHA256)

### Where User IDs are Generated
- **OAuth Callback** (auth service): When merchant completes Shopify OAuth
- **start_conversation** (agents service): When session begins with shop_domain
- **oauth_complete** (agents service): When OAuth completion is reported

### Common Mistakes to Avoid
```python
# ❌ WRONG - Never generate IDs manually
user_id = f"shop_{shop_domain.replace('.myshopify.com', '')}"  # NO!
user_id = f"user_{merchant_id}"  # NO!

# ✅ CORRECT - Always use the authoritative function
from shared.user_identity import get_or_create_user
user_id, is_new = get_or_create_user(shop_domain)
```

### Frontend Guidelines
- NEVER attempt to generate user IDs
- Store only `merchantId` and `shopDomain` in localStorage
- Send these raw values to backend via `session_update`
- Backend will handle all ID generation and user creation

## 🎯 Prompt Transparency Principle

**Critical for Debuggability**: All CJ behavior must be understandable by reading static files. No hidden prompt mutations at runtime.

### What CJ Sees
CJ's complete prompt consists of exactly two parts:
1. **Base Prompt**: `agents/prompts/cj/versions/v{version}.yaml` - Core identity and principles
2. **Workflow Prompt**: `agents/prompts/workflows/{workflow}.yaml` - Workflow-specific instructions

### The Golden Rules
✅ **DO**: 
- Put all instructions in YAML files
- Use simple template variable substitution ({merchant_name}, {workflow_name})
- Keep base + workflow separation clear
- Make system event handling visible in workflow YAML

❌ **DON'T**:
- Dynamically modify prompts at runtime
- Inject hidden context that's not in YAML files
- Use complex conditional logic to build prompts
- Hide behavior in code instead of prompts

### Example: System Events
Instead of complex code to handle OAuth completion, we simply add to the workflow YAML:
```yaml
SYSTEM EVENT HANDLING:
When you receive a message from sender "system":
  For "New Shopify merchant authenticated from [store]":
    - Respond: "Perfect! I've connected to [store]..."
```

This principle ensures developers can always understand CJ's behavior by reading two YAML files.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment

### Installation
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install
```

### Running the Server

#### Development with Hot Reload (Recommended)
```bash
make dev
```
This starts the server with automatic hot reload - any changes to Python files will automatically restart the server.

#### Development without Hot Reload
If hot reload causes issues (e.g., with certain async operations):
```bash
make dev-noreload
```

#### Production
```bash
make run
```

### Key Features
- **Hot Reload**: The development server automatically restarts when you modify Python files
- **Debug Logging**: Development mode enables DEBUG level logging
- **Port**: Server runs on http://localhost:8000
- **API Docs**: Available at http://localhost:8000/docs

### Stopping the Server
```bash
make stop
```

### Testing
```bash
# Run all tests
make test

# Run Python tests only
make test-python

# Run YAML behavioral tests
make test-cj
```

## 📁 Project Structure
```
app/
├── agents/         # Agent implementations
│   ├── cj_agent.py         # Direct CJ agent (server-side)
│   ├── api_adapter.py      # API adapter for external clients
│   ├── merchant_agent.py   # Merchant simulation agent
│   └── universe_data_agent.py  # Universe data access
├── api/           # REST API endpoints
├── platforms/     # Platform integrations
│   └── web_platform.py     # WebSocket handler
├── services/      # Core services
│   ├── session_manager.py  # Session lifecycle management
│   ├── message_processor.py # Message handling with CJ
│   ├── merchant_memory.py  # Merchant memory persistence
│   └── conversation_storage.py # Conversation persistence
├── models.py      # Data models
├── config.py      # Configuration
└── main.py        # FastAPI application

data/
├── merchant_memory/  # Persistent merchant facts (YAML)
├── conversations/    # Conversation history (JSON)
└── universe/        # Scenario-specific universe data
```

## 🎯 Usage Patterns

### For Web Interface Users
The web interface automatically uses the WebSocket API. Sessions are managed server-side with proper memory and universe data loading.

### For Script Writers
Always use the API adapter for external scripts:
```python
# ✅ Correct - Uses API adapter
from app.agents.api_adapter import create_cj_agent, Crew, Task

# ❌ Wrong - Direct import only for server internals
from app.agents.cj_agent import create_cj_agent
```

### For Server Development
When working on server components (MessageProcessor, etc.), use direct imports:
```python
# Server-side code uses direct agent
from app.agents.cj_agent import create_cj_agent
```

## 🧠 Merchant Memory

The system maintains persistent memory about each merchant across conversations:

### How It Works
1. **Automatic Loading**: Memory loads when a session starts
2. **Fact Accumulation**: Facts extracted from conversations (Phase 8-9, coming soon)
3. **Context Injection**: Facts included in CJ's context (Phase 7, in progress)
4. **Persistence**: YAML files in `data/merchant_memory/`

### Memory Architecture
```
Session Creation
    ↓
SessionManager loads MerchantMemory
    ↓
MessageProcessor passes memory to CJ Agent
    ↓
CJ Agent uses facts in responses (Phase 7)
    ↓
FactExtractor extracts new facts (Phase 8-9)
    ↓
Memory saved to disk
```

## 📊 Analytics Capabilities

The support_daily workflow includes comprehensive analytics tools for support operations:

### Available Analytics
1. **Daily Snapshot**: Comprehensive daily metrics (volume, response times, CSAT, SLA)
2. **CSAT Analysis**: Deep dive into ratings with full conversation history
3. **Backlog Monitoring**: Age distribution and oldest ticket identification
4. **Response Metrics**: Statistical analysis with percentiles and outliers
5. **Volume Trends**: Spike detection and trend analysis over time
6. **SLA Tracking**: Breach identification and pattern analysis
7. **Root Cause Analysis**: Understand drivers behind ticket spikes

### Example Usage
```python
# Daily health check
"Give me yesterday's support metrics"
→ Returns volume, response times, CSAT scores, SLA breaches

# Investigate dissatisfaction  
"Show me bad CSAT ratings with full conversations"
→ Returns ratings with complete interaction history

# Monitor performance
"Analyze our response times for the past week"
→ Returns statistical breakdown with CSAT correlation

# Detect anomalies
"What caused the spike in tickets on May 26th?"
→ Returns tag analysis, example tickets, insights
```

### Key Features
- **Real-time Analysis**: All metrics computed from live database
- **Merchant Isolation**: Data strictly filtered by merchant_id
- **Conversation Context**: Optional full conversation history for CSAT analysis
- **Statistical Insights**: Automated spike detection, trend analysis
- **Actionable Output**: Prioritized issues and recommendations

For detailed scenarios and examples, see [Analytics Scenarios Guide](docs/ANALYTICS_SCENARIOS.md).

### SQLAlchemy Best Practices

When working with database models and SQLAlchemy in this codebase, follow these critical guidelines:

#### 1. **Keep Models Thin**
Models should be data containers with minimal logic. They define schema and basic properties only.

**✅ GOOD - What belongs in models:**
```python
class FreshdeskTicket(Base):
    __tablename__ = 'freshdesk_tickets'
    
    # Column definitions
    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, nullable=False, index=True)
    status = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True))
    
    # Relationships
    conversations = relationship("FreshdeskConversation", back_populates="ticket")
    
    # Simple properties
    @property
    def is_resolved(self):
        return self.status in [4, 5]
    
    @property
    def age_days(self):
        if self.created_at:
            return (datetime.utcnow() - self.created_at).days
        return 0
```

**❌ BAD - What does NOT belong in models:**
```python
class FreshdeskTicket(Base):
    # ❌ Never import from lib modules
    from app.lib.analytics import calculate_metrics
    
    # ❌ No business logic methods
    def calculate_sla_breach(self):
        from app.lib.sla_calculator import check_breach
        return check_breach(self)
    
    # ❌ No session creation
    def get_related_tickets(self):
        with get_db_session() as session:  # NO!
            return session.query(FreshdeskTicket)...
    
    # ❌ No external API calls
    def sync_with_freshdesk(self):
        response = requests.get(...)  # NO!
```

#### 2. **Session Management**
Proper session handling is critical for performance and data consistency.

**✅ GOOD Patterns:**
```python
# Pass sessions down through function calls
def get_ticket_analytics(session: Session, merchant_id: int):
    tickets = session.query(FreshdeskTicket).filter(
        FreshdeskTicket.merchant_id == merchant_id
    ).all()
    return analyze_tickets(session, tickets)

# Use context managers at the entry point
def handle_request():
    with get_db_session() as session:
        result = get_ticket_analytics(session, merchant_id)
        session.commit()  # Explicit commits when needed
        return result

# Bulk operations in a single session
def process_tickets(session: Session, ticket_ids: List[int]):
    tickets = session.query(FreshdeskTicket).filter(
        FreshdeskTicket.id.in_(ticket_ids)
    ).all()
    
    for ticket in tickets:
        ticket.processed = True
    
    session.commit()  # One commit for all changes
```

**❌ BAD Patterns:**
```python
# ❌ Creating sessions inside library functions
def get_ticket_analytics(merchant_id: int):
    with get_db_session() as session:  # NO! Session should be passed in
        return session.query(...)

# ❌ Multiple session creates/commits
def process_tickets(ticket_ids: List[int]):
    for ticket_id in ticket_ids:
        with get_db_session() as session:  # NO! Creates N sessions
            ticket = session.query(...).first()
            ticket.processed = True
            session.commit()  # N commits!

# ❌ Implicit session access in models
class Ticket(Base):
    def get_conversations(self):
        session = inspect(self).session  # NO! Anti-pattern
        return session.query(...)
```

#### 3. **Query Patterns & Optimization**

**Data Isolation (CRITICAL):**
```python
# ✅ ALWAYS filter by merchant_id first
tickets = session.query(FreshdeskTicket).filter(
    FreshdeskTicket.merchant_id == merchant_id,  # First filter!
    FreshdeskTicket.status == 2
).all()

# ✅ Use indexed columns in WHERE clauses
# Make sure merchant_id, status, created_at are indexed
```

**Eager Loading to Prevent N+1:**
```python
# ✅ Load relationships upfront
tickets = session.query(FreshdeskTicket).options(
    joinedload(FreshdeskTicket.conversations),
    joinedload(FreshdeskTicket.ratings)
).filter(
    FreshdeskTicket.merchant_id == merchant_id
).all()

# Now accessing ticket.conversations won't trigger new queries
```

**Efficient Aggregations:**
```python
# ✅ Use database aggregations
from sqlalchemy import func

stats = session.query(
    func.count(FreshdeskTicket.id).label('total'),
    func.avg(FreshdeskTicket.resolution_time).label('avg_resolution')
).filter(
    FreshdeskTicket.merchant_id == merchant_id
).first()

# ❌ Don't aggregate in Python
tickets = session.query(FreshdeskTicket).all()
total = len(tickets)  # NO! Use COUNT in query
avg = sum(t.resolution_time for t in tickets) / len(tickets)  # NO!
```

**Batch Operations:**
```python
# ✅ Bulk inserts
session.bulk_insert_mappings(FreshdeskTicket, [
    {"merchant_id": 1, "subject": "Issue 1"},
    {"merchant_id": 1, "subject": "Issue 2"},
])

# ✅ Bulk updates
session.query(FreshdeskTicket).filter(
    FreshdeskTicket.merchant_id == merchant_id,
    FreshdeskTicket.created_at < cutoff_date
).update({"archived": True})
```

#### 4. **Transaction Management**

```python
# ✅ Explicit transaction control
def transfer_tickets(session: Session, from_merchant: int, to_merchant: int):
    try:
        # All operations in one transaction
        tickets = session.query(FreshdeskTicket).filter(
            FreshdeskTicket.merchant_id == from_merchant
        ).all()
        
        for ticket in tickets:
            ticket.merchant_id = to_merchant
        
        session.commit()
    except Exception as e:
        session.rollback()
        raise

# ✅ Use savepoints for nested transactions
def complex_operation(session: Session):
    with session.begin_nested():  # Savepoint
        try:
            risky_operation(session)
        except SpecificError:
            # Only rolls back to savepoint
            pass
```

#### 5. **Common Anti-Patterns to Avoid**

```python
# ❌ Lazy loading in loops
for ticket in tickets:
    print(ticket.conversations)  # Each triggers a query!

# ❌ Loading entire objects for single fields
tickets = session.query(FreshdeskTicket).all()
ids = [t.id for t in tickets]  # Loaded entire objects for just IDs

# ✅ Better: Query only what you need
ids = session.query(FreshdeskTicket.id).all()

# ❌ Using model instances after session close
def get_ticket():
    with get_db_session() as session:
        return session.query(FreshdeskTicket).first()

ticket = get_ticket()
print(ticket.conversations)  # Error! Session closed

# ✅ Better: Return data, not model instances
def get_ticket_data():
    with get_db_session() as session:
        ticket = session.query(FreshdeskTicket).first()
        return {
            "id": ticket.id,
            "conversations": [{"id": c.id} for c in ticket.conversations]
        }
```

#### 6. **Testing Considerations**

```python
# ✅ Use transactions in tests that rollback
class TestCase:
    def setUp(self):
        self.session = get_db_session()
        self.trans = self.session.begin_nested()
    
    def tearDown(self):
        self.trans.rollback()
        self.session.close()

# ✅ Use factories for test data
def create_test_ticket(session, **kwargs):
    defaults = {
        "merchant_id": 1,
        "status": 2,
        "subject": "Test Ticket"
    }
    defaults.update(kwargs)
    ticket = FreshdeskTicket(**defaults)
    session.add(ticket)
    session.flush()
    return ticket
```

#### 7. **Performance Tips**

1. **Index Strategy**: Always index columns used in WHERE, ORDER BY, and JOIN
2. **Query Logging**: Enable SQL logging in development to spot inefficiencies
3. **Connection Pooling**: Configure appropriate pool size for your workload
4. **Batch Size**: Use reasonable batch sizes (100-1000) for bulk operations
5. **Query Complexity**: Sometimes 2 simple queries are better than 1 complex join

Remember: The database is powerful - let it do the heavy lifting. Don't retrieve data just to filter/aggregate in Python!

## 🔧 Configuration
See `app/config.py` for all configuration options. Key environment variables:
- `LOG_LEVEL`: Logging level (default: INFO, dev: DEBUG)
- `API_HOST`: Host to bind to (default: 0.0.0.0)
- `API_PORT`: Port to bind to (default: 8000)
- `HIRECJ_API_URL`: WebSocket URL for API adapter (default: ws://localhost:8000)

## 🏛️ Architectural Principles

### North Star Principles
1. **Simplify**: One way to do things, no alternatives
2. **No Cruft**: Remove redundant code and complexity
3. **Break & Fix Right**: No compatibility shims
4. **Long-term Elegance**: Performant, type-safe solutions
5. **Backend-Driven**: Server handles complexity
6. **Single Source of Truth**: One session, one state

### Why Two CJ Agent Interfaces?
- **Not technical debt**: This is intentional architecture
- **External access**: Always through API for proper state management
- **Internal processing**: Direct agent for efficiency
- **Benefits**: Centralized sessions, persistence, consistency
