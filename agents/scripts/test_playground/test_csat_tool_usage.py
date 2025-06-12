"""Test the CSAT detail log tool with mock data"""

from datetime import date
from app.agents.database_tools import create_database_tools

def test_csat_tool():
    """Test the CSAT detail log tool"""
    
    # Create all database tools
    tools = create_database_tools()
    
    # Find the get_csat_detail_log tool
    csat_tool = None
    for tool in tools:
        if tool.name == "get_csat_detail_log":
            csat_tool = tool
            break
    
    if not csat_tool:
        print("❌ CSAT detail log tool not found!")
        return
    
    print("✅ Found get_csat_detail_log tool")
    print(f"Tool name: {csat_tool.name}")
    print(f"Tool description: {csat_tool.description}")
    
    # Test 1: Call with default parameters (yesterday)
    print("\n📋 Test 1: Default call (yesterday's data)")
    try:
        result = csat_tool.func()
        print("Result preview:")
        print(result[:500] + "..." if len(result) > 500 else result)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Call with specific date
    print("\n📋 Test 2: Specific date")
    try:
        result = csat_tool.func(date_str="2024-01-10")
        print("Result preview:")
        print(result[:500] + "..." if len(result) > 500 else result)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Call with custom threshold
    print("\n📋 Test 3: Custom threshold (only perfect scores)")
    try:
        result = csat_tool.func({
            "date_str": "2024-01-10",
            "rating_threshold": 103
        })
        print("Result preview:")
        print(result[:500] + "..." if len(result) > 500 else result)
    except Exception as e:
        print(f"Error: {e}")


def list_all_tools():
    """List all available database tools"""
    print("\n📚 All Available Database Tools:")
    tools = create_database_tools()
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}")
        print(f"   {tool.description.split('.')[0]}.")


if __name__ == "__main__":
    print("🔧 CSAT Detail Log Tool Test")
    print("=" * 50)
    
    # First list all tools
    list_all_tools()
    
    # Then test the CSAT tool
    print("\n" + "=" * 50)
    test_csat_tool()