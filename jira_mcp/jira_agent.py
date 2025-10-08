"""
LangGraph + GPT-4.1 Agent using Jira MCP HTTP Streaming Server (fixed)
----------------------------------------------------------------------
Connects to FastMCP Jira Operations server using streamable HTTP transport.
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
    # Enhanced system prompt for Jira operations
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
    
    🎯 ISSUE CREATION STRATEGY:
    - When user says "create new issue" or mentions a non-existent issue, CREATE IT
    - Use meaningful descriptions like: "Issue created for [SUMMARY] with document attachments"
    - For company documents, create descriptions like: "Document repository for [COMPANY_NAME] materials"
    - Choose appropriate issue types: Task (default), Bug (for problems), Story (for features)
    - Set reasonable priorities: Medium (default), High (urgent), Low (nice-to-have)
    - Always confirm successful issue creation with web URL
    
    🎯 SMART WORKFLOW SELECTION:
    - If issue doesn't exist and user wants to upload: CREATE ISSUE FIRST, then upload
    - For PDF uploads: Always include vector database ingestion
    - For company documents: Add company name to metadata
    - Suggest batch operations for multiple files
    
    🎯 BEST PRACTICES:
    - Always validate issue exists before uploading OR auto-create if needed
    - Check file size limits (10MB max for Jira)
    - Provide meaningful error messages
    - Ask for clarification if file path or project key is unclear
    - Use descriptive issue summaries and meaningful descriptions
    
    🎯 DATA SOURCE CONTEXT:
    You have access to various document types including:
    - 10K PDFs from major companies (Amazon, Google, Microsoft, etc.)
    - Financial reports and regulatory documents
    - Technical specifications and project documentation
    
    When users want to upload documents to issues that don't exist, CREATE THE ISSUE automatically.
    This is a key improvement - you can now handle the complete workflow seamlessly!
    
    Respond professionally and provide detailed information about operations performed.
    """
    
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8000/mcp"

    async with streamablehttp_client(MCP_HTTP_STREAM_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("✅ MCP Client Session initialized")
            tools = await load_mcp_tools(session)
            print(f"✅ Loaded {len(tools)} Jira MCP tools via HTTP stream")
            
            # Print available tools for user reference
            print("\n🔧 Available Jira Tools:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            agent = create_react_agent(
                model=model,
                tools=tools,
                name="JiraOperationsAgent",
                prompt=system_prompt
            )
            
            print("\n" + "="*80)
            print("🤖 JIRA OPERATIONS AGENT - Ready for Commands")
            print("="*80)
            print("\n📋 Example commands:")
            print("  • Upload file: 'Upload /path/to/document.pdf to issue PROJ-123'")
            print("  • Search issues: 'Find all bugs in project DEMO with high priority'")
            print("  • List attachments: 'Show all PDF attachments in project DEMO'")
            print("  • Project stats: 'Generate statistics for project DEMO'")
            print("\n💡 You can also specify company names for metadata when uploading PDFs")
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
