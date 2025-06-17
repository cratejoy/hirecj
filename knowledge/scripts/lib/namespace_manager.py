"""
Namespace management for Knowledge CLI
"""
import aiohttp
import json
from typing import List, Dict, Optional, Any
from .utils import print_error, print_success, print_info, parse_api_error


class NamespaceManager:
    """Handles namespace operations"""
    
    def __init__(self, api_base: str):
        self.api_base = api_base
    
    async def list_namespaces(self) -> List[Dict[str, Any]]:
        """List all namespaces"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/api/namespaces") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        namespaces = data.get('namespaces', [])
                        
                        # Fetch statistics for each namespace
                        for ns in namespaces:
                            stats = await self.get_namespace_stats(ns['id'])
                            if stats:
                                ns['stats'] = stats
                        
                        return namespaces
                    else:
                        error_text = await resp.text()
                        error_msg = parse_api_error(error_text)
                        print_error(f"Failed to list namespaces: {error_msg}")
                        return []
        except aiohttp.ClientError as e:
            print_error(f"Unable to connect to Knowledge API at {self.api_base}: {str(e)}")
            return []
        except Exception as e:
            print_error(f"Unexpected error listing namespaces: {str(e)}")
            return []
    
    async def get_namespace_stats(self, namespace_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a namespace"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/api/{namespace_id}/statistics") as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception:
            return None
    
    async def create_namespace(self, namespace_id: str, name: str, description: str) -> bool:
        """Create a new namespace"""
        try:
            async with aiohttp.ClientSession() as session:
                # namespace_id goes as query parameter, config in body
                params = {"namespace_id": namespace_id}
                payload = {
                    "name": name,
                    "description": description
                }
                
                async with session.post(
                    f"{self.api_base}/api/namespaces",
                    params=params,
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        return True
                    else:
                        error_text = await resp.text()
                        error_msg = parse_api_error(error_text)
                        
                        # Add more context for common errors
                        if resp.status == 409:
                            print_error(f"Namespace '{namespace_id}' already exists")
                        elif resp.status == 400:
                            print_error(f"Invalid namespace ID '{namespace_id}': {error_msg}")
                        else:
                            print_error(f"Failed to create namespace: {error_msg}")
                        return False
        except aiohttp.ClientError as e:
            print_error(f"Unable to connect to Knowledge API at {self.api_base}: {str(e)}")
            return False
        except Exception as e:
            print_error(f"Unexpected error creating namespace: {str(e)}")
            return False
    
    async def ensure_namespace_exists(self, namespace_id: str) -> bool:
        """Ensure a namespace exists, create if not"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check if namespace exists
                async with session.get(f"{self.api_base}/api/namespaces/{namespace_id}") as resp:
                    if resp.status == 200:
                        return False  # Already exists
                    elif resp.status == 404:
                        # Create it
                        name = namespace_id.replace('_', ' ').title()
                        description = f"Auto-created namespace for {namespace_id}"
                        return await self.create_namespace(namespace_id, name, description)
                    else:
                        error_text = await resp.text()
                        error_msg = parse_api_error(error_text)
                        print_error(f"Error checking namespace: {error_msg}")
                        return False
        except aiohttp.ClientError as e:
            print_error(f"Unable to connect to Knowledge API at {self.api_base}: {str(e)}")
            return False
        except Exception as e:
            print_error(f"Unexpected error ensuring namespace exists: {str(e)}")
            return False
    
    async def get_namespace_info(self, namespace_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a namespace"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/api/namespaces/{namespace_id}") as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception:
            return None