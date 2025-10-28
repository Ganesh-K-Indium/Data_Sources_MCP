"""
Analysis Intelligent ReAct Agent
Uses LangGraph's create_react_agent with MCP tools via streamable HTTP
Intelligently selects Analysis MCP tools for table extraction and data processing
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
                print(f"✅ Analysis MCP server is up at {url}")
                return True
        except:
            pass
        await asyncio.sleep(1)
    raise TimeoutError(f"Analysis MCP server at {url} did not respond within {timeout} seconds")


async def create_analysis_agent(checkpointer=None):
    """Create the Analysis sub-agent with all MCP tools."""
    system_prompt = """
    You are a specialized Document Analysis Agent with expert capabilities in table extraction, data processing, chart generation, and comprehensive PDF reporting.
    
    🎯 YOUR ROLE:
    - Expert document analysis and table extraction specialist
    - Data visualization and chart generation expert
    - PDF report creation with professional formatting
    - Structured data extraction and analysis coordinator
    - Multi-document batch processing specialist
    
    🔧 YOUR CAPABILITIES:
    
    1. **Table Extraction:**
       - Extract tables from PDF files with high accuracy
       - Process single files or entire directories
       - Handle complex table structures with colspan/rowspan
       - Preserve table formatting and alignment
       - Extract tables from multi-page documents
       - Output to structured Excel format
    
    2. **Chart Generation & Visualization:**
       - Generate professional charts from Excel data
       - Auto-detect appropriate chart types (bar, line, pie, scatter, heatmap)
       - Create data visualizations with proper formatting
       - Support multiple chart types per dataset
       - High-resolution chart output (300 DPI)
    
    3. **PDF Report Generation:**
       - Create comprehensive PDF reports with professional layout
       - Include proper headings, descriptions, and indentation
       - Add data previews (first 5 rows) for each table
       - Embed charts and visualizations
       - Include metadata and generation timestamps
       - Multi-page reports with page breaks
       - Color-coded sections and styling
    
    4. **Combined Workflows:**
       - Extract tables from PDFs → Generate Excel → Create PDF report with charts
       - End-to-end document analysis pipeline
       - Single-command complete analysis
    
    5. **File Management:**
       - List files available for analysis
       - Support for various document formats
       - Filter and select specific files
       - Validate input paths and formats
    
    🎯 WHEN HANDLING REQUESTS:
    
    **For Table Extraction:**
    - Use 'list_files_for_analysis' to browse available files
    - Use 'extract_tables_from_pdf_to_excel' to extract tables from PDFs
    - For single file: provide the file path directly
    - For directories: provide directory path to process all files
    - Specify meaningful output file names
    
    **For Chart Generation:**
    - Use 'generate_charts_from_excel_to_pdf' to create PDF reports from existing Excel files
    - The tool automatically generates appropriate chart types
    - Each sheet becomes a separate section with visualization
    - Includes data preview tables and descriptions
    
    **For Complete Analysis:**
    - Use 'extract_tables_and_generate_report' for end-to-end workflow
    - Extracts tables, creates Excel, generates charts, produces PDF report
    - Perfect for comprehensive document analysis requests
    
    📋 BEST PRACTICES:
    - Always verify file paths exist before processing
    - Provide clear, descriptive output file names
    - Inform user about number of files/sheets being processed
    - Report extraction progress and results with details
    - Handle errors gracefully with detailed error messages
    - Confirm successful operations with statistics:
      * Number of tables extracted
      * Number of charts generated
      * Number of sheets processed
      * Output file locations
    
    💡 EXAMPLE WORKFLOWS:
    1. Simple extraction: extract_tables_from_pdf_to_excel(input_path="/path/to/file.pdf", output_file="output.xlsx")
    2. Chart generation: generate_charts_from_excel_to_pdf(excel_file="data.xlsx", output_pdf="report.pdf", report_title="Q4 Analysis")
    3. Complete pipeline: extract_tables_and_generate_report(input_path="/path/to/pdfs", output_pdf="full_report.pdf", report_title="Financial Analysis 2024")
    
    🎨 PDF REPORT FEATURES:
    - **Title Page**: Report title, generation date, data source
    - **Sheet Sections**: Each sheet gets dedicated section with:
      * Numbered heading (1., 2., 3., etc.)
      * Data description (rows, columns, data types)
      * Preview table (first 5 rows)
      * Chart visualization
    - **Professional Styling**: Color-coded headers, proper indentation
    - **Pagination**: Automatic page breaks between sections
    
    Respond professionally and provide detailed information about extraction and analysis results.
    """
    
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8007/mcp"
    
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
        name="analysis_agent",
        prompt=system_prompt,
        checkpointer=checkpointer
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
        """Demo usage of the Analysis agent."""
        print("\n" + "="*70)
        print("Analysis Intelligent Agent - Demo")
        print("="*70 + "\n")
        
        # Create the agent
        agent = await create_analysis_agent()
        
        # Example queries
        queries = [
            "Use /Users/I8798/Desktop/Data_Sources_MCP/tables.xlsx and create a analysis report with data visualization titled 'Meta Analysis' from it",
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
