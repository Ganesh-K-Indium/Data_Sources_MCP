#!/bin/bash

# Startup script to run all MCP servers and API server for Docker

echo "Starting MCP servers..."

# Start MCP servers in background
python jira_mcp/jira_mcp.py 8000 &
python confluence_mcp/confluence_mcp.py 8001 &
python sharepoint/sharepoint_mcp.py 8002 &
python local_pdf/local_pdf_mcp.py 8003 &
python gdrive/gdrive_mcp.py 8005 &

# Wait a bit for MCP servers to start
sleep 5

echo "Starting API server..."
# Start API server in foreground (this will keep the container running)
python api_server.py