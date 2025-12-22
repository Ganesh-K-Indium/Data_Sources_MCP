"""
FastAPI Server for Data Sources MCP Supervisor Agent
Exposes the supervisor agent functionality via REST API
"""

import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os
from datetime import datetime

# Import the existing agent functionality
from main_agent import (
    wait_for_server,
    create_confluence_agent,
    create_jira_agent,
    create_sharepoint_agent,
    create_local_pdf_agent,
    create_gdrive_agent
)

from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    success: bool

class StatusResponse(BaseModel):
    status: str
    servers_ready: Dict[str, bool]
    agents_ready: bool
    timestamp: str

# Global variables for agent management
supervisor = None
agents_initialized = False
saver = None  # Add saver to global scope
saver_cm = None  # Store context manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    global supervisor, agents_initialized, saver, saver_cm
    try:
        await initialize_agents()
        yield
    finally:
        # Shutdown
        if saver_cm is not None:
            try:
                await saver_cm.__aexit__(None, None, None)
                print("✅ Memory saver cleaned up successfully")
            except Exception as e:
                print(f"⚠️ Error cleaning up memory saver: {e}")


# FastAPI app with lifespan
app = FastAPI(
    title="Data Sources MCP Supervisor API",
    description="REST API for the Data Sources MCP Supervisor Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def initialize_agents():
    """Initialize all agents and supervisor on startup"""
    global supervisor, agents_initialized, saver, saver_cm

    if agents_initialized:
        return

    try:
        print("🚀 Initializing Data Sources MCP Supervisor Agent...")
        
        # Initialize memory saver
        print("💾 Initializing SQLite memory...")
        connection_string = os.getenv("SQLITE_CONNECTION_STRING", "sqlite:///checkpoint.db")
        saver_cm = AsyncSqliteSaver.from_conn_string(connection_string)
        saver = await saver_cm.__aenter__()
        await saver.setup()  # Creates tables if needed
        print("✅ Memory initialized successfully")

        # Wait for MCP servers to be ready
        print("⏳ Waiting for MCP servers...")
        await wait_for_server("http://localhost:8000/mcp")  # Jira
        await wait_for_server("http://localhost:8001/mcp")  # Confluence
        await wait_for_server("http://localhost:8002/mcp")  # SharePoint
        await wait_for_server("http://localhost:8003/mcp")  # Local PDF
        await wait_for_server("http://localhost:8005/mcp")  # Google Drive

        # Create sub-agents
        print("🔧 Creating sub-agents...")
        confluence_agent = await create_confluence_agent(checkpointer=saver)
        jira_agent = await create_jira_agent(checkpointer=saver)
        sharepoint_agent = await create_sharepoint_agent(checkpointer=saver)
        local_pdf_agent = await create_local_pdf_agent(checkpointer=saver)
        gdrive_agent = await create_gdrive_agent(checkpointer=saver)

        print("✅ Sub-agents created successfully")

        # Create supervisor
        supervisor_prompt = (
            "You are a supervisor managing five specialized data source agents:\n\n"
            "- **confluence_agent**: Expert in Confluence operations including page creation, content search, "
            "document uploads, space management, and knowledge base operations. Assign tasks related to "
            "Confluence spaces, pages, content creation, document management, and wiki operations.\n\n"
            "- **jira_agent**: Expert in Jira operations including issue creation, project management, "
            "ticket handling, document attachments, and issue tracking. Assign tasks related to "
            "Jira projects, issues, bug tracking, task management, and project workflows.\n\n"
            "- **sharepoint_agent**: Expert in SharePoint operations including file uploads, downloads, "
            "document library management, content search, and document ingestion into vector databases. "
            "Assign tasks related to SharePoint sites, document libraries, file operations, and RAG pipeline ingestion.\n\n"
            "- **local_pdf_agent**: Expert in local PDF operations including file management, content extraction, "
            "document ingestion into vector databases, and search across ingested PDFs. Assign tasks related to "
            "local PDF files, document organization, vector database integration, and PDF content processing.\n\n"
            "- **gdrive_agent**: Expert in Google Drive operations including file downloads, folder management, "
            "content search, document organization, and document ingestion into vector databases. Assign tasks "
            "related to Google Drive files, folder creation, file retrieval, bulk downloads, and RAG pipeline ingestion.\n\n"
            "🎯 TASK ROUTING GUIDELINES:\n"
            "- For wiki/documentation/knowledge base tasks → confluence_agent\n"
            "- For issue tracking/project management/tickets → jira_agent\n"
            "- For document uploads/downloads and file management from SharePoint → sharepoint_agent\n"
            "- For local PDF file operations, ingestion, and search → local_pdf_agent\n"
            "- For Google Drive file operations, downloads, and folder management → gdrive_agent\n"
            "- For document uploads: route based on destination (Confluence pages vs Jira issues vs SharePoint libraries)\n"
            "- For searches: route based on system (Confluence content vs Jira issues vs SharePoint files vs local PDFs vs Google Drive)\n"
            "- For statistics: route based on system (space stats vs project stats vs library stats)\n"
            "- For vector database ingestion: Jira related files → jira_agent, Confluence related files → confluence_agent, SharePoint files → sharepoint_agent, local PDFs → local_pdf_agent, Google Drive files → gdrive_agent\n\n"
            "🧠 INTELLIGENT RESPONSE GUIDELINES:\n"
            "- For follow-up questions about previous results (e.g., 'how many?', 'count them', 'what did I ask?'), analyze the conversation history and answer directly without re-running tools\n"
            "- When user asks analytical questions about data already retrieved, perform the analysis yourself (count, summarize, compare) instead of delegating\n"
            "- Only delegate to agents when NEW data needs to be fetched from external systems\n"
            "- Remember user details (name, preferences) from conversation history and use them in responses\n\n"
            "Assign work to one agent at a time, do not call agents in parallel.\n"
            "Do not do any work yourself for data retrieval - always delegate to the appropriate specialist agent.\n"
            "Provide clear context about why you're routing to a specific agent."
        )

        global supervisor
        supervisor_graph = create_supervisor(
            model=ChatOpenAI(temperature=0, model_name="gpt-4o"),
            agents=[jira_agent, confluence_agent, sharepoint_agent, local_pdf_agent, gdrive_agent],
            prompt=supervisor_prompt,
            add_handoff_back_messages=True,
            output_mode="full_history",
        )
        supervisor = supervisor_graph.compile(checkpointer=saver)

        agents_initialized = True
        print("✅ Supervisor agent initialized successfully")

    except Exception as e:
        print(f"❌ Failed to initialize agents: {str(e)}")
        raise


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {"message": "Data Sources MCP Supervisor API", "status": "running"}

@app.get("/health", response_model=StatusResponse, tags=["Health"])
async def health_check():
    """
    Comprehensive health check for the API and all MCP servers.
    
    Checks:
    - All 5 MCP servers are responding
    - Agents are initialized
    - Database connectivity (SQLite)
    - Supervisor agent is ready
    
    Returns:
    - status: "healthy" or "unhealthy"
    - servers_ready: Status of each MCP server
    - agents_ready: Whether supervisor and sub-agents are initialized
    - database_ready: Database connectivity status
    - timestamp: ISO formatted timestamp
    """
    import socket
    from urllib.parse import urlparse

    def check_server(url):
        """Check if a server is responding on its port"""
        try:
            parsed = urlparse(url)
            host = parsed.hostname or 'localhost'
            port = parsed.port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            print(f"❌ Server check failed for {url}: {str(e)}")
            return False

    async def check_database():
        """Check SQLite database connectivity"""
        try:
            connection_string = os.getenv("SQLITE_CONNECTION_STRING", "sqlite:///checkpoint.db")
            if not connection_string:
                return False
            
            # For SQLite, extract the file path from the connection string
            if connection_string.startswith("sqlite:///"):
                db_path = connection_string[10:]  # Remove 'sqlite:///'
            else:
                db_path = connection_string
            
            # Try to create a connection
            import sqlite3
            import asyncio
            
            def test_connection():
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT 1')
                    cursor.fetchone()
                    conn.close()
                    return True
                except Exception as e:
                    print(f"❌ Database check failed: {str(e)}")
                    return False
            
            # Run sync test in thread
            result = await asyncio.to_thread(test_connection)
            return result
        except Exception as e:
            print(f"❌ Database check error: {str(e)}")
            return False

    # Check all MCP servers
    servers_status = {
        "jira": check_server("http://localhost:8000/mcp"),
        "confluence": check_server("http://localhost:8001/mcp"),
        "sharepoint": check_server("http://localhost:8002/mcp"),
        "local_pdf": check_server("http://localhost:8003/mcp"),
        "gdrive": check_server("http://localhost:8005/mcp")
    }

    # Check database
    database_ready = await check_database()

    # Determine overall health
    all_servers_ready = all(servers_status.values())
    overall_healthy = all_servers_ready and agents_initialized and database_ready and supervisor is not None

    status = "healthy" if overall_healthy else "unhealthy"

    # Enhanced status response
    response_data = {
        "status": status,
        "servers_ready": servers_status,
        "agents_ready": agents_initialized,
        "timestamp": datetime.now().isoformat()
    }
    
    # Add database status if available
    if hasattr(StatusResponse, 'database_ready'):
        response_data["database_ready"] = database_ready

    return StatusResponse(**response_data)

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_agent(request: ChatRequest, background_tasks: BackgroundTasks):
    """Send a message to the supervisor agent and get a response"""

    if not agents_initialized or supervisor is None:
        raise HTTPException(
            status_code=503,
            detail="Agents not initialized. Please check server status."
        )

    try:
        # Generate session ID if not provided
        session_id = request.session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"🧠 Processing request: {request.message[:100]}...")

        # Get the current state to know how many messages exist
        current_state = await supervisor.aget_state(config={"configurable": {"thread_id": session_id}})
        messages_before = len(current_state.values.get('messages', [])) if current_state.values else 0

        # Invoke supervisor with thread_id for memory persistence
        # Use HumanMessage to ensure proper message handling
        response = await supervisor.ainvoke(
            {"messages": [HumanMessage(content=request.message)]},
            config={"configurable": {"thread_id": session_id}}
        )

        # Extract only NEW messages from this turn
        all_messages = response['messages']
        new_messages = all_messages[messages_before:] if messages_before > 0 else all_messages
        
        # Find the last AI message from the new messages that is not a transfer/handoff
        final_message = None
        for msg in reversed(new_messages):
            if msg.type == 'ai' and msg.name != 'supervisor' and not msg.content.startswith('Transferring back') and not msg.content.startswith('Successfully transferred'):
                final_message = msg
                break
        
        # Fallback to last new message if no suitable AI message found
        if final_message is None and new_messages:
            final_message = new_messages[-1]
        elif final_message is None:
            final_message = all_messages[-1]

        # Save response to file in background
        background_tasks.add_task(save_response_to_file, response, session_id)

        return ChatResponse(
            response=final_message.content,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            success=True
        )

    except Exception as e:
        print(f"❌ Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

def save_response_to_file(response, session_id):
    """Save response to JSON file"""
    try:
        def serialize_response(obj):
            try:
                if isinstance(obj, dict):
                    return {k: serialize_response(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_response(item) for item in obj]
                elif isinstance(obj, (str, int, float, bool, type(None))):
                    return obj
                elif hasattr(obj, 'dict') and callable(getattr(obj, 'dict', None)):
                    return obj.model_dump()
                elif hasattr(obj, '__dict__'):
                    return serialize_response(obj.__dict__)
                else:
                    return str(obj)
            except Exception:
                return str(obj)

        responses_dir = os.path.join(os.path.dirname(__file__), "responses")
        os.makedirs(responses_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_response_{session_id}_{timestamp}.json"
        filepath = os.path.join(responses_dir, filename)
        with open(filepath, "w") as f:
            json.dump(serialize_response(response), f, indent=4)
        print(f"📁 API response saved to {filepath}")
    except Exception as e:
        print(f"❌ Failed to save response: {str(e)}")

@app.get("/capabilities", tags=["Info"])
async def get_capabilities():
    """Get information about available capabilities"""
    return {
        "confluence_operations": [
            "Create and manage Confluence pages",
            "Upload documents to wikis and knowledge bases",
            "Search content across Confluence spaces",
            "Generate space statistics and content reports",
            "Download and organize documentation"
        ],
        "jira_operations": [
            "Create and manage Jira issues and projects",
            "Upload attachments to tickets and issues",
            "Search and filter project issues",
            "Generate project statistics and reports",
            "Track bugs, tasks, and project workflows"
        ],
        "sharepoint_operations": [
            "Upload and download files from SharePoint libraries",
            "Manage document libraries and folders",
            "Search content across SharePoint sites",
            "Ingest documents into vector databases for RAG",
            "Bulk operations and file synchronization"
        ],
        "local_pdf_operations": [
            "List and manage local PDF files",
            "Extract text and metadata from PDFs",
            "Ingest PDFs into vector databases for RAG",
            "Search across ingested PDF documents",
            "Copy, move, and organize PDF files"
        ],
        "google_drive_operations": [
            "List and manage Google Drive files and folders",
            "Download files from Google Drive",
            "Create new folders in Google Drive",
            "Search across Google Drive content",
            "Ingest PDFs from Google Drive into vector databases for RAG"
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting Data Sources MCP API Server...")
    print("📍 API will be available at: http://localhost:8004")
    print("📖 API documentation at: http://localhost:8006/docs")

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8006,
        reload=False,
        log_level="info"
    )