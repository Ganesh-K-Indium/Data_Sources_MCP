import asyncio
import aiohttp
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain.chat_models import init_chat_model
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
                print(f"✅ MCP server is up at {url}")
                return True
        except:
            pass
        await asyncio.sleep(1)
    raise TimeoutError(f"MCP server at {url} did not respond within {timeout} seconds")


async def create_confluence_agent():
    """Create the Confluence sub-agent with all MCP tools."""
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
    
    🎯 WHEN HANDLING UPLOAD REQUESTS:
    - ALWAYS use 'upload_and_ingest_file_to_page_or_create' for PDFs when page might not exist
    - Use 'create_page_and_upload_and_ingest_file' when explicitly asked to create new page
    - Use 'upload_file_to_page_or_create' for non-PDF files when page might not exist
    - If user mentions a page title that doesn't exist, CREATE IT automatically
    - Provide clear feedback on whether page was created or already existed
    - Include file size and attachment information
    
    Respond professionally and provide detailed information about operations performed.
    """
    
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8001/mcp"
    
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
        name="confluence_agent",
        prompt=system_prompt
    )
    
    # Attach the session and client to the agent to keep them alive
    agent._mcp_session = session
    agent._mcp_client = client
    
    return agent