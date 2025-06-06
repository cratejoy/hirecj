"""
UI Components for Agent Responses

Currently supports only Shopify OAuth button.
Designed to be extended when needed.
"""

import re
from typing import Dict, List, Tuple, Optional

class UIComponentParser:
    """Parse UI components from agent responses."""
    
    # For now, just one pattern
    OAUTH_PATTERN = re.compile(
        r'{{oauth:shopify}}',
        re.IGNORECASE
    )
    
    def parse_oauth_buttons(self, content: str) -> Tuple[str, List[Dict]]:
        """
        Find OAuth button markers and extract them.
        
        Args:
            content: The agent's response text
            
        Returns:
            Tuple of:
            - content_with_placeholders: Text with markers replaced by placeholders
            - ui_components: List of UI component definitions
            
        Example:
            Input: "Let's connect your store: {{oauth:shopify}}"
            Output: ("Let's connect your store: __OAUTH_BUTTON_1__", 
                    [{'id': 'oauth_1', 'type': 'oauth_button', ...}])
        """
        components = []
        
        # Find all OAuth markers
        matches = list(self.OAUTH_PATTERN.finditer(content))
        
        # Process in reverse to maintain string positions
        clean_content = content
        for i, match in enumerate(reversed(matches)):
            component_id = len(matches) - i
            placeholder = f"__OAUTH_BUTTON_{component_id}__"
            
            # Replace marker with placeholder
            start, end = match.span()
            clean_content = clean_content[:start] + placeholder + clean_content[end:]
            
            # Create component definition
            components.append({
                'id': f'oauth_{component_id}',
                'type': 'oauth_button',
                'provider': 'shopify',
                'placeholder': placeholder
            })
        
        # Return in correct order (reversed back)
        return clean_content, list(reversed(components))
    
    # Future extension example (not implemented yet):
    # def parse_choices(self, content: str) -> Tuple[str, List[Dict]]:
    #     """Parse {{choices:option1,option2,option3}} markers."""
    #     pass