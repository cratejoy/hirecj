"""
Proxy routes to the agents service catalog API.
Ensures the agents service remains the single source of truth for persona data.
"""

import httpx
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["catalog-proxy"])


@router.get("/personas")
async def get_personas() -> Dict[str, Any]:
    """
    Proxy to agents service for persona data.
    Transforms the response to match frontend expectations.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Call the agents service catalog API
            response = await client.get(
                f"{settings.agents_service_url}/api/v1/catalog/merchants",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Transform to match frontend expectations
            # The frontend expects: { personas: [{id, name, business, description?}] }
            personas = []
            for merchant in data.get("merchants", []):
                personas.append({
                    "id": merchant["id"],
                    "name": merchant["name"],
                    "business": merchant["business"],
                    "description": merchant.get("description", "")
                })
            
            logger.info(f"Proxied personas request, returning {len(personas)} personas")
            return {"personas": personas}
            
        except httpx.RequestError as e:
            logger.error(f"Failed to reach agents service: {str(e)}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to reach agents service: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Agents service returned error: {e.response.status_code}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Agents service error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error proxying personas request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error proxying request: {str(e)}"
            )


@router.get("/personas/{persona_id}")
async def get_persona(persona_id: str) -> Dict[str, Any]:
    """
    Proxy to agents service for specific persona data.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Call the agents service catalog API
            response = await client.get(
                f"{settings.agents_service_url}/api/v1/catalog/merchants/{persona_id}",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Proxied persona request for {persona_id}")
            return data
            
        except httpx.RequestError as e:
            logger.error(f"Failed to reach agents service: {str(e)}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to reach agents service: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Persona {persona_id} not found"
                )
            logger.error(f"Agents service returned error: {e.response.status_code}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Agents service error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error proxying persona request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error proxying request: {str(e)}"
            )