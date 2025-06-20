from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any, Optional
import httpx
import os
import json
from datetime import datetime
import glob
from pathlib import Path

router = APIRouter()

# Base paths
EVALS_BASE_PATH = Path("/Users/aelaguiz/workspace/hirecj/hirecj_evals")
CONVERSATIONS_PATH = EVALS_BASE_PATH / "conversations"
DATASETS_PATH = EVALS_BASE_PATH / "datasets"

# Ensure directories exist
CONVERSATIONS_PATH.mkdir(parents=True, exist_ok=True)
DATASETS_PATH.mkdir(parents=True, exist_ok=True)

@router.get("/conversations")
async def list_conversations():
    """List all captured conversations."""
    conversations = []
    
    for source_dir in CONVERSATIONS_PATH.iterdir():
        if not source_dir.is_dir():
            continue
            
        for date_dir in source_dir.iterdir():
            if not date_dir.is_dir():
                continue
                
            for conv_file in date_dir.glob("*.json"):
                try:
                    with open(conv_file, 'r') as f:
                        data = json.load(f)
                        
                    # Create summary
                    summary = {
                        "id": data.get("id", conv_file.stem),
                        "timestamp": data.get("timestamp", ""),
                        "source": source_dir.name,
                        "workflow": data.get("context", {}).get("workflow", {}).get("name", "unknown"),
                        "persona": data.get("context", {}).get("persona", {}).get("name", None),
                        "message_count": len(data.get("messages", [])),
                        "has_tool_calls": any(
                            msg.get("agent_processing", {}).get("tool_calls", [])
                            for msg in data.get("messages", [])
                        ),
                        "has_grounding": any(
                            msg.get("agent_processing", {}).get("grounding_queries", [])
                            for msg in data.get("messages", [])
                        ),
                        "file_path": str(conv_file)
                    }
                    conversations.append(summary)
                except Exception as e:
                    print(f"Error reading conversation {conv_file}: {e}")
                    continue
    
    # Sort by timestamp descending
    conversations.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {"conversations": conversations}

@router.get("/conversations/{conversation_id}/convert")
async def convert_conversation_to_cases(conversation_id: str):
    """Convert a conversation to eval test cases."""
    
    # Find the conversation file
    conv_file = None
    for source_dir in CONVERSATIONS_PATH.iterdir():
        if not source_dir.is_dir():
            continue
        for date_dir in source_dir.iterdir():
            if not date_dir.is_dir():
                continue
            potential_file = date_dir / f"{conversation_id}.json"
            if potential_file.exists():
                conv_file = potential_file
                break
        if conv_file:
            break
    
    if not conv_file:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        with open(conv_file, 'r') as f:
            conversation = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading conversation: {e}")
    
    # Convert to eval cases
    cases = []
    messages_so_far = []
    
    # Add system message if present
    if conversation.get("prompts", {}).get("cj_prompt"):
        messages_so_far.append({
            "role": "system",
            "content": conversation["prompts"]["cj_prompt"]
        })
    
    for i, msg in enumerate(conversation.get("messages", [])):
        # Add user message
        messages_so_far.append({
            "role": "user",
            "content": msg["user_input"]
        })
        
        # Create eval case
        case = {
            "id": f"{conversation_id}_turn_{msg['turn']}",
            "eval_id": "conversation_flow",
            "sample_id": f"{conversation_id}_turn_{msg['turn']}",
            "input": {
                "messages": messages_so_far.copy(),
                "context": {
                    "workflow": conversation.get("context", {}).get("workflow", {}).get("name", ""),
                    "available_tools": [t["name"] for t in conversation.get("prompts", {}).get("tool_definitions", [])],
                    "persona": conversation.get("context", {}).get("persona", {}).get("name", None),
                    "trust_level": conversation.get("context", {}).get("trustLevel", 0)
                }
            },
            "ideal": {
                "tool_selection": {
                    "should_use_tool": len(msg.get("agent_processing", {}).get("tool_calls", [])) > 0,
                    "acceptable_tools": [tc["tool"] for tc in msg.get("agent_processing", {}).get("tool_calls", [])]
                } if msg.get("agent_processing", {}).get("tool_calls") else {},
                "response_criteria": {
                    "must_include": [],  # User can fill these in
                    "tone": "helpful"
                }
            },
            "actual": {
                "thinking": msg.get("agent_processing", {}).get("thinking", ""),
                "tool_calls": [tc["tool"] for tc in msg.get("agent_processing", {}).get("tool_calls", [])],
                "grounding_queries": [gq["query"] for gq in msg.get("agent_processing", {}).get("grounding_queries", [])],
                "response": msg.get("agent_processing", {}).get("final_response", "")
            },
            "metadata": {
                "source_conversation": conversation_id,
                "turn": msg["turn"],
                "timestamp": conversation.get("timestamp", ""),
                "created_by": "eval_designer",
                "modified_at": datetime.now().isoformat()
            }
        }
        cases.append(case)
        
        # Add assistant message for next turn
        messages_so_far.append({
            "role": "assistant",
            "content": msg.get("agent_processing", {}).get("final_response", "")
        })
    
    return {"cases": cases}

@router.get("/datasets")
async def list_datasets():
    """List all eval datasets."""
    datasets = []
    
    for category_dir in DATASETS_PATH.iterdir():
        if not category_dir.is_dir():
            continue
            
        for dataset_file in category_dir.glob("*.jsonl"):
            try:
                # Read metadata from first line or separate metadata file
                metadata_file = dataset_file.with_suffix(".meta.json")
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                else:
                    # Create default metadata
                    metadata = {
                        "created_at": datetime.fromtimestamp(dataset_file.stat().st_ctime).isoformat(),
                        "updated_at": datetime.fromtimestamp(dataset_file.stat().st_mtime).isoformat(),
                        "version": "1.0.0"
                    }
                
                # Count cases
                case_count = sum(1 for _ in open(dataset_file))
                
                dataset = {
                    "id": dataset_file.stem,
                    "name": dataset_file.stem.replace("_", " ").title(),
                    "description": metadata.get("description", ""),
                    "category": category_dir.name,
                    "cases": [],  # Don't load all cases for listing
                    "metadata": metadata
                }
                datasets.append(dataset)
            except Exception as e:
                print(f"Error reading dataset {dataset_file}: {e}")
                continue
    
    return {"datasets": datasets}

@router.post("/datasets")
async def create_dataset(request: Request):
    """Create a new eval dataset."""
    data = await request.json()
    
    name = data.get("name", "").replace(" ", "_").lower()
    if not name:
        raise HTTPException(status_code=400, detail="Dataset name is required")
    
    category = data.get("category", "generated")
    category_dir = DATASETS_PATH / category
    category_dir.mkdir(exist_ok=True)
    
    dataset_file = category_dir / f"{name}.jsonl"
    metadata_file = category_dir / f"{name}.meta.json"
    
    if dataset_file.exists():
        raise HTTPException(status_code=409, detail="Dataset already exists")
    
    # Save cases
    cases = data.get("cases", [])
    with open(dataset_file, 'w') as f:
        for case in cases:
            f.write(json.dumps(case) + '\n')
    
    # Save metadata
    metadata = {
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "description": data.get("description", ""),
        "tags": data.get("tags", [])
    }
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return {
        "id": name,
        "name": data.get("name"),
        "description": data.get("description", ""),
        "category": category,
        "cases": cases,
        "metadata": metadata
    }

@router.post("/datasets/save")
async def save_cases_to_dataset(request: Request):
    """Save eval cases to an existing or new dataset."""
    data = await request.json()
    
    dataset_id = data.get("dataset_id", "new")
    cases = data.get("cases", [])
    
    if dataset_id == "new":
        # Generate a new dataset name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_id = f"generated_{timestamp}"
        category = "generated"
    else:
        # Find existing dataset
        dataset_file = None
        for category_dir in DATASETS_PATH.iterdir():
            if not category_dir.is_dir():
                continue
            potential_file = category_dir / f"{dataset_id}.jsonl"
            if potential_file.exists():
                dataset_file = potential_file
                category = category_dir.name
                break
        
        if not dataset_file:
            raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Save cases
    category_dir = DATASETS_PATH / category
    category_dir.mkdir(exist_ok=True)
    dataset_file = category_dir / f"{dataset_id}.jsonl"
    
    # Append to existing or create new
    with open(dataset_file, 'a') as f:
        for case in cases:
            case["metadata"]["modified_at"] = datetime.now().isoformat()
            f.write(json.dumps(case) + '\n')
    
    # Update metadata
    metadata_file = category_dir / f"{dataset_id}.meta.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    
    metadata["updated_at"] = datetime.now().isoformat()
    if "source_conversation" in data.get("metadata", {}):
        if "source_conversations" not in metadata:
            metadata["source_conversations"] = []
        metadata["source_conversations"].append(data["metadata"]["source_conversation"])
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return {
        "dataset_id": dataset_id,
        "cases_saved": len(cases),
        "path": str(dataset_file)
    }

@router.get("/datasets/{dataset_id}/export")
async def export_dataset(dataset_id: str):
    """Export a dataset as JSONL file."""
    
    # Find dataset file
    dataset_file = None
    for category_dir in DATASETS_PATH.iterdir():
        if not category_dir.is_dir():
            continue
        potential_file = category_dir / f"{dataset_id}.jsonl"
        if potential_file.exists():
            dataset_file = potential_file
            break
    
    if not dataset_file:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Return file contents
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(dataset_file),
        filename=f"{dataset_id}.jsonl",
        media_type="application/x-ndjson"
    )

@router.post("/preview")
async def preview_eval_execution(request: Request):
    """Preview eval execution using actual evaluators."""
    data = await request.json()
    cases = data.get("cases", [])
    
    # Import evaluation dependencies
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    
    from agents.app.evals.base import ModelGraded, EvalSample
    from agents.app.config import settings
    
    # Check for API key
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500, 
            detail="OPENAI_API_KEY not configured. Set it in your environment to run evaluations."
        )
    
    results = []
    
    for case in cases:
        case_results = {
            "case_id": case["id"],
            "evaluations": []
        }
        
        # Get response to evaluate
        response = case.get("actual", {}).get("response", "")
        
        # Get requirements from case
        requirements = case.get("ideal", {}).get("requirements", [])
        
        # If no requirements specified, check for legacy criteria
        if not requirements and case.get("ideal", {}).get("response_criteria"):
            criteria = case["ideal"]["response_criteria"]
            # Convert legacy must_include to requirements
            for must_include in criteria.get("must_include", []):
                requirements.append(f"Response must include '{must_include}'")
            if criteria.get("tone"):
                requirements.append(f"Response must have a {criteria['tone']} tone")
        
        # Evaluate each requirement
        all_passed = True
        for requirement in requirements:
            try:
                # Create evaluator for this requirement
                evaluator = ModelGraded(
                    grader_model="gpt-4o-mini",
                    temperature=0.0,
                    max_tokens=150,
                    grading_prompt=f"""Check if this response meets the following requirement:
{requirement}

Response to evaluate:
{response}

Respond with:
PASS - if requirement is met (explain briefly why)
FAIL - if requirement is not met (quote specific issue)"""
                )
                
                # Create eval sample
                sample = EvalSample(
                    eval_id="requirement",
                    sample_id=case["id"],
                    input=case.get("input", {}),
                    actual={"response": response}
                )
                
                # Run evaluation
                result = evaluator.eval_sample(sample)
                
                passed = result.status.value == "pass"
                if not passed:
                    all_passed = False
                
                case_results["evaluations"].append({
                    "requirement": requirement,
                    "passed": passed,
                    "reason": result.reason or "",
                    "details": result.details
                })
                
            except Exception as e:
                # Handle evaluation errors
                all_passed = False
                case_results["evaluations"].append({
                    "requirement": requirement,
                    "passed": False,
                    "reason": f"Evaluation error: {str(e)}",
                    "details": None
                })
        
        # Overall result for the case
        case_results["passed"] = all_passed
        case_results["score"] = 1.0 if all_passed else 0.0
        
        results.append(case_results)
    
    return {"results": results}