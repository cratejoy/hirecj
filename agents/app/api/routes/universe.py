"""
Universe management API endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pathlib import Path
import yaml

from app.universe.loader import UniverseLoader
from app.conversation_catalog import ConversationCatalog
from app.logging_config import get_logger
from app.constants import HTTPStatus

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/universes", tags=["universes"])


@router.get("/", response_model=List[Dict[str, Any]])
async def list_universes():
    """List all available universes with their metadata."""
    universe_dir = Path("data/universes")
    universes = []

    if universe_dir.exists():
        for universe_file in universe_dir.glob("*.yaml"):
            # Parse filename to extract merchant and scenario
            # Format: merchant_scenario_v1.yaml
            parts = universe_file.stem.split("_")
            if len(parts) >= 3 and parts[-1].startswith("v"):
                version = parts[-1]
                scenario_parts = parts[:-1]

                # Find the split between merchant and scenario
                # This is tricky because both can have underscores
                # Use catalog to help identify valid merchants
                catalog = ConversationCatalog()
                merchant_names = list(catalog.get_personas().keys())

                merchant = None
                scenario = None

                # Try to match merchant name
                for i in range(1, len(scenario_parts) + 1):
                    potential_merchant = "_".join(scenario_parts[:i])
                    if potential_merchant in merchant_names:
                        merchant = potential_merchant
                        scenario = "_".join(scenario_parts[i:])
                        break

                if merchant and scenario:
                    # Load universe to get metadata
                    try:
                        with open(universe_file, "r") as f:
                            universe_data = yaml.safe_load(f)

                        universes.append(
                            {
                                "merchant": merchant,
                                "scenario": scenario,
                                "version": version,
                                "filename": universe_file.name,
                                "business_context": universe_data.get(
                                    "business_context", {}
                                ),
                                "total_customers": len(
                                    universe_data.get("customers", [])
                                ),
                                "total_tickets": len(
                                    universe_data.get("support_tickets", [])
                                ),
                                "days": universe_data.get("metadata", {}).get(
                                    "days", 90
                                ),
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error loading universe {universe_file}: {e}")

    return universes


@router.get("/{merchant}/{scenario}", response_model=Dict[str, Any])
async def get_universe_info(merchant: str, scenario: str):
    """Get detailed information about a specific universe."""
    try:
        loader = UniverseLoader()
        universe = loader.load_by_merchant_scenario(merchant, scenario)

        return {
            "merchant": merchant,
            "scenario": scenario,
            "exists": True,
            "business_context": universe.get("business_context", {}),
            "metadata": universe.get("metadata", {}),
            "total_customers": len(universe.get("customers", [])),
            "total_tickets": len(universe.get("support_tickets", [])),
            "metrics": {
                "mrr": universe.get("business_context", {})
                .get("current_state", {})
                .get("mrr", 0),
                "csat_score": universe.get("business_context", {})
                .get("current_state", {})
                .get("csat_score", 0),
                "churn_rate": universe.get("business_context", {})
                .get("current_state", {})
                .get("churn_rate", 0),
            },
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Universe not found for {merchant}/{scenario}. Please generate it first.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error loading universe: {str(e)}",
        )


@router.post("/generate", response_model=Dict[str, Any])
async def generate_universe(request: Dict[str, Any]):
    """Generate a new universe (placeholder for now)."""
    merchant = request.get("merchant")
    scenario = request.get("scenario")

    if not merchant or not scenario:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Both merchant and scenario are required",
        )

    # Universe generation is handled via CLI for complex universe creation
    return {
        "status": "not_implemented",
        "message": f"Universe generation for {merchant}/{scenario} is not yet implemented. Please use the CLI: python scripts/generate_universe.py --merchant {merchant} --scenario {scenario}",
    }


@router.get("/check/{merchant}/{scenario}", response_model=Dict[str, bool])
async def check_universe_exists(merchant: str, scenario: str):
    """Quick check if a universe exists."""
    loader = UniverseLoader()
    try:
        loader.load_by_merchant_scenario(merchant, scenario)
        return {"exists": True}
    except FileNotFoundError:
        return {"exists": False}
