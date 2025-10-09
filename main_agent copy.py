"""
Main LangGraph Supervisor Agent for Data Sources MCP
---------------------------------------------------
Manages Confluence and Jira agents as specialized sub-agents.
Uses langgraph-supervisor to coordinate work between agents.
"""

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
from confluence_mcp.confluence_agent import create_confluence_agent
from jira_mcp.jira_agent import create_jira_agent
from sharepoint.sharepoint_agent import create_sharepoint_agent
from local_pdf.local_pdf_agent import create_local_pdf_agent
import os
from datetime import datetime
import json

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

async def main():
    """Main supervisor agent that coordinates Confluence and Jira sub-agents."""
    
    print("🚀 Initializing Data Sources MCP Supervisor Agent...")
    print("=" * 80)
    
    # Wait for both MCP servers to be ready
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
    supervisor = create_supervisor(
        model=ChatOpenAI(temperature=0, model_name="gpt-4.1"),
        agents=[jira_agent, confluence_agent,sharepoint_agent, local_pdf_agent],
        prompt=(
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
        ),
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    
    print("\n" + "="*80)
    print("🤖 DATA SOURCES MCP SUPERVISOR AGENT - Ready for Commands")
    print("="*80)
    print("\n📋 What I can help you with:")
    print("\n🔗 CONFLUENCE OPERATIONS:")
    print("  • Create and manage Confluence pages")
    print("  • Upload documents to wikis and knowledge bases")
    print("  • Search content across Confluence spaces")
    print("  • Generate space statistics and content reports")
    print("  • Download and organize documentation")
    
    print("\n🎫 JIRA OPERATIONS:")
    print("  • Create and manage Jira issues and projects")
    print("  • Upload attachments to tickets and issues")
    print("  • Search and filter project issues")
    print("  • Generate project statistics and reports")
    print("  • Track bugs, tasks, and project workflows")
    
    print("\n📁 SHAREPOINT OPERATIONS:")
    print("  • Upload and download files from SharePoint libraries")
    print("  • Manage document libraries and folders")
    print("  • Search content across SharePoint sites")
    print("  • Ingest documents into vector databases for RAG")
    print("  • Bulk operations and file synchronization")
    
    print("\n📄 LOCAL PDF OPERATIONS:")
    print("  • List and manage local PDF files")
    print("  • Extract text and metadata from PDFs")
    print("  • Ingest PDFs into vector databases for RAG")
    print("  • Search across ingested PDF documents")
    print("  • Copy, move, and organize PDF files")
    
    print("\n🤖 INTELLIGENT ROUTING:")
    print("  • I automatically route your requests to the right specialist")
    print("  • Support for complex workflows across all four systems")
    
    
    print("\nEnter your command (or 'quit' to exit): ")
    
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
            
            # Invoke supervisor
            response = await supervisor.ainvoke({"messages": [{"role": "user", "content": user_input}]})
            
            # Extract and display the final response
            # Find the last AI message that is not a handoff or transfer message
            final_message = None
            for msg in reversed(response['messages']):
                if msg.type == 'ai' and msg.name != 'supervisor' and not msg.content.startswith('Transferring back') and not msg.content.startswith('Successfully transferred'):
                    final_message = msg
                    break
            if final_message is None:
                final_message = response['messages'][-1]
            
            print("\n🤖 Response:")
            print(final_message.content)

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
            filename = f"response_{timestamp}.json"
            filepath = os.path.join(responses_dir, filename)
            with open(filepath, "w") as f:
                json.dump(serialize_response(response), f, indent=4)
            print(f"📁 Response saved to {filepath}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            continue


if __name__ == "__main__":
    asyncio.run(main())