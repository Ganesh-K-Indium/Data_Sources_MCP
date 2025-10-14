#!/usr/bin/env python3
"""
Multi-Server Runner for Data Sources MCP
Starts all MCP servers simultaneously and manages their lifecycle
"""

import subprocess
import signal
import sys
import time
import os
from pathlib import Path

# Server configurations
SERVERS = [
    {
        "name": "Jira MCP Server",
        "script": "jira_mcp/jira_mcp.py",
        "port": 8000,
        "url": "http://localhost:8000/mcp"
    },
    {
        "name": "Confluence MCP Server",
        "script": "confluence_mcp/confluence_mcp.py",
        "port": 8001,
        "url": "http://localhost:8001/mcp"
    },
    {
        "name": "SharePoint MCP Server",
        "script": "sharepoint/sharepoint_mcp.py",
        "port": 8002,
        "url": "http://localhost:8002/mcp"
    },
    {
        "name": "Google Drive MCP Server",
        "script": "gdrive/gdrive_mcp.py",
        "port": 8005,
        "url": "http://localhost:8005/mcp"
    },
    {
        "name": "Local PDF MCP Server",
        "script": "local_pdf/local_pdf_mcp.py",
        "port": 8003,
        "url": "http://localhost:8003/mcp"
    },
    {
        "name": "API Server",
        "script": "api_server.py",
        "port": 8004,
        "url": "http://localhost:8004"
    }
]

# Global list to track running processes
running_processes = []

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\n{'='*70}")
    print("🛑 SHUTDOWN SIGNAL RECEIVED - Stopping all servers...")
    print(f"{'='*70}")

    shutdown_all_servers()
    sys.exit(0)

def check_server_ready(url, timeout=10):
    """Check if a server is ready by testing the URL"""
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or 'localhost'
    port = parsed.port

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def start_server(server_config):
    """Start a single MCP server"""
    script_path = server_config["script"]
    port = server_config["port"]
    name = server_config["name"]

    print(f"🚀 Starting {name} on port {port}...")

    # Check if script exists
    if not Path(script_path).exists():
        print(f"❌ ERROR: Script not found: {script_path}")
        return None

    try:
        # Special handling for API server
        if name == "API Server":
            # API server uses uvicorn and doesn't need port argument
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
        else:
            # MCP servers take port as argument
            process = subprocess.Popen(
                [sys.executable, script_path, str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )

        # Wait for server to be ready
        if check_server_ready(server_config["url"]):
            print(f"✅ {name} is ready at {server_config['url']}")
            return process
        else:
            print(f"❌ {name} failed to start within timeout")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return None

    except Exception as e:
        print(f"❌ Failed to start {name}: {str(e)}")
        return None

def shutdown_all_servers():
    """Shutdown all running server processes"""
    if not running_processes:
        print("ℹ️  No servers running")
        return

    print(f"🛑 Stopping {len(running_processes)} server(s)...")

    for process in running_processes:
        try:
            process.terminate()
        except:
            pass

    # Wait for processes to terminate gracefully
    time.sleep(2)

    # Force kill any remaining processes
    for process in running_processes:
        try:
            if process.poll() is None:
                process.kill()
        except:
            pass

    print("✅ All servers stopped")
    running_processes.clear()

def main():
    """Main function to run all servers"""
    print(f"{'='*70}")
    print("🚀 DATA SOURCES MCP - Multi-Server Runner")
    print(f"{'='*70}")
    print(f"📋 Starting {len(SERVERS)} MCP servers...")
    print()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start all servers
        for server_config in SERVERS:
            process = start_server(server_config)
            if process:
                running_processes.append(process)
            else:
                print(f"⚠️  Continuing without {server_config['name']}")

        if not running_processes:
            print("❌ ERROR: No servers could be started!")
            return 1

        print(f"\n{'='*70}")
        print("🎉 ALL SERVERS STARTED SUCCESSFULLY!")
        print(f"{'='*70}")
        print(f"📊 Running servers: {len(running_processes)}")
        print()

        # Display server information
        for i, server_config in enumerate(SERVERS, 1):
            print(f"{i}. {server_config['name']}")
            print(f"   📍 URL: {server_config['url']}")
            print(f"   🔧 Port: {server_config['port']}")
            print()

        print("💡 Server URLs for testing:")
        for server_config in SERVERS:
            if server_config["name"] == "API Server":
                print(f"   🌐 API: {server_config['url']}")
                print(f"   📖 Docs: {server_config['url']}/docs")
            else:
                print(f"   curl {server_config['url']}")
        print()

        print("🤖 To use with main agent:")
        print("   python main_agent.py")
        print()

        print("🌐 To use the REST API:")
        print("   POST http://localhost:8004/chat")
        print("   Body: {\"message\": \"your query here\"}")
        print()

        print("⏹️  Press Ctrl+C to stop all servers")
        print(f"{'='*70}")

        # Keep the script running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n👋 Shutdown requested by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
    finally:
        shutdown_all_servers()

    return 0

if __name__ == "__main__":
    sys.exit(main())