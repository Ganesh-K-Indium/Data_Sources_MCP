"""
FastAPI Server for Data Sources MCP Supervisor Agent
Exposes the supervisor agent functionality via REST API
"""

import asyncio
import uvicorn
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
    create_supervisor
)
from langchain_openai import ChatOpenAI

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

# FastAPI app
app = FastAPI(
    title="Data Sources MCP Supervisor API",
    description="REST API for the Data Sources MCP Supervisor Agent",
    version="1.0.0"
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
    global supervisor, agents_initialized

    if agents_initialized:
        return

    try:
        print("🚀 Initializing Data Sources MCP Supervisor Agent...")

        # Wait for MCP servers to be ready
        print("⏳ Waiting for MCP servers...")
        await wait_for_server("http://localhost:8000/mcp")  # Jira
        await wait_for_server("http://localhost:8001/mcp")  # Confluence
        await wait_for_server("http://localhost:8002/mcp")  # SharePoint
        await wait_for_server("http://localhost:8003/mcp")  # Local PDF

        # Create sub-agents
        print("🔧 Creating sub-agents...")
        confluence_agent = await create_confluence_agent()
        jira_agent = await create_jira_agent()
        sharepoint_agent = await create_sharepoint_agent()
        local_pdf_agent = await create_local_pdf_agent()

        print("✅ Sub-agents created successfully")

        # Create supervisor
        supervisor_prompt = (
            "You are a supervisor managing four specialized data source agents:\n\n"
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
            "🎯 TASK ROUTING GUIDELINES:\n"
            "- For wiki/documentation/knowledge base tasks → confluence_agent\n"
            "- For issue tracking/project management/tickets → jira_agent\n"
            "- For document uploads/downloads and file management from SharePoint → sharepoint_agent\n"
            "- For local PDF file operations, ingestion, and search → local_pdf_agent\n"
            "- For document uploads: route based on destination (Confluence pages vs Jira issues vs SharePoint libraries)\n"
            "- For searches: route based on system (Confluence content vs Jira issues vs SharePoint files vs local PDFs)\n"
            "- For statistics: route based on system (space stats vs project stats vs library stats)\n"
            "- For vector database ingestion: Jira related files → jira_agent, Confluence related files → confluence_agent, SharePoint files → sharepoint_agent, local PDFs → local_pdf_agent\n\n"
            "Assign work to one agent at a time, do not call agents in parallel.\n"
            "Do not do any work yourself - always delegate to the appropriate specialist agent.\n"
            "Provide clear context about why you're routing to a specific agent."
        )

        global supervisor
        supervisor = create_supervisor(
            model=ChatOpenAI(temperature=0, model_name="gpt-4o"),
            agents=[jira_agent, confluence_agent, sharepoint_agent, local_pdf_agent],
            prompt=supervisor_prompt,
            add_handoff_back_messages=True,
            output_mode="full_history",
        ).compile()

        agents_initialized = True
        print("✅ Supervisor agent initialized successfully")

    except Exception as e:
        print(f"❌ Failed to initialize agents: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize agents on startup"""
    await initialize_agents()

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {"message": "Data Sources MCP Supervisor API", "status": "running"}

@app.get("/health", response_model=StatusResponse, tags=["Health"])
async def health_check():
    """Check the health status of the API and all MCP servers"""
    import socket
    from urllib.parse import urlparse

    def check_server(url):
        try:
            parsed = urlparse(url)
            host = parsed.hostname or 'localhost'
            port = parsed.port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    servers_status = {
        "jira": check_server("http://localhost:8000/mcp"),
        "confluence": check_server("http://localhost:8001/mcp"),
        "sharepoint": check_server("http://localhost:8002/mcp"),
        "local_pdf": check_server("http://localhost:8003/mcp")
    }

    all_servers_ready = all(servers_status.values())

    status = "healthy" if (all_servers_ready and agents_initialized) else "unhealthy"

    return StatusResponse(
        status=status,
        servers_ready=servers_status,
        agents_ready=agents_initialized,
        timestamp=datetime.now().isoformat()
    )

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

        # Invoke supervisor
        response = await supervisor.ainvoke({"messages": [{"role": "user", "content": request.message}]})

        # Extract and display the final response
        final_message = None
        for msg in reversed(response['messages']):
            if msg.type == 'ai' and msg.name != 'supervisor' and not msg.content.startswith('Transferring back') and not msg.content.startswith('Successfully transferred'):
                final_message = msg
                break
        if final_message is None:
            final_message = response['messages'][-1]

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
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting Data Sources MCP API Server...")
    print("📍 API will be available at: http://localhost:8004")
    print("📖 API documentation at: http://localhost:8004/docs")

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8005,
        reload=False,
        log_level="info"
    )