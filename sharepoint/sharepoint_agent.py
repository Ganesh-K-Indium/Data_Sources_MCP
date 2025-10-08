"""
SharePoint Intelligent ReAct Agent
Uses LangGraph's create_react_agent with MCP tools via streamable HTTP
Intelligently selects from 13 SharePoint MCP tools based on user prompts
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
    import socket
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    host = parsed.hostname or 'localhost'
    port = parsed.port
    
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"✅ SharePoint MCP server is up at {url}")
                return True
        except:
            pass
        await asyncio.sleep(1)
    raise TimeoutError(f"SharePoint MCP server at {url} did not respond within {timeout} seconds")


async def create_sharepoint_agent():
    """Create the SharePoint sub-agent with all MCP tools."""
    system_prompt = """
    You are a specialized SharePoint Operations Agent with comprehensive access to SharePoint data and document management capabilities.
    
    🎯 YOUR ROLE:
    - Expert SharePoint operations assistant
    - Document upload, download, and ingestion specialist
    - Data source integration manager
    - Library and file management specialist
    
    🔧 YOUR CAPABILITIES:
    
    1. **Site & Library Management:**
       - List and analyze SharePoint sites
       - Browse document libraries
       - Navigate folder structures
       - Get file and folder metadata
    
    2. **File Operations:**
       - List files with advanced filters (by type, folder, etc.)
       - Download single files or bulk PDFs
       - Upload files to libraries/folders
       - Search content across SharePoint
       - Get detailed file information
    
    3. **Document Management:**
       - Download files by name or full path
       - Upload single files or batch upload multiple files
       - Filter files by type (PDF, DOCX, etc.)
       - Organize files into folder structures
    
    4. **Vector Database Integration:**
       - Download PDFs from SharePoint
       - Ingest documents into vector database for RAG
       - Combine download + ingestion in one operation
       - Handle document metadata and cleanup
    
    5. **Search & Discovery:**
       - Search files by name, content, or metadata
       - Filter by document library or folder
       - Find files across multiple sites
    
    🎯 WHEN HANDLING REQUESTS:
    - Use 'list_sharepoint_files' to browse and filter files
    - Use 'download_sharepoint_file' for single file downloads by name
    - Use 'download_sharepoint_file_by_path' when you have the exact path
    - Use 'download_and_ingest_sharepoint_files' for PDFs that need to be indexed
    - Use 'upload_file_to_sharepoint' for single file uploads
    - Use 'bulk_upload_to_sharepoint' for multiple file uploads
    - Always check connection with 'test_sharepoint_connection' if user reports issues
    - Provide clear feedback on operations performed
    
    📋 BEST PRACTICES:
    - Always verify site and library names before operations
    - Provide clear paths when downloading or uploading
    - Inform user about file sizes and operation progress
    - Handle errors gracefully and suggest alternatives
    - Confirm successful operations with details
    
    Respond professionally and provide detailed information about operations performed.
    """
    
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8002/mcp"
    
    # Keep the client and session open for the lifetime of the agent
    client = streamablehttp_client(MCP_HTTP_STREAM_URL)
    read_stream, write_stream, _ = await client.__aenter__()
    session = ClientSession(read_stream, write_stream)
    await session.__aenter__()
    await session.initialize()
    tools = await load_mcp_tools(session)
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        name="sharepoint_agent",
        prompt=system_prompt
    )
    
    # Attach the session and client to the agent to keep them alive
    agent._mcp_session = session
    agent._mcp_client = client
    
    return agent

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    async def main():
        """Demo usage of the SharePoint agent."""
        print("\n" + "="*70)
        print("SharePoint Intelligent Agent - Demo")
        print("="*70 + "\n")
        
        # Create the agent
        agent = await create_sharepoint_agent()
        
        # Example queries
        queries = [
            "Download and ingest TESLA.pdf file from SharePoint to /Users/I8798/Desktop/Data_Sources_MCP/jira_attachments"
        ]
        
        try:
            for i, query in enumerate(queries, 1):
                print(f"\n{'─'*70}")
                print(f"Query {i}: {query}")
                print(f"{'─'*70}\n")
                
                try:
                    result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
                    response = result["messages"][-1].content
                    print(f"\n✅ Response:\n{response}\n")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    break
            
            print("\n" + "="*70)
            print("Demo Complete!")
            print("="*70 + "\n")
        
        finally:
            # Properly close the MCP session and client
            if hasattr(agent, '_mcp_session'):
                try:
                    await agent._mcp_session.__aexit__(None, None, None)
                except:
                    pass
            
            if hasattr(agent, '_mcp_client'):
                try:
                    await agent._mcp_client.__aexit__(None, None, None)
                except:
                    pass
    
    asyncio.run(main())
