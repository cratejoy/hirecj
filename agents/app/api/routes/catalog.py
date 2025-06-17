"""
Catalog API endpoints for discovering merchants, scenarios, and workflows.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.conversation_catalog import ConversationCatalog
from app.universe.discovery import UniverseDiscovery
from app.config import settings
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])

# Initialize persona service
persona_service = PersonaService()


@router.get("/merchants")
async def get_merchants() -> Dict[str, Any]:
    """Get all available merchant personas with metadata."""
    return {
        "merchants": persona_service.get_all_personas()
    }


@router.get("/merchants/{merchant_id}")
async def get_merchant(merchant_id: str) -> Dict[str, Any]:
    """Get specific merchant persona details."""
    persona = persona_service.get_persona(merchant_id)
    if not persona:
        raise HTTPException(404, detail=f"Merchant {merchant_id} not found")
    return persona


@router.get("/scenarios")
async def get_scenarios() -> Dict[str, Any]:
    """Get all available business scenarios with metadata."""
    catalog = ConversationCatalog()
    scenarios = catalog.get_scenarios()

    # Convert to API-friendly format
    return {
        "scenarios": [
            {
                "id": key,
                "name": scenario.display_name,
                "stress_level": scenario.stress_level.value,
                "description": scenario.description,
                "key_metrics": scenario.key_metrics,
                "main_challenge": scenario.main_challenge,
                "urgency": scenario.urgency,
            }
            for key, scenario in scenarios.items()
        ]
    }


@router.get("/workflows")
async def get_workflows() -> Dict[str, Any]:
    """Get all available conversation workflows."""
    catalog = ConversationCatalog()
    workflows = catalog.get_workflows()

    # Convert to API-friendly format
    return {
        "workflows": [
            {
                "id": key,
                "name": workflow.display_name,
                "description": workflow.description,
                "typical_turns": workflow.typical_turns,
                "initiator": workflow.initiator,
                "best_for": workflow.best_for,
            }
            for key, workflow in workflows.items()
        ]
    }


@router.get("/universes")
async def get_universes() -> Dict[str, Any]:
    """Get all available universe data combinations."""
    discovery = UniverseDiscovery()

    # Get available combinations
    available = discovery.get_available_combinations()
    merchants_with_data = discovery.get_available_merchants()

    # Build universe info for each combination
    universes = []
    for merchant, scenario in available:
        info = discovery.get_universe_info(merchant, scenario)
        if info:
            universes.append(
                {
                    "merchant": merchant,
                    "scenario": scenario,
                    "generated_at": info["generated_at"],
                    "timeline_days": info["timeline_days"],
                    "current_day": info["current_day"],
                    "total_customers": info["total_customers"],
                    "total_tickets": info["total_tickets"],
                }
            )

    return {
        "total_available": len(available),
        "merchants_with_data": merchants_with_data,
        "universes": universes,
    }


@router.get("/recommendations")
async def get_recommendations() -> Dict[str, Any]:
    """Get recommended conversation combinations."""
    catalog = ConversationCatalog()
    recommendations = catalog.get_recommended_combinations()

    return {"recommendations": recommendations}


@router.get("/cj-versions")
async def get_cj_versions() -> Dict[str, Any]:
    """Get available CJ prompt versions."""
    catalog = ConversationCatalog()
    versions = catalog.get_cj_versions()

    return {
        "versions": [
            {
                "version": version,
                "description": description,
                "is_default": version == settings.default_cj_version,
            }
            for version, description in versions.items()
        ]
    }
