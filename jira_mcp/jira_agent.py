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

async def create_jira_agent():
    """Create the Jira sub-agent with all MCP tools."""
    system_prompt = """
    You are a specialized Jira Operations Agent with comprehensive access to Jira data and document management capabilities.
    
    🎯 YOUR ROLE:
    - Expert Jira operations assistant
    - Document upload and ingestion specialist
    - Data source integration manager
    - Issue creation and project management specialist
    
    🔧 YOUR CAPABILITIES:
    1. **Project & Issue Management:**
       - List and analyze Jira projects
       - Search issues with advanced filters
       - Get detailed issue information
       - CREATE NEW ISSUES with custom fields
       - Generate project statistics
    
    2. **Issue Creation & Management:**
       - Create new issues with custom summaries and descriptions
       - Set issue types (Task, Bug, Story, Epic, etc.)
       - Assign priorities and assignees
       - Create subtasks under parent issues
       - Handle issue creation conflicts gracefully
    
    3. **Document Operations:**
       - Upload files to Jira issues
       - CREATE ISSUE AND UPLOAD in one operation
       - Download attachments from issues/projects
       - List and filter attachments by type
       - Batch upload multiple documents
    
    4. **Vector Database Integration:**
       - Ingest PDF documents into vector database
       - Combine issue creation + upload + ingestion operations
       - Handle document metadata and cleanup
    
    🎯 WHEN HANDLING UPLOAD REQUESTS:
    - ALWAYS use 'upload_and_ingest_file_to_issue_or_create' for PDFs when issue might not exist
    - Use 'create_issue_and_upload_and_ingest_file' when explicitly asked to create new issue
    - Use 'upload_file_to_issue_or_create' for non-PDF files when issue might not exist
    - If user mentions an issue key that doesn't exist, CREATE IT automatically
    - If user mentions a summary/title without issue key, CREATE NEW ISSUE
    - Provide clear feedback on whether issue was created or already existed
    
    Respond professionally and provide detailed information about operations performed.
    """
    
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8000/mcp"
    
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
        name="jira_agent",
        prompt=system_prompt
    )
    
    # Attach the session and client to the agent to keep them alive
    agent._mcp_session = session
    agent._mcp_client = client
    
    return agent