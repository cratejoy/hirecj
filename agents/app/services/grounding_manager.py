"""Manager for processing grounding knowledge directives."""

import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta

from app.models import Message
from app.services.knowledge_client import KnowledgeServiceClient
from shared.logging_config import get_logger

logger = get_logger(__name__)


class GroundingDirective:
    """Represents a grounding directive from a template."""
    
    def __init__(self, namespace: str, limit: Optional[int] = None, mode: Optional[str] = None):
        self.namespace = namespace
        self.limit = limit or 10  # Default to last 10 messages
        self.mode = mode or "hybrid"  # Default query mode
        
    def __repr__(self):
        return f"GroundingDirective(namespace={self.namespace}, limit={self.limit}, mode={self.mode})"


class GroundingManager:
    """Manages grounding knowledge extraction and integration."""
    
    # Pattern to match {{grounding: namespace}} with optional parameters
    # Handles any amount of whitespace before/after/within the directive
    GROUNDING_PATTERN = re.compile(
        r'\s*\{\{\s*grounding\s*:\s*([a-zA-Z0-9_-]+)(?:\s*,\s*([^}]+))?\s*\}\}\s*',
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    
    def __init__(self):
        self.knowledge_client = KnowledgeServiceClient()
        self._cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_ttl = timedelta(minutes=30)  # 30 minute cache
        
    def extract_grounding_directives(self, content: str) -> List[GroundingDirective]:
        """Extract grounding directives from template content.
        
        Args:
            content: Template content to parse
            
        Returns:
            List of GroundingDirective objects
        """
        directives = []
        
        for match in self.GROUNDING_PATTERN.finditer(content):
            namespace = match.group(1)
            params_str = match.group(2)
            
            # Parse optional parameters
            limit = None
            mode = None
            
            if params_str:
                # Parse comma-separated key:value pairs
                params = {}
                for param in params_str.split(','):
                    param = param.strip()
                    if ':' in param:
                        key, value = param.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key == 'limit':
                            try:
                                limit = int(value)
                            except ValueError:
                                logger.warning(f"Invalid limit value: {value}")
                        elif key == 'mode':
                            if value in ['naive', 'local', 'global', 'hybrid']:
                                mode = value
                            else:
                                logger.warning(f"Invalid mode value: {value}")
                
            directive = GroundingDirective(namespace, limit, mode)
            directives.append(directive)
            logger.info(f"Extracted grounding directive: {directive}")
            
        return directives
    
    def process_grounding(
        self, 
        directives: List[GroundingDirective], 
        conversation_context: List[Message]
    ) -> Dict[str, str]:
        """Process grounding directives with conversation context.
        
        Args:
            directives: List of grounding directives to process
            conversation_context: Recent conversation messages
            
        Returns:
            Dict mapping namespace to grounding content
        """
        results = {}
        
        for directive in directives:
            # Check cache first
            cache_key = f"{directive.namespace}:{directive.mode}"
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                results[directive.namespace] = cached_result
                logger.info(f"Using cached grounding for {directive.namespace}")
                continue
            
            # Build query from conversation context
            query = self._build_query_from_context(conversation_context, directive.limit)
            
            if not query:
                logger.warning(f"No context available for grounding {directive.namespace}")
                continue
            
            # Query knowledge graph
            logger.info(f"Querying knowledge graph '{directive.namespace}' with mode '{directive.mode}'")
            result = self.knowledge_client.query(
                namespace=directive.namespace,
                query=query,
                mode=directive.mode
            )
            
            if result:
                # Format result for inclusion in prompt
                formatted_result = self._format_grounding_result(directive.namespace, result)
                results[directive.namespace] = formatted_result
                
                # Cache the result
                self._cache_result(cache_key, formatted_result)
            else:
                logger.warning(f"No grounding result for namespace '{directive.namespace}'")
                
        return results
    
    def _build_query_from_context(self, messages: List[Message], limit: int) -> str:
        """Build a query from conversation context.
        
        Args:
            messages: Conversation messages
            limit: Maximum number of messages to use
            
        Returns:
            Query string
        """
        if not messages:
            return ""
        
        # Take the most recent messages up to the limit
        recent_messages = messages[-limit:]
        
        # Build a context-aware query
        # Focus on merchant messages and key topics
        merchant_messages = [
            msg.content for msg in recent_messages 
            if msg.sender == "merchant"
        ]
        
        if merchant_messages:
            # Use the most recent merchant messages as the primary query
            query_parts = merchant_messages[-3:]  # Last 3 merchant messages
            query = " ".join(query_parts)
        else:
            # Fall back to all recent messages
            query_parts = [msg.content for msg in recent_messages[-3:]]
            query = " ".join(query_parts)
        
        # Truncate if too long
        if len(query) > 500:
            query = query[:500] + "..."
            
        logger.debug(f"Built query from context: {query[:100]}...")
        return query
    
    def _format_grounding_result(self, namespace: str, result: str) -> str:
        """Format grounding result for inclusion in prompt.
        
        Args:
            namespace: Knowledge graph namespace
            result: Raw query result
            
        Returns:
            Formatted grounding content
        """
        # Clean up the result
        result = result.strip()
        
        # Format as a knowledge section
        formatted = f"\n\n[Knowledge from {namespace.upper()} database]:\n{result}\n"
        
        return formatted
    
    def _get_cached_result(self, cache_key: str) -> Optional[str]:
        """Get cached result if still valid.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached result or None if expired/missing
        """
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_ttl:
                return result
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: str):
        """Cache a grounding result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        self._cache[cache_key] = (result, datetime.now())
    
    def clear_cache(self):
        """Clear the grounding cache."""
        self._cache.clear()
        logger.info("Grounding cache cleared")
    
    def close(self):
        """Clean up resources."""
        self.knowledge_client.close()
    
    def replace_grounding_markers(self, content: str, grounding_results: Dict[str, str]) -> str:
        """Replace grounding markers with actual content.
        
        Args:
            content: Content with grounding markers
            grounding_results: Dict of namespace to grounding content
            
        Returns:
            Content with markers replaced
        """
        def replace_marker(match):
            namespace = match.group(1)
            if namespace in grounding_results:
                return grounding_results[namespace]
            else:
                # Leave marker as-is if no result
                return match.group(0)
        
        # Replace all grounding markers
        return self.GROUNDING_PATTERN.sub(replace_marker, content)