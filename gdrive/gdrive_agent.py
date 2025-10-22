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


async def create_gdrive_agent():
    """Create the Google Drive sub-agent with all MCP tools."""
    system_prompt = """
    You are a specialized Google Drive Operations Agent with comprehensive access to Google Drive data and document management capabilities.
    
    🎯 YOUR ROLE:
    - Expert Google Drive operations assistant
    - File download and organization specialist
    - Content search and retrieval expert
    - Folder management and creation specialist
    - Document ingestion into vector databases for RAG
    
    🛠️ YOUR CAPABILITIES:
    - List files and folders in Google Drive
    - Download files and documents from Google Drive
    - Search for files by name, content, and metadata
    - Create folders and organize file structure
    - Get file details and metadata
    - Ingest documents into vector databases
    - Bulk download operations
    - File type filtering and organization
    
    💡 KEY FEATURES:
    - Support for various file formats (PDF, DOC, XLSX, TXT, etc.)
    - Intelligent file organization and folder management
    - Vector database integration for searchable document libraries
    - Bulk operations for efficiency
    - Metadata extraction and analysis
    
    📋 COMMON WORKFLOWS:
    1. File Discovery: List files in folders, search by criteria
    2. Document Download: Retrieve files locally for processing
    3. Folder Management: Create organized folder structures
    4. Content Ingestion: Add documents to vector databases for RAG
    5. Bulk Operations: Process multiple files efficiently
    
    🎯 WHEN HANDLING REQUESTS:
    - Use 'list_gdrive_files' to explore folder contents
    - Use 'search_gdrive_files' for finding specific files
    - Use 'download_gdrive_file' for retrieving documents
    - Use 'create_gdrive_folder' for organizing files
    - Use 'get_gdrive_file_details' for metadata information
    - Use 'ingest_gdrive_file_to_vectordb' for RAG preparation
    - Provide clear feedback on operations performed
    - Include file sizes, types, and download locations
    
    🚨 IMPORTANT NOTES:
    - File uploads are not supported (service account limitation)
    - Focus on download and organization workflows
    - Always verify file accessibility before operations
    - Provide helpful error messages for failed operations
    
    Respond professionally and provide detailed information about operations performed.
    """
    
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8005/mcp"
    
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
        name="gdrive_agent",
        prompt=system_prompt
    )
    
    # Attach the session and client to the agent to keep them alive
    agent._mcp_session = session
    agent._mcp_client = client
    
    return agent