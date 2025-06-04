import pytest
from app.services.ui_components import UIComponentParser

def test_single_oauth_marker():
    """Test parsing a single OAuth marker."""
    parser = UIComponentParser()
    content = "Let's connect your store: {{oauth:shopify}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    # Verify content has placeholder
    assert clean_content == "Let's connect your store: __OAUTH_BUTTON_1__"
    
    # Verify component extracted
    assert len(components) == 1
    assert components[0]['type'] == 'oauth_button'
    assert components[0]['provider'] == 'shopify'
    assert components[0]['placeholder'] == '__OAUTH_BUTTON_1__'

def test_multiple_oauth_markers():
    """Test parsing multiple OAuth markers."""
    parser = UIComponentParser()
    content = "First: {{oauth:shopify}} and second: {{oauth:shopify}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    # Verify both placeholders
    assert "__OAUTH_BUTTON_1__" in clean_content
    assert "__OAUTH_BUTTON_2__" in clean_content
    assert len(components) == 2

def test_no_markers():
    """Test content without markers passes through unchanged."""
    parser = UIComponentParser()
    content = "This is regular content with no markers"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert clean_content == content
    assert len(components) == 0

def test_case_insensitive():
    """Test marker parsing is case insensitive."""
    parser = UIComponentParser()
    content = "Connect: {{OAUTH:SHOPIFY}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert "__OAUTH_BUTTON_1__" in clean_content
    assert len(components) == 1

def test_marker_with_surrounding_text():
    """Test marker parsing with text before and after."""
    parser = UIComponentParser()
    content = "Before text {{oauth:shopify}} after text"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert clean_content == "Before text __OAUTH_BUTTON_1__ after text"
    assert len(components) == 1

def test_multiple_markers_with_ids():
    """Test that multiple markers get correct IDs and placeholders."""
    parser = UIComponentParser()
    content = "First {{oauth:shopify}}, second {{oauth:shopify}}, third {{oauth:shopify}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    # Check all placeholders are present
    assert "__OAUTH_BUTTON_1__" in clean_content
    assert "__OAUTH_BUTTON_2__" in clean_content
    assert "__OAUTH_BUTTON_3__" in clean_content
    
    # Check component IDs
    assert components[0]['id'] == 'oauth_1'
    assert components[1]['id'] == 'oauth_2'
    assert components[2]['id'] == 'oauth_3'
    
    # Check placeholders match
    assert components[0]['placeholder'] == '__OAUTH_BUTTON_1__'
    assert components[1]['placeholder'] == '__OAUTH_BUTTON_2__'
    assert components[2]['placeholder'] == '__OAUTH_BUTTON_3__'

def test_empty_content():
    """Test parsing empty content."""
    parser = UIComponentParser()
    content = ""
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert clean_content == ""
    assert len(components) == 0

def test_marker_at_start():
    """Test marker at the beginning of content."""
    parser = UIComponentParser()
    content = "{{oauth:shopify}} Connect your store now!"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert clean_content == "__OAUTH_BUTTON_1__ Connect your store now!"
    assert len(components) == 1

def test_marker_at_end():
    """Test marker at the end of content."""
    parser = UIComponentParser()
    content = "Connect your store now! {{oauth:shopify}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert clean_content == "Connect your store now! __OAUTH_BUTTON_1__"
    assert len(components) == 1

def test_multiline_content():
    """Test parsing markers in multiline content."""
    parser = UIComponentParser()
    content = """Here's how to connect:
    
    {{oauth:shopify}}
    
    Once connected, you'll see insights."""
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert "__OAUTH_BUTTON_1__" in clean_content
    assert "{{oauth:shopify}}" not in clean_content
    assert len(components) == 1