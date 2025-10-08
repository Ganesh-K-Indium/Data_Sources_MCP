"""
LangGraph + GPT-4o Agent using Confluence MCP HTTP Streaming Server
-------------------------------------------------------------------
            print("\\n📋 Example commands:")
            print("  • Upload to new page: 'Upload /path/to/document.pdf to page Documentation in space TEAM'")
            print("  • Create page: 'Create page Meeting Notes in space PROJECT'")
            print("  • Create and upload: 'Create page JP MORGAN in space FINANCE and upload /path/to/JP_MORGAN.pdf'")
            print("  • Search content: 'Find all pages about project planning in space TEAM'")
            print("  • List attachments: 'Show all PDF attachments in space DOCS'")
            print("  • Space stats: 'Generate statistics for space TEAM'")
            print("\\n💡 NEW: I can now create pages automatically when uploading to non-existent pages!")
            print("💡 PDFs are automatically processed for vector search when uploaded")
            print("💡 Smart workflow: Upload -> Create page if needed -> Process for search")astMCP Confluence Operations server using streamable HTTP transport.
"""

import asyncio
import aiohttp
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from dotenv import load_dotenv
import os

load_dotenv()


async def wait_for_server(url: str, timeout: int = 10):
    """Wait until the MCP server is ready to accept connections."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status in (200, 404):  # 404 is fine, stream endpoint doesn't return JSON
                        print(f"✅ MCP server is up at {url}")
                        return True
        except aiohttp.ClientConnectionError:
            await asyncio.sleep(1)
    raise TimeoutError(f"MCP server at {url} did not respond within {timeout} seconds")


async def main():
    # Enhanced system prompt for Confluence operations
    system_prompt = """
    You are a specialized Confluence Operations Agent with comprehensive access to Confluence data and document management capabilities.
    
    🎯 YOUR ROLE:
    - Expert Confluence operations assistant
    - Document upload and knowledge management specialist
    - Content organization and retrieval expert
    - Page creation and content management specialist
    
    🔧 YOUR CAPABILITIES:
    1. **Space & Content Management:**
       - List and analyze Confluence spaces
       - Search content with advanced filters
       - Get detailed page/blog post information
       - Find content by title within spaces
       - CREATE NEW PAGES in spaces
    
    2. **Page Creation & Management:**
       - Create new pages with custom titles and content
       - Create pages under parent pages (hierarchical structure)
       - Smart page creation with meaningful default content
       - Handle page creation conflicts gracefully
    
    3. **Document Operations:**
       - Upload files to Confluence pages/content
       - Upload by content ID or page title
       - CREATE PAGE AND UPLOAD in one operation
       - Download attachments from pages/spaces
       - List and filter attachments by type
       - Batch upload multiple documents
    
    4. **Vector Database Integration:**
       - Ingest PDF documents into vector database
       - Combine page creation + upload + ingestion operations
       - Handle document metadata and cleanup
       - Enable enterprise search capabilities
    
    5. **Content Discovery:**
       - Generate space statistics
       - Search across multiple content types
       - Filter by author, date, content type
    
    🎯 WHEN HANDLING UPLOAD REQUESTS:
    - ALWAYS use 'upload_and_ingest_file_to_page_or_create' for PDFs when page might not exist
    - Use 'create_page_and_upload_and_ingest_file' when explicitly asked to create new page
    - Use 'upload_file_to_page_or_create' for non-PDF files when page might not exist
    - If user mentions a page title that doesn't exist, CREATE IT automatically
    - Provide clear feedback on whether page was created or already existed
    - Include file size and attachment information
    
    🎯 PAGE CREATION STRATEGY:
    - When user says "create new page" or mentions a non-existent page title, CREATE IT
    - Use meaningful default content like: "<p>This page contains documents related to [TITLE]</p>"
    - For company documents, create content like: "<p>This page contains documentation for [COMPANY_NAME]</p>"
    - Ask for parent page if hierarchical organization is needed
    - Always confirm successful page creation with web URL
    
    🎯 SMART WORKFLOW SELECTION:
    - If page doesn't exist and user wants to upload: CREATE PAGE FIRST, then upload
    - For PDF uploads: Always include vector database ingestion
    - For company documents: Add company name to metadata
    - Suggest batch operations for multiple files
    
    🎯 BEST PRACTICES:
    - Always verify space exists before creating pages
    - Use descriptive page titles and meaningful content
    - Check file size limits (25MB max for Confluence)
    - Provide meaningful comments for attachments
    - Ask for clarification if file path, space, or page details are unclear
    
    🎯 DATA SOURCE CONTEXT:
    You have access to various document types including:
    - 10K PDFs from major companies (Amazon, Google, Microsoft, etc.)
    - Financial reports and regulatory documents
    - Technical specifications and project documentation
    - Knowledge base articles and documentation
    
    When users want to upload documents to pages that don't exist, CREATE THE PAGE automatically.
    This is a key improvement - you can now handle the complete workflow seamlessly!
    
    Respond professionally and provide detailed information about operations performed.
    """
    
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8001/mcp"

    async with streamablehttp_client(MCP_HTTP_STREAM_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("✅ MCP Client Session initialized")
            tools = await load_mcp_tools(session)
            print(f"✅ Loaded {len(tools)} Confluence MCP tools via HTTP stream")
            
            # Print available tools for user reference
            print("\n🔧 Available Confluence Tools:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            agent = create_react_agent(
                model=model,
                tools=tools,
                name="confluence_agent",
                prompt=system_prompt
            )
            
            print("\n" + "="*80)
            print("🤖 CONFLUENCE OPERATIONS AGENT - Ready for Commands")
            print("="*80)
            print("📋 Example commands:")
            print("  • Upload to new page: 'Upload /path/to/document.pdf to page Documentation in space TEAM'")
            print("  • Create page: 'Create page Meeting Notes in space PROJECT'")
            print("  • Create and upload: 'Create page JP MORGAN in space FINANCE and upload /path/to/JP_MORGAN.pdf'")
            print("  • Search content: 'Find all pages about project planning in space TEAM'")
            print("  • List attachments: 'Show all PDF attachments in space DOCS'")
            print("  • Space stats: 'Generate statistics for space TEAM'")
            print("\\n💡 NEW: I can now create pages automatically when uploading to non-existent pages!")
            print("💡 PDFs are automatically processed for vector search when uploaded")
            print("💡 Smart workflow: Upload -> Create page if needed -> Process for search")
            print("\\n🔧 STANDALONE MODE: Running directly (use main_agent.py for supervisor mode)")
            print("\\nEnter your command (or 'quit' to exit): ")
            
            while True:
                try:
                    user_input = input("\n>>> ").strip()
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("👋 Goodbye!")
                        break
                    
                    if not user_input:
                        continue
                    
                    print(f"\n🧠 Processing: {user_input}")
                    print("-" * 50)
                    
                    response = await agent.ainvoke({"messages": [{"role": "user", "content": user_input}]})
                    
                    # Extract and display the final response
                    final_message = response['messages'][-1]
                    print("\n🤖 Response:")
                    print(final_message.content)
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}")
                    continue

if __name__ == "__main__":
    asyncio.run(main())