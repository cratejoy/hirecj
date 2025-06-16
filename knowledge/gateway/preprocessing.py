"""
Content preprocessing pipeline for Knowledge API
Handles various content formats and prepares them for ingestion
"""
import json
import re
from typing import Dict, Any, Optional
import html2text
from datetime import datetime

class ContentPreprocessor:
    """Preprocesses various content types for LightRAG ingestion"""
    
    def __init__(self):
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.body_width = 0  # Don't wrap lines
    
    def preprocess_text(self, content: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Normalize line endings
        content = content.replace('\r\n', '\n')
        content = content.replace('\r', '\n')
        
        # Remove zero-width characters
        content = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', content)
        
        # Strip leading/trailing whitespace
        content = content.strip()
        
        return content
    
    def json_to_text(self, json_data: Any, indent_level: int = 0) -> str:
        """Convert JSON data to readable text format"""
        lines = []
        indent = "  " * indent_level
        
        if isinstance(json_data, dict):
            for key, value in json_data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{indent}{key}:")
                    lines.append(self.json_to_text(value, indent_level + 1))
                else:
                    # Convert value to string and clean it
                    str_value = str(value).strip()
                    if str_value:
                        lines.append(f"{indent}{key}: {str_value}")
        
        elif isinstance(json_data, list):
            for i, item in enumerate(json_data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent}Item {i + 1}:")
                    lines.append(self.json_to_text(item, indent_level + 1))
                else:
                    str_value = str(item).strip()
                    if str_value:
                        lines.append(f"{indent}- {str_value}")
        
        else:
            # Primitive value
            str_value = str(json_data).strip()
            if str_value:
                lines.append(f"{indent}{str_value}")
        
        return "\n".join(filter(None, lines))
    
    def html_to_text(self, html_content: str) -> str:
        """Convert HTML to clean text"""
        # Convert HTML to markdown-style text
        text = self.h2t.handle(html_content)
        
        # Clean up the result
        text = self.preprocess_text(text)
        
        return text
    
    def extract_metadata_from_json(self, json_data: Any) -> Dict[str, str]:
        """Extract useful metadata from JSON structure"""
        metadata = {}
        
        if isinstance(json_data, dict):
            # Look for common metadata fields
            metadata_fields = ['title', 'name', 'description', 'author', 
                             'date', 'created_at', 'updated_at', 'type', 
                             'category', 'tags', 'id', 'version']
            
            for field in metadata_fields:
                if field in json_data:
                    value = json_data[field]
                    if isinstance(value, list):
                        metadata[field] = ', '.join(str(v) for v in value)
                    else:
                        metadata[field] = str(value)
        
        return metadata
    
    def extract_metadata_from_url(self, url: str, content_type: str = None) -> Dict[str, str]:
        """Extract metadata from URL"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        metadata = {
            'source_url': url,
            'domain': parsed.netloc,
            'path': parsed.path,
            'fetch_time': datetime.now().isoformat()
        }
        
        if content_type:
            metadata['content_type'] = content_type
        
        return metadata
    
    def preprocess_json_file(self, content: str) -> tuple[str, Dict[str, str]]:
        """Preprocess JSON file content"""
        try:
            json_data = json.loads(content)
            
            # Extract metadata
            metadata = self.extract_metadata_from_json(json_data)
            
            # Convert to text
            text_content = self.json_to_text(json_data)
            
            # Clean up
            text_content = self.preprocess_text(text_content)
            
            return text_content, metadata
            
        except json.JSONDecodeError as e:
            # If JSON is invalid, treat as text
            return self.preprocess_text(content), {"json_error": str(e)}
    
    def preprocess_url_content(self, html_content: str, url: str, content_type: str = None) -> tuple[str, Dict[str, str]]:
        """Preprocess content fetched from URL"""
        # Extract metadata
        metadata = self.extract_metadata_from_url(url, content_type)
        
        # Convert HTML to text
        if content_type and 'html' in content_type.lower():
            text_content = self.html_to_text(html_content)
        else:
            # Assume plain text
            text_content = self.preprocess_text(html_content)
        
        return text_content, metadata