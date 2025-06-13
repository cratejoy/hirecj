"""
Workflow management API endpoints.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

# Path to workflows directory
WORKFLOWS_DIR = Path(settings.workflows_dir)


class WorkflowListResponse(BaseModel):
    """Response containing list of workflows"""
    workflows: List[Dict[str, Any]]


class WorkflowResponse(BaseModel):
    """Response containing workflow details"""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    data: Dict[str, Any]


class WorkflowCreateRequest(BaseModel):
    """Request to create/update a workflow"""
    name: str
    description: str
    steps: List[Dict[str, Any]]
    data: Dict[str, Any] = {}


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows():
    """List all available workflows."""
    try:
        workflows = []
        
        # Check in workflow_definitions.yaml first
        workflow_defs_file = Path(settings.prompts_dir).parent / "workflow_definitions.yaml"
        if workflow_defs_file.exists():
            try:
                with open(workflow_defs_file, 'r') as f:
                    data = yaml.safe_load(f)
                    if data and 'workflows' in data:
                        for wf_id, wf_data in data['workflows'].items():
                            workflows.append({
                                "id": wf_id,
                                "name": wf_data.get("name", wf_id),
                                "description": wf_data.get("description", ""),
                            })
            except Exception as e:
                logger.warning(f"Error reading workflow definitions: {e}")
        
        # Also check individual workflow files if directory exists
        if WORKFLOWS_DIR.exists():
            yaml_files = list(WORKFLOWS_DIR.glob("*.yaml"))
            for file in yaml_files:
                try:
                    with open(file, 'r') as f:
                        data = yaml.safe_load(f)
                        workflows.append({
                            "id": file.stem,
                            "name": data.get("name", file.stem),
                            "description": data.get("description", ""),
                        })
                except Exception as e:
                    logger.warning(f"Error reading workflow file {file}: {e}")
        
        logger.info(f"Found {len(workflows)} workflows")
        return WorkflowListResponse(workflows=workflows)
        
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list workflows"
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    """Get details of a specific workflow."""
    try:
        # Check in workflow_definitions.yaml first
        workflow_defs_file = Path(settings.prompts_dir).parent / "workflow_definitions.yaml"
        if workflow_defs_file.exists():
            with open(workflow_defs_file, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'workflows' in data and workflow_id in data['workflows']:
                    wf_data = data['workflows'][workflow_id]
                    return WorkflowResponse(
                        id=workflow_id,
                        name=wf_data.get("name", workflow_id),
                        description=wf_data.get("description", ""),
                        steps=wf_data.get("steps", []),
                        data=wf_data
                    )
        
        # Check individual file
        workflow_file = WORKFLOWS_DIR / f"{workflow_id}.yaml"
        if workflow_file.exists():
            with open(workflow_file, 'r') as f:
                data = yaml.safe_load(f)
            
            return WorkflowResponse(
                id=workflow_id,
                name=data.get("name", workflow_id),
                description=data.get("description", ""),
                steps=data.get("steps", []),
                data=data
            )
        
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow_id} not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to read workflow"
        )


@router.post("/", response_model=WorkflowResponse)
async def create_workflow(request: WorkflowCreateRequest):
    """Create a new workflow."""
    try:
        # Generate ID from name
        workflow_id = request.name.lower().replace(" ", "_")
        
        # Ensure directory exists
        WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
        
        workflow_file = WORKFLOWS_DIR / f"{workflow_id}.yaml"
        
        if workflow_file.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Workflow {workflow_id} already exists"
            )
        
        # Create workflow data
        workflow_data = {
            "name": request.name,
            "description": request.description,
            "steps": request.steps,
            **request.data
        }
        
        # Write workflow file
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"Created workflow {workflow_id}")
        
        return WorkflowResponse(
            id=workflow_id,
            name=request.name,
            description=request.description,
            steps=request.steps,
            data=workflow_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create workflow"
        )


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, request: WorkflowCreateRequest):
    """Update an existing workflow."""
    try:
        workflow_file = WORKFLOWS_DIR / f"{workflow_id}.yaml"
        
        # Check if updating in workflow_definitions.yaml
        workflow_defs_file = Path(settings.prompts_dir).parent / "workflow_definitions.yaml"
        in_definitions = False
        
        if workflow_defs_file.exists():
            with open(workflow_defs_file, 'r') as f:
                data = yaml.safe_load(f)
                if data and 'workflows' in data and workflow_id in data['workflows']:
                    in_definitions = True
        
        if not workflow_file.exists() and not in_definitions:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Create backup if individual file
        if workflow_file.exists():
            from datetime import datetime
            backup_file = WORKFLOWS_DIR / f"{workflow_id}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml"
            try:
                import shutil
                shutil.copy2(workflow_file, backup_file)
                logger.info(f"Created backup: {backup_file.name}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")
        
        # Update workflow data
        workflow_data = {
            "name": request.name,
            "description": request.description,
            "steps": request.steps,
            **request.data
        }
        
        # If it's in the individual file or needs to be created
        if not in_definitions:
            WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
            with open(workflow_file, 'w') as f:
                yaml.dump(workflow_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            # Update in workflow_definitions.yaml
            with open(workflow_defs_file, 'r') as f:
                all_data = yaml.safe_load(f)
            
            all_data['workflows'][workflow_id] = workflow_data
            
            # Backup the definitions file
            from datetime import datetime
            backup_file = workflow_defs_file.with_suffix(f".backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml")
            try:
                import shutil
                shutil.copy2(workflow_defs_file, backup_file)
                logger.info(f"Created backup: {backup_file.name}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")
            
            with open(workflow_defs_file, 'w') as f:
                yaml.dump(all_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"Updated workflow {workflow_id}")
        
        return {"success": True, "message": f"Workflow {workflow_id} updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update workflow"
        )


@router.get("/{workflow_id}/raw")
async def get_workflow_raw(workflow_id: str):
    """Get raw workflow YAML content."""
    try:
        workflow_file = WORKFLOWS_DIR / f"{workflow_id}.yaml"
        
        if not workflow_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found"
            )
        
        with open(workflow_file, 'r') as f:
            content = f.read()
        
        logger.info(f"Retrieved raw workflow {workflow_id}")
        return {"content": content}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to read workflow content"
        )