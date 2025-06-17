"""
Unified service for persona data and prompts.
Provides a single source of truth for all persona-related data.
"""

import re
from typing import Dict, List, Optional
from app.prompts.loader import PromptLoader


class PersonaService:
    """Unified service for persona data and prompts."""
    
    def __init__(self):
        self.prompt_loader = PromptLoader()
    
    def get_all_personas(self) -> List[Dict]:
        """Get all personas - just the basics we actually have."""
        persona_dirs = self.prompt_loader.list_merchant_personas()
        result = []
        
        for persona_id in persona_dirs:
            # Convert ID to display name
            name = persona_id.replace("_", " ").title()
            
            # Try to get business name from prompt, otherwise use a default
            prompt_text = self.get_persona_prompt(persona_id, "v1.0.0")
            business = name  # Default to name
            
            if prompt_text:
                # Quick extract of business line if it exists
                match = re.search(r'\*\*Business:\*\* (.+)', prompt_text)
                if match:
                    business = match.group(1).strip()
            
            result.append({
                "id": persona_id,
                "name": name,
                "business": business
            })
        
        return result
    
    def get_persona(self, persona_id: str) -> Optional[Dict]:
        """Get single persona data."""
        available_personas = self.prompt_loader.list_merchant_personas()
        
        if persona_id not in available_personas:
            return None
        
        # Convert ID to display name
        name = persona_id.replace("_", " ").title()
        
        # Try to get business name from prompt
        prompt_text = self.get_persona_prompt(persona_id, "v1.0.0")
        business = name  # Default to name
        
        if prompt_text:
            # Quick extract of business line if it exists
            match = re.search(r'\*\*Business:\*\* (.+)', prompt_text)
            if match:
                business = match.group(1).strip()
        
        return {
            "id": persona_id,
            "name": name,
            "business": business,
            "has_prompts": True,
            "available_versions": self._get_versions(persona_id)
        }
    
    def get_persona_prompt(self, persona_id: str, version: str = "latest") -> Optional[str]:
        """Get prompt text for a persona."""
        try:
            data = self.prompt_loader.load_merchant_persona(persona_id, version)
            return data.get("prompt", "")
        except FileNotFoundError:
            return None
    
    def _get_versions(self, persona_id: str) -> List[str]:
        """Get available prompt versions."""
        try:
            return self.prompt_loader.list_persona_versions(persona_id)
        except Exception:
            return []