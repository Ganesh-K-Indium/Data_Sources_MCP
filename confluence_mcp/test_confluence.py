"""
Test script for Confluence MCP Tools
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_confluence_mcp():
    """Test the Confluence MCP tools functionality."""
    
    # Check if environment variables are set
    required_vars = ['CONFLUENCE_URL', 'CONFLUENCE_USERNAME', 'CONFLUENCE_API_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file")
        return
    
    print("✅ Environment variables are configured")
    
    try:
        # Import and test basic functionality
        from utils import ConfluenceUtils
        
        print("🔧 Testing Confluence client connection...")
        utils = ConfluenceUtils()
        
        # Test basic API connection
        spaces_result = utils.confluence_client.get_spaces(limit=5)
        spaces = spaces_result.get('results', [])
        
        if spaces:
            print(f"✅ Successfully connected to Confluence!")
            print(f"   Found {len(spaces)} accessible spaces:")
            for space in spaces[:3]:  # Show first 3 spaces
                print(f"   - {space.get('key', 'N/A')}: {space.get('name', 'N/A')}")
            
            # Test content search on first space
            if spaces:
                first_space_key = spaces[0].get('key')
                print(f"\n🔍 Testing content search in space '{first_space_key}'...")
                
                filter_obj = utils.create_content_filter(
                    space_key=first_space_key,
                    content_type='page'
                )
                cql = utils.build_cql_from_filter(filter_obj)
                print(f"   Generated CQL: {cql}")
                
                content_result = utils.confluence_client.search_content(cql, limit=3)
                content_items = content_result.get('results', [])
                
                if content_items:
                    print(f"✅ Found {len(content_items)} content items")
                    for content in content_items:
                        print(f"   - {content.get('title', 'N/A')} (ID: {content.get('id', 'N/A')})")
                else:
                    print("   No content found in this space")
        else:
            print("⚠️  No accessible spaces found. Check permissions.")
            
    except Exception as e:
        print(f"❌ Error testing Confluence connection: {str(e)}")
        print("   Please check your credentials and network connection")
        return
    
    print("\n🎉 Confluence MCP tools test completed!")
    print("\nNext steps:")
    print("1. Start the MCP server: python confluence_mcp.py")
    print("2. Run the agent: python confluence_agent.py")


if __name__ == "__main__":
    asyncio.run(test_confluence_mcp())