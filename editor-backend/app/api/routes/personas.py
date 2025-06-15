"""
User persona management API endpoints.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/personas", tags=["personas"])

# Path to personas directory
PERSONAS_DIR = Path(settings.personas_dir)


class PersonaListResponse(BaseModel):
    """Response containing list of personas"""
    personas: List[Dict[str, Any]]


class PersonaResponse(BaseModel):
    """Response containing persona details"""
    id: str
    name: str
    description: str
    data: Dict[str, Any]


class PersonaCreateRequest(BaseModel):
    """Request to create a new persona"""
    name: str
    description: str
    data: Dict[str, Any]


@router.get("/", response_model=PersonaListResponse)
async def list_personas():
    """List all available user personas."""
    try:
        if not PERSONAS_DIR.exists():
            logger.warning(f"Personas directory not found: {PERSONAS_DIR}")
            return PersonaListResponse(personas=[])
        
        personas = []
        yaml_files = list(PERSONAS_DIR.glob("*.yaml"))
        
        for file in yaml_files:
            try:
                with open(file, 'r') as f:
                    data = yaml.safe_load(f)
                    personas.append({
                        "id": file.stem,
                        "name": data.get("name", file.stem),
                        "description": data.get("description", ""),
                    })
            except Exception as e:
                logger.warning(f"Error reading persona file {file}: {e}")
        
        logger.info(f"Found {len(personas)} personas")
        return PersonaListResponse(personas=personas)
        
    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list personas"
        )


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str):
    """Get details of a specific persona."""
    try:
        persona_file = PERSONAS_DIR / f"{persona_id}.yaml"
        
        if not persona_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Persona {persona_id} not found"
            )
        
        with open(persona_file, 'r') as f:
            data = yaml.safe_load(f)
        
        return PersonaResponse(
            id=persona_id,
            name=data.get("name", persona_id),
            description=data.get("description", ""),
            data=data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading persona {persona_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to read persona"
        )


@router.post("/", response_model=PersonaResponse)
async def create_persona(request: PersonaCreateRequest):
    """Create a new persona."""
    try:
        # Generate ID from name
        persona_id = request.name.lower().replace(" ", "_")
        persona_file = PERSONAS_DIR / f"{persona_id}.yaml"
        
        if persona_file.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Persona {persona_id} already exists"
            )
        
        # Create persona data
        persona_data = {
            "name": request.name,
            "description": request.description,
            **request.data
        }
        
        # Ensure directory exists
        PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Write persona file
        with open(persona_file, 'w') as f:
            yaml.dump(persona_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"Created persona {persona_id}")
        
        return PersonaResponse(
            id=persona_id,
            name=request.name,
            description=request.description,
            data=persona_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create persona"
        )


@router.put("/{persona_id}")
async def update_persona(persona_id: str, request: PersonaCreateRequest):
    """Update an existing persona."""
    try:
        persona_file = PERSONAS_DIR / f"{persona_id}.yaml"
        
        if not persona_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Persona {persona_id} not found"
            )
        
        # Create backup
        from datetime import datetime
        backup_file = PERSONAS_DIR / f"{persona_id}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml"
        try:
            import shutil
            shutil.copy2(persona_file, backup_file)
            logger.info(f"Created backup: {backup_file.name}")
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
        
        # Update persona data
        persona_data = {
            "name": request.name,
            "description": request.description,
            **request.data
        }
        
        # Write updated file
        with open(persona_file, 'w') as f:
            yaml.dump(persona_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"Updated persona {persona_id}")
        
        return {"success": True, "message": f"Persona {persona_id} updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating persona {persona_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update persona"
        )


@router.delete("/{persona_id}")
async def delete_persona(persona_id: str):
    """Delete a persona."""
    try:
        persona_file = PERSONAS_DIR / f"{persona_id}.yaml"
        
        if not persona_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Persona {persona_id} not found"
            )
        
        # Create backup before deleting
        from datetime import datetime
        backup_file = PERSONAS_DIR / f"{persona_id}.deleted-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml"
        try:
            import shutil
            shutil.move(str(persona_file), str(backup_file))
            logger.info(f"Moved to backup: {backup_file.name}")
        except Exception as e:
            logger.error(f"Could not create backup: {e}")
            raise
        
        logger.info(f"Deleted persona {persona_id}")
        
        return {"success": True, "message": f"Persona {persona_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting persona {persona_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete persona"
        )