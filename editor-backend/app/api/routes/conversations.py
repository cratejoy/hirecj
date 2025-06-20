"""
Proxy routes for conversation capture to the agents service.
Enables the editor to capture conversations for evaluation purposes.
"""

import httpx
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.post("/capture")
async def proxy_capture(request: Request) -> Dict[str, Any]:
    """
    Proxy conversation capture requests to the agents service.
    
    The agents service handles the actual file storage and organization
    of captured conversations for evaluation purposes.
    """
    try:
        # Get the request body
        body = await request.json()
        
        logger.info(f"Proxying conversation capture request for conversation: {body.get('conversation', {}).get('id', 'unknown')}")
        
        async with httpx.AsyncClient() as client:
            # Forward to agents service with a longer timeout for file operations
            response = await client.post(
                f"{settings.agents_service_url}/api/v1/conversations/capture",
                json=body,
                timeout=30.0
            )
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"Agents service returned error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to capture conversation: {response.text}"
                )
            
            result = response.json()
            logger.info(f"Successfully captured conversation: {result.get('id')} to {result.get('path')}")
            
            return result
            
    except httpx.RequestError as e:
        logger.error(f"Failed to reach agents service: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach agents service: {str(e)}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from agents service: {str(e)}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Agents service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in conversation capture proxy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to capture conversation: {str(e)}"
        )