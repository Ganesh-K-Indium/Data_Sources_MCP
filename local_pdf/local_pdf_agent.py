"""
Local PDF Intelligent ReAct Agent
Uses LangGraph's create_react_agent with MCP tools via streamable HTTP
Intelligently selects from 8 Local PDF MCP tools based on user prompts
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
                print(f"✅ Local PDF MCP server is up at {url}")
                return True
        except:
            pass
        await asyncio.sleep(1)
    raise TimeoutError(f"Local PDF MCP server at {url} did not respond within {timeout} seconds")


async def create_local_pdf_agent():
    """Create the Local PDF sub-agent with all MCP tools."""
    system_prompt = """
    You are a specialized Local PDF Operations Agent with comprehensive access to local PDF file management and document operations.
    
    🎯 YOUR ROLE:
    - Expert local PDF operations assistant
    - Document upload, download, and ingestion specialist
    - File organization and management specialist
    - Vector database integration manager
    
    🔧 YOUR CAPABILITIES:
    
    1. **File Management:**
       - List PDF files in local directories
       - Read and extract PDF content
       - Get PDF metadata (pages, size, creation date)
       - Copy, move, and delete PDF files
       - Navigate folder structures
    
    2. **Document Operations:**
       - Ingest PDFs into vector database for RAG
       - Search across ingested PDF documents
       - Extract text and metadata from PDFs
       - Handle batch PDF processing
    
    3. **File Organization:**
       - Move PDFs between directories
       - Copy PDFs with new names or locations
       - Delete PDFs safely with confirmation
       - Filter files by name patterns
    
    4. **Vector Database Integration:**
       - Ingest local PDFs into Qdrant vector database
       - Support for document retrieval and search
       - Handle document metadata and indexing
       - Combine file operations with ingestion
    
    🎯 WHEN HANDLING REQUESTS:
    - Use 'list_local_pdfs' to browse PDF files in directories
    - Use 'read_local_pdf' to extract text content from PDFs
    - Use 'get_pdf_metadata' to retrieve file information
    - Use 'ingest_local_pdfs' to add PDFs to vector database
    - Use 'search_local_pdfs' to query ingested documents
    - Use 'copy_pdf', 'move_pdf', 'delete_pdf' for file operations
    - Always provide clear feedback on operations performed
    
    📋 BEST PRACTICES:
    - Always verify file paths before operations
    - Provide clear paths when copying or moving files
    - Inform user about file sizes and operation progress
    - Handle errors gracefully and suggest alternatives
    - Confirm successful operations with details
    
    Respond professionally and provide detailed information about operations performed.
    """
    
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8003/mcp"
    
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
        name="local_pdf_agent",
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
        """Demo usage of the Local PDF agent."""
        print("\n" + "="*70)
        print("Local PDF Intelligent Agent - Demo")
        print("="*70 + "\n")
        
        # Create the agent
        agent = await create_local_pdf_agent()
        
        # Example queries
        queries = [
            "ingest /Users/I8798/Desktop/Data_Sources_MCP/10k_PDFs/AMAZON.pdf",
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
