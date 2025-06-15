"""
Prompt management API endpoints for internal editor tool.
"""

import yaml
from pathlib import Path
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])

# Path to prompts directory
PROMPTS_DIR = Path(settings.prompts_dir) / "cj" / "versions"


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse version string like 'v6.0.1' into (major, minor, patch)"""
    clean = version_str.replace('v', '')
    parts = clean.split('.')
    return int(parts[0]), int(parts[1]), int(parts[2])


def increment_version(version_str: str, increment_type: str = 'patch') -> str:
    """Increment version number. Default increments patch version."""
    major, minor, patch = parse_version(version_str)
    
    if increment_type == 'major':
        return f"v{major + 1}.0.0"
    elif increment_type == 'minor':
        return f"v{major}.{minor + 1}.0"
    else:  # patch
        return f"v{major}.{minor}.{patch + 1}"


def find_next_available_version(base_version: str) -> str:
    """Find the next available version number if the expected one exists."""
    next_version = increment_version(base_version)
    version_file = PROMPTS_DIR / f"{next_version}.yaml"
    
    # If the expected version doesn't exist, use it
    if not version_file.exists():
        return next_version
    
    # Otherwise, keep incrementing until we find an available version
    major, minor, patch = parse_version(base_version)
    while True:
        patch += 1
        test_version = f"v{major}.{minor}.{patch}"
        if not (PROMPTS_DIR / f"{test_version}.yaml").exists():
            return test_version


class PromptVersionResponse(BaseModel):
    """Response containing list of prompt versions"""
    versions: List[str]


class PromptContentResponse(BaseModel):
    """Response containing prompt content"""
    prompt: str


class PromptUpdateRequest(BaseModel):
    """Request to update prompt content"""
    prompt: str


class NewVersionRequest(BaseModel):
    """Request to create a new version of a prompt"""
    current_version: str
    prompt: str


class NewVersionResponse(BaseModel):
    """Response after creating a new version"""
    version: str
    message: str


@router.get("/", response_model=PromptVersionResponse)
async def list_prompt_versions():
    """List all available prompt versions."""
    try:
        if not PROMPTS_DIR.exists():
            logger.error(f"Prompts directory not found: {PROMPTS_DIR}")
            raise HTTPException(
                status_code=500,
                detail="Prompts directory not found"
            )
        
        # Get all YAML files
        yaml_files = list(PROMPTS_DIR.glob("*.yaml"))
        versions = [f.stem for f in yaml_files]
        
        # Sort versions properly (v6.0.1 > v6.0.0 > v5.0.0)
        def parse_version(v):
            return [int(x) for x in v.replace('v', '').split('.')]
        
        versions.sort(key=parse_version, reverse=True)
        
        logger.info(f"Found {len(versions)} prompt versions")
        return PromptVersionResponse(versions=versions)
        
    except Exception as e:
        logger.error(f"Error listing prompt versions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list prompt versions"
        )


@router.get("/{version}", response_model=PromptContentResponse)
async def get_prompt_content(version: str):
    """Get content of a specific prompt version."""
    try:
        prompt_file = PROMPTS_DIR / f"{version}.yaml"
        
        if not prompt_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Prompt version {version} not found"
            )
        
        with open(prompt_file, 'r') as f:
            data = yaml.safe_load(f)
        
        prompt_content = data.get('prompt', '')
        logger.info(f"Loaded prompt {version} ({len(prompt_content)} chars)")
        
        return PromptContentResponse(prompt=prompt_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading prompt {version}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to read prompt content"
        )


@router.put("/{version}")
async def update_prompt(version: str, update: PromptUpdateRequest):
    """Update prompt content with automatic backup."""
    try:
        prompt_file = PROMPTS_DIR / f"{version}.yaml"
        
        if not prompt_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Prompt version {version} not found"
            )
        
        # Create backup before modifying
        backup_file = PROMPTS_DIR / f"{version}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml"
        try:
            import shutil
            shutil.copy2(prompt_file, backup_file)
            logger.info(f"Created backup: {backup_file.name}")
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
        
        # Prepare data for YAML
        data = {'prompt': update.prompt}
        
        # Write updated content
        with open(prompt_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"Updated prompt {version} ({len(update.prompt)} chars)")
        
        return {"success": True, "message": f"Prompt {version} updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt {version}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update prompt"
        )


@router.post("/new-version", response_model=NewVersionResponse)
async def create_new_version(request: NewVersionRequest):
    """Create a new version of a prompt with incremented version number."""
    try:
        # Verify current version exists
        current_file = PROMPTS_DIR / f"{request.current_version}.yaml"
        if not current_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Current version {request.current_version} not found"
            )
        
        # Find the next available version
        new_version = find_next_available_version(request.current_version)
        new_file = PROMPTS_DIR / f"{new_version}.yaml"
        
        # Prepare data for YAML
        data = {'prompt': request.prompt}
        
        # Write new version
        with open(new_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"Created new prompt version {new_version} from {request.current_version}")
        
        return NewVersionResponse(
            version=new_version,
            message=f"Created new version {new_version}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating new prompt version: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create new prompt version"
        )