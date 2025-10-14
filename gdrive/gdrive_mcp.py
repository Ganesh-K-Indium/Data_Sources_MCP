"""
Google Drive MCP Tools Registry
Defines MCP tools for Google Drive operations using FastMCP
10 tools for listing, downloading, searching files, and creating folders

Note: File upload operations disabled - service accounts cannot upload files to personal Google Drive
      However, creating folders works fine!
"""
import json
import os
import sys
import traceback
from typing import Optional, List
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Google Drive MCP Server")


# Helper functions
def _get_gdrive_client():
    """Get Google Drive client instance"""
    try:
        from .utils import GoogleDriveClient
    except ImportError:
        # Fallback for direct execution
        from utils import GoogleDriveClient
    return GoogleDriveClient()


@mcp.tool()
def list_gdrive_files(
    folder_name: str = "root",
    file_types: Optional[List[str]] = None
) -> str:
    """
    Lists files in a Google Drive folder.
    
    Args:
        folder_name: Folder name or "root" for root directory (default: "root")
        file_types: Filter by file types (e.g., ["pdf", "docx"])
    
    Returns:
        JSON string with list of files (names, IDs, sizes, modified dates)
    """
    try:
        client = _get_gdrive_client()
        
        # Handle file_types parameter - convert string to list if needed
        if file_types and isinstance(file_types, str):
            file_types = [file_types]
        
        # Find folder ID by name if not "root"
        folder_id = "root"
        if folder_name != "root":
            folder_id = client.find_folder_by_name(folder_name)
            if not folder_id:
                return json.dumps({
                    "success": False,
                    "error": f"Folder not found: {folder_name}"
                })
        
        files = client.list_files(
            folder_id=folder_id,
            file_types=file_types
        )
        return json.dumps({
            "success": True,
            "files": files,
            "count": len(files)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def list_gdrive_folders(parent_folder_name: str = "root") -> str:
    """
    Lists folders in Google Drive or within a specific folder.
    
    Args:
        parent_folder_name: Parent folder name or "root" for root directory (default: "root")
    
    Returns:
        JSON string with list of folders (names and IDs)
    """
    try:
        client = _get_gdrive_client()
        
        # Find parent folder ID by name if not "root"
        parent_id = "root"
        if parent_folder_name != "root":
            parent_id = client.find_folder_by_name(parent_folder_name)
            if not parent_id:
                return json.dumps({
                    "success": False,
                    "error": f"Parent folder not found: {parent_folder_name}"
                })
        
        folders = client.list_folders(parent_folder_id=parent_id)
        return json.dumps({
            "success": True,
            "folders": folders,
            "count": len(folders)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def download_gdrive_file(
    file_name: str,
    destination_path: str,
    folder_name: Optional[str] = None
) -> str:
    """
    Downloads a specific file from Google Drive by name.
    
    Args:
        file_name: Name of the file to download
        destination_path: Local path to save the file
        folder_name: Name of the folder containing the file (optional)
    
    Returns:
        JSON string with success message and local file path
    """
    try:
        client = _get_gdrive_client()
        
        # Find the file by name
        file_info = client.find_file_by_name(file_name, folder_name)
        if not file_info:
            folder_msg = f" in folder '{folder_name}'" if folder_name else ""
            return json.dumps({
                "success": False,
                "error": f"File not found: {file_name}{folder_msg}"
            })
        
        # Download using the file ID
        path = client.download_file(
            file_id=file_info["id"],
            destination_path=destination_path
        )
        return json.dumps({
            "success": True,
            "message": "File downloaded successfully",
            "path": path,
            "file_info": file_info
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def download_gdrive_pdfs(
    folder_name: str = "root",
    destination_folder: str = "./downloads"
) -> str:
    """
    Downloads all PDF files from a Google Drive folder.
    
    Args:
        folder_name: Folder name or "root" for root directory (default: "root")
        destination_folder: Local folder to save PDFs (default: "./downloads")
    
    Returns:
        JSON string with list of downloaded files and their paths
    """
    try:
        client = _get_gdrive_client()
        
        # Find folder ID by name if not "root"
        folder_id = "root"
        if folder_name != "root":
            folder_id = client.find_folder_by_name(folder_name)
            if not folder_id:
                return json.dumps({
                    "success": False,
                    "error": f"Folder not found: {folder_name}"
                })
        
        # List all PDF files
        files = client.list_files(
            folder_id=folder_id,
            file_types=["pdf"]
        )
        
        if not files:
            return json.dumps({
                "success": True,
                "message": "No PDF files found",
                "files": []
            })
        
        # Download each PDF
        downloaded_files = []
        for file_info in files:
            dest_path = os.path.join(destination_folder, file_info["name"])
            client.download_file(file_info["id"], dest_path)
            downloaded_files.append({
                "name": file_info["name"],
                "path": dest_path,
                "size": file_info["size"]
            })
        
        return json.dumps({
            "success": True,
            "message": f"Downloaded {len(downloaded_files)} PDF files",
            "files": downloaded_files
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# NOTE: Upload functionality removed - Service accounts cannot upload to personal Google Drive
# Only Shared Drives (Google Workspace) or OAuth delegation support uploads
# Available operations: list, download, search (read-only)


@mcp.tool()
def search_gdrive_content(
    query: str,
    folder_name: Optional[str] = None,
    file_types: Optional[List[str]] = None
) -> str:
    """
    Searches for files in Google Drive by query.
    
    Args:
        query: Search query string
        folder_name: Name of folder to limit search (optional)
        file_types: Filter by file types (optional)
    
    Returns:
        JSON string with list of matching files and their metadata
    """
    try:
        client = _get_gdrive_client()
        
        # Handle file_types parameter - convert string to list if needed
        if file_types and isinstance(file_types, str):
            file_types = [file_types]
        
        # Find folder ID by name if specified
        folder_id = None
        if folder_name:
            folder_id = client.find_folder_by_name(folder_name)
            if not folder_id:
                return json.dumps({
                    "success": False,
                    "error": f"Folder not found: {folder_name}"
                })
        
        results = client.search_files(
            query=query,
            folder_id=folder_id,
            file_types=file_types
        )
        return json.dumps({
            "success": True,
            "results": results,
            "count": len(results)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def get_gdrive_file_info(
    file_name: str,
    folder_name: Optional[str] = None
) -> str:
    """
    Gets detailed metadata for a Google Drive file by name.
    
    Args:
        file_name: Name of the file
        folder_name: Name of folder containing the file (optional)
    
    Returns:
        JSON string with detailed file metadata (name, size, MIME type, sharing info)
    """
    try:
        client = _get_gdrive_client()
        
        # Find the file by name
        file_info = client.find_file_by_name(file_name, folder_name)
        if not file_info:
            folder_msg = f" in folder '{folder_name}'" if folder_name else ""
            return json.dumps({
                "success": False,
                "error": f"File not found: {file_name}{folder_msg}"
            })
        
        # Get full metadata using the file ID
        metadata = client.get_file_metadata(file_info["id"])
        return json.dumps({
            "success": True,
            "metadata": metadata
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def create_gdrive_folder(
    folder_name: str,
    parent_folder_name: str = "root"
) -> str:
    """
    Creates a new folder in Google Drive.
    
    Args:
        folder_name: Name of the new folder
        parent_folder_name: Parent folder name or "root" (default: "root")
    
    Returns:
        JSON string with created folder information
    """
    try:
        client = _get_gdrive_client()
        
        # Find parent folder ID by name if not "root"
        parent_id = "root"
        if parent_folder_name != "root":
            parent_id = client.find_folder_by_name(parent_folder_name)
            if not parent_id:
                return json.dumps({
                    "success": False,
                    "error": f"Parent folder not found: {parent_folder_name}"
                })
        
        # Create the folder
        result = client.create_folder(
            folder_name=folder_name,
            parent_folder_id=parent_id
        )
        
        return json.dumps({
            "success": True,
            "message": "Folder created successfully",
            "folder": result
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# NOTE: create_gdrive_folder removed - Service accounts cannot create folders in personal Google Drive


@mcp.tool()
def test_gdrive_connection() -> str:
    """
    Tests the connection to Google Drive.
    
    Returns:
        JSON string with connection status
    """
    try:
        client = _get_gdrive_client()
        is_connected = client.test_connection()
        
        if is_connected:
            return json.dumps({
                "success": True,
                "message": "Successfully connected to Google Drive",
                "credentials_file": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "Failed to connect to Google Drive"
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def download_and_ingest_gdrive_files(
    folder_name: str = "root",
    file_types: Optional[List[str]] = None,
    destination_folder: str = "./temp_gdrive_downloads",
    specific_file_name: Optional[str] = None
) -> str:
    """
    Downloads PDF files from a Google Drive folder and ingests them into the Qdrant vector database for semantic search.
    Use this tool when you need to download and index documents for RAG (Retrieval Augmented Generation).
    
    Args:
        folder_name: Name of the Google Drive folder to download from (default: "root")
        file_types: List of file extensions to download (e.g., ["pdf"]) (default: ["pdf"])
        destination_folder: Local directory to save downloaded files (default: "./temp_gdrive_downloads")
        specific_file_name: Name of a specific file to download and ingest (e.g., "META.pdf"). If provided, only this file will be processed.
    
    Returns:
        JSON string with download and ingestion results including file paths and status messages
    """
    # Add required paths for pdf_processor1 and vector_store imports
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    utility_path = os.path.join(parent_dir, "utility")
    
    # Add both parent directory (for vector_store) and utility directory (for pdf_processor1)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    if utility_path not in sys.path:
        sys.path.insert(0, utility_path)
    
    try:
        from pdf_processor1 import process_pdf_and_stream
        client = _get_gdrive_client()
        
        # Default to PDF if no file types specified
        if not file_types:
            file_types = ["pdf"]
        elif isinstance(file_types, str):
            # If file_types is a string, convert to list
            file_types = [file_types]
        
        # Find folder ID by name if not "root"
        folder_id = "root"
        if folder_name != "root":
            folder_id = client.find_folder_by_name(folder_name)
            if not folder_id:
                return json.dumps({
                    "success": False,
                    "error": f"Folder not found: {folder_name}"
                })
        
        # List files with specified types
        files = client.list_files(
            folder_id=folder_id,
            file_types=file_types
        )
        
        if not files:
            return json.dumps({
                "success": True,
                "message": f"No {', '.join(file_types)} files found",
                "files": []
            })
        
        # Filter for specific file if requested
        if specific_file_name:
            files = [f for f in files if f["name"] == specific_file_name]
            if not files:
                return json.dumps({
                    "success": False,
                    "error": f"Specific file not found: {specific_file_name} in folder {folder_name}"
                })
        
        # Create destination folder
        company_folder = os.path.join(destination_folder, folder_name.upper())
        os.makedirs(company_folder, exist_ok=True)
        
        # Download each file
        downloaded_files = []
        for file_info in files:
            dest_path = os.path.join(company_folder, file_info["name"])
            client.download_file(file_info["id"], dest_path)
            downloaded_files.append(dest_path)
        
        # Ingest PDFs if any were downloaded
        ingestion_results = []
        if file_types and "pdf" in file_types and downloaded_files:
            try:
                for pdf_path in downloaded_files:
                    for message in process_pdf_and_stream(str(pdf_path)):
                        ingestion_results.append(message)
            except Exception as ingest_error:
                return json.dumps({
                    "success": True,
                    "message": f"Downloaded {len(downloaded_files)} files successfully, but ingestion failed",
                    "files": downloaded_files,
                    "ingestion_error": str(ingest_error),
                    "note": "Files are downloaded but not ingested into vector database. Make sure Qdrant is running on http://localhost:6333"
                }, indent=2)
        
        # Create appropriate success message
        if specific_file_name:
            message = f"Successfully downloaded and ingested specific file: {specific_file_name}"
        else:
            message = f"Downloaded and ingested {len(downloaded_files)} files"
        
        return json.dumps({
            "success": True,
            "message": message,
            "files": downloaded_files,
            "ingestion_messages": ingestion_results,
            "specific_file_processed": specific_file_name if specific_file_name else None
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@mcp.tool()
def get_gdrive_mode() -> str:
    """
    Returns information about the Google Drive connection mode.
    
    Returns:
        JSON string with mode information
    """
    try:
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
        return json.dumps({
            "success": True,
            "mode": "Service Account",
            "credentials_file": credentials_path,
            "scopes": [
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file"
            ]
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# Export the MCP server instance
def get_gdrive_mcp_server():
    """
    Get the FastMCP server instance for Google Drive operations.
    
    Returns:
        FastMCP server instance with 10 registered tools:
        - list_gdrive_files, list_gdrive_folders
        - download_gdrive_file, download_gdrive_pdfs
        - search_gdrive_content, get_gdrive_file_info
        - create_gdrive_folder (works!)
        - test_gdrive_connection, download_and_ingest_gdrive_files
        - get_gdrive_mode
        
    Note: File upload operations removed - service accounts cannot upload files to personal Google Drive
          However, creating folders works fine!
    """
    return mcp



# ============================================================================
# RUN AS HTTP SERVER
# ============================================================================

if __name__ == "__main__":
    """
    Run the Google Drive MCP server as an HTTP server.
    
    Usage:
        python -m gdrive.gdrive_mcp
    
    This starts the server on http://localhost:8005/mcp
    """
    import sys
    
    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8005
    
    print("\n" + "="*70)
    print("🚀 Starting Google Drive MCP Server (Read-Only Files)")
    print("="*70)
    print(f"📍 URL: http://localhost:{port}/mcp")
    print(f"🔧 Transport: streamable-http")
    print(f"📚 Tools: 10 operations (list, download, search, create folders)")
    print(f"⚠️  Note: File upload disabled - Service accounts can't upload files")
    print("="*70)
    print("\n💡 To test the server:")
    print(f"   curl http://localhost:{port}/mcp")
    print("\n📝 To use with agent:")
    print(f"   python test_gdrive_agent_http.py")
    print("\n⏹️  Press Ctrl+C to stop\n")
    
    # Run the server
    mcp.run(transport='streamable-http', port=port)
