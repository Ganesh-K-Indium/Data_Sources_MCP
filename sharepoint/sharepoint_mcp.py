"""
SharePoint MCP Tools - Unified Module
Comprehensive SharePoint operations with automatic client detection
Combines multi-site and single-site capabilities
"""
import json
import os
import sys
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Add parent directory to sys.path for absolute imports when run as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize FastMCP server
mcp = FastMCP("SharePoint MCP Server")


def _get_sharepoint_client():
    """Get SharePoint client from local sharepoint/utils.py"""
    from sharepoint.utils import SharePointClient
    return SharePointClient()


def _get_site_url():
    """Get site URL from environment - fallback to default"""
    return os.getenv("SHAREPOINT_SITE_URL") or os.getenv("SHAREPOINT_URL")


# ============================================================================
# DISCOVERY & LISTING TOOLS
# ============================================================================

@mcp.tool()
def list_sharepoint_sites() -> str:
    """
    Lists all SharePoint sites accessible to the authenticated user.
    
    Note: Only works in multi-site mode (requires SHAREPOINT_TENANT_ID, etc.)
    
    Returns:
        JSON string with list of sites (URLs, names, IDs)
    
    Example:
        sites = list_sharepoint_sites()
        # Returns: {"success": true, "sites": [...], "count": 5}
    """
    try:
        from sharepoint.utils import list_sharepoint_sites as get_sites
        return get_sites()
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def list_sharepoint_libraries(site_url: Optional[str] = None) -> str:
    """
    Lists all document libraries in a SharePoint site.
    
    Args:
        site_url: SharePoint site URL (optional in single-site mode)
    
    Returns:
        JSON string with list of libraries (names, IDs, descriptions)
    
    Example:
        # Multi-site mode
        libraries = list_sharepoint_libraries("https://company.sharepoint.com/sites/TeamSite")
        
        # Single-site mode (uses configured site)
        libraries = list_sharepoint_libraries()
    """
    try:
        from sharepoint.utils import list_sharepoint_libraries as get_libraries
        return get_libraries(site_url)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def list_sharepoint_files(
    library_name: str = "Documents",
    folder_path: Optional[str] = None,
    site_url: Optional[str] = None
) -> str:
    """
    Lists files in a SharePoint library or folder.
    
    Args:
        library_name: Document library name (default: "Documents")
        folder_path: Folder path within library (optional)
        site_url: SharePoint site URL (optional in single-site mode)
    
    Returns:
        JSON string with list of files
    
    Example:
        # Single-site mode
        files = list_sharepoint_files(library_name="Documents", folder_path="Reports/2024")
        
        # Multi-site mode
        files = list_sharepoint_files(
            site_url="https://company.sharepoint.com/sites/Finance",
            library_name="Documents"
        )
    """
    try:
        if site_url:
            # Multi-site mode with explicit site_url
            from sharepoint.utils import SharePointClient
            client = SharePointClient()
            files = client.list_files(site_url, library_name, folder_path or "")
        else:
            # Single-site mode using environment variables
            from sharepoint.utils import list_sharepoint_files as get_files
            files = get_files(library_name, folder_path or "")
        
        return json.dumps({
            "success": True,
            "count": len(files),
            "library": library_name,
            "folder": folder_path or "root",
            "files": [
                {
                    "name": f.get('name'),
                    "size": f.get('size'),
                    "modified": f.get('lastModifiedDateTime') or f.get('modified'),
                    "type": "folder" if f.get('folder') else "file"
                }
                for f in files
            ]
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# DOWNLOAD TOOLS
# ============================================================================

@mcp.tool()
def download_sharepoint_file(
    file_name: str,
    destination_path: str,
    library_name: str = "Documents",
    folder_path: Optional[str] = None,
    site_url: Optional[str] = None
) -> str:
    """
    Downloads a specific file from SharePoint by name.
    
    Args:
        file_name: Name of the file to download
        destination_path: Local directory or full file path to save the file
        library_name: Document library name (default: "Documents")
        folder_path: Folder path within library (optional)
        site_url: SharePoint site URL (optional in single-site mode)
    
    Returns:
        JSON string with download status and file info
    
    Example:
        # Single-site mode - directory path
        download_sharepoint_file("report.pdf", "./downloads")
        
        # Single-site mode - full file path
        download_sharepoint_file("report.pdf", "./downloads/report.pdf")
        
        # Multi-site mode
        download_sharepoint_file(
            "report.pdf",
            "./downloads/report.pdf",
            site_url="https://company.sharepoint.com/sites/Finance"
        )
    """
    try:
        from sharepoint.utils import download_specific_sharepoint_file
        
        # Determine if destination_path is a directory or full file path
        if os.path.isdir(destination_path):
            # It's a directory - use it as local_folder
            local_folder = destination_path
            final_path = os.path.join(destination_path, file_name)
        else:
            # It's a full file path - extract directory and use destination as final path
            local_folder = os.path.dirname(destination_path) or "."
            final_path = destination_path
        
        local_path = download_specific_sharepoint_file(
            file_name=file_name,
            library_name=library_name,
            folder_path=folder_path or "",
            local_folder=local_folder
        )
        
        if local_path:
            # Rename/move if needed
            if local_path != final_path:
                import shutil
                os.makedirs(os.path.dirname(final_path) or ".", exist_ok=True)
                shutil.move(local_path, final_path)
            
            return json.dumps({
                "success": True,
                "message": f"File downloaded successfully: {file_name}",
                "path": final_path
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": f"Failed to download: {file_name}"
            })
            
            if success:
                return json.dumps({
                    "success": True,
                    "message": f"File downloaded successfully: {file_name}",
                    "path": destination_path,
                    "file_info": file_info
                }, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "error": "Download failed"
                })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def download_sharepoint_file_by_path(
    file_path: str,
    library_name: str = "Documents",
    local_path: Optional[str] = None
) -> str:
    """
    Downloads a file by its full path in SharePoint.
    
    Note: Only works in single-site mode
    
    Args:
        file_path: Full path to file (e.g., "folder1/subfolder/file.pdf")
        library_name: Document library name (default: "Documents")
        local_path: Local path to save file (optional)
    
    Returns:
        JSON string with download status
    
    Example:
        download_sharepoint_file_by_path(
            "Reports/2024/Q3/financial_report.pdf",
            local_path="./reports/financial.pdf"
        )
    """
    try:
        
        from sharepoint.utils import download_file_by_sharepoint_path
        
        success = download_file_by_sharepoint_path(
            file_path=file_path,
            library_name=library_name,
            local_path=local_path
        )
        
        if success:
            return json.dumps({
                "success": True,
                "message": f"File downloaded successfully: {file_path}",
                "local_path": local_path or f"downloaded_files/{os.path.basename(file_path)}"
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": f"Failed to download: {file_path}"
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def download_sharepoint_pdfs(
    library_name: str = "Documents",
    folder_path: Optional[str] = None,
    local_folder: str = "sharepoint_pdfs"
) -> str:
    """
    Downloads all PDF files from a SharePoint library/folder.
    
    Note: Only works in single-site mode
    
    Args:
        library_name: Document library name (default: "Documents")
        folder_path: Folder path within library (optional)
        local_folder: Local folder to save PDFs (default: "sharepoint_pdfs")
    
    Returns:
        JSON string with list of downloaded files
    
    Example:
        download_sharepoint_pdfs(
            library_name="Documents",
            folder_path="Reports/2024",
            local_folder="./downloaded_pdfs"
        )
    """
    try:
        
        from sharepoint.utils import download_pdfs_from_sharepoint
        
        downloaded_files = download_pdfs_from_sharepoint(
            library_name=library_name,
            folder_path=folder_path or "",
            local_folder=local_folder
        )
        
        return json.dumps({
            "success": True,
            "count": len(downloaded_files),
            "files": downloaded_files,
            "local_folder": local_folder
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# UPLOAD TOOLS
# ============================================================================

@mcp.tool()
def upload_file_to_sharepoint(
    local_file_path: str,
    library_name: str = "Documents",
    folder_path: Optional[str] = None,
    remote_file_name: Optional[str] = None
) -> str:
    """
    Uploads a file to SharePoint document library.
    
    Note: Only works in single-site mode
    
    Args:
        local_file_path: Path to the local file to upload
        library_name: Document library name (default: "Documents")
        folder_path: Folder path within library (e.g., "Reports/2024")
        remote_file_name: Name for file in SharePoint (optional, uses local filename)
    
    Returns:
        JSON string with upload status and file information
    
    Example:
        upload_file_to_sharepoint(
            "./report.pdf",
            library_name="Documents",
            folder_path="Reports/Q4",
            remote_file_name="Q4_Report.pdf"
        )
    """
    try:
        
        from sharepoint.utils import upload_file_to_sharepoint as sp_upload
        
        file_info = sp_upload(
            local_file_path=local_file_path,
            library_name=library_name,
            folder_path=folder_path or "",
            remote_file_name=remote_file_name
        )
        
        if file_info:
            return json.dumps({
                "success": True,
                "message": f"File uploaded successfully: {file_info.get('name')}",
                "file_info": {
                    "name": file_info.get('name'),
                    "id": file_info.get('id'),
                    "size": file_info.get('size'),
                    "webUrl": file_info.get('webUrl'),
                    "lastModified": file_info.get('lastModifiedDateTime')
                }
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "Failed to upload file"
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def bulk_upload_to_sharepoint(
    local_files: List[str],
    library_name: str = "Documents",
    folder_path: Optional[str] = None
) -> str:
    """
    Uploads multiple files to SharePoint at once.
    
    Note: Only works in single-site mode
    
    Args:
        local_files: List of local file paths to upload
        library_name: Document library name (default: "Documents")
        folder_path: Folder path within library
    
    Returns:
        JSON string with upload summary for each file
    
    Example:
        bulk_upload_to_sharepoint(
            ["file1.pdf", "file2.pdf", "file3.pdf"],
            library_name="Documents",
            folder_path="Uploads"
        )
    """
    try:
        
        from sharepoint.utils import bulk_upload_to_sharepoint as sp_bulk_upload
        
        uploaded_files = sp_bulk_upload(
            local_files=local_files,
            library_name=library_name,
            folder_path=folder_path or ""
        )
        
        return json.dumps({
            "success": True,
            "total": len(local_files),
            "uploaded": len(uploaded_files),
            "failed": len(local_files) - len(uploaded_files),
            "files": [
                {
                    "name": f.get('name'),
                    "id": f.get('id'),
                    "size": f.get('size')
                }
                for f in uploaded_files
            ]
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# SEARCH & INFO TOOLS
# ============================================================================

@mcp.tool()
def search_sharepoint_content(
    query: str,
    site_url: Optional[str] = None,
    file_types: Optional[str] = None
) -> str:
    """
    Searches for content across SharePoint sites.
    
    Args:
        query: Search query string
        site_url: Limit search to specific site (optional)
        file_types: Comma-separated file types (e.g., "pdf,docx")
    
    Returns:
        JSON string with list of matching files and their metadata
    
    Example:
        search_sharepoint_content(
            query="annual report",
            file_types="pdf"
        )
    """
    try:
        from sharepoint.utils import search_sharepoint_content as search_content
        file_types_list = file_types.split(",") if file_types else None
        return search_content(query, site_url, file_types_list)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def get_sharepoint_file_info(
    file_name: str,
    library_name: str = "Documents",
    folder_path: Optional[str] = None
) -> str:
    """
    Gets detailed information about a specific file in SharePoint.
    
    Note: Only works in single-site mode
    
    Args:
        file_name: Name of the file
        library_name: Document library name (default: "Documents")
        folder_path: Folder path within library (optional)
    
    Returns:
        JSON string with file metadata
    
    Example:
        info = get_sharepoint_file_info(
            "report.pdf",
            library_name="Documents",
            folder_path="Reports"
        )
    """
    try:
        
        from sharepoint.utils import find_sharepoint_file
        
        file_info = find_sharepoint_file(
            file_name=file_name,
            library_name=library_name,
            folder_path=folder_path or ""
        )
        
        if file_info:
            return json.dumps({
                "success": True,
                "file": {
                    "name": file_info.get('name'),
                    "id": file_info.get('id'),
                    "size": file_info.get('size'),
                    "modified": file_info.get('lastModifiedDateTime'),
                    "created": file_info.get('createdDateTime'),
                    "webUrl": file_info.get('webUrl'),
                    "drive_id": file_info.get('drive_id')
                }
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": f"File not found: {file_name}"
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })



# ============================================================================
# INGESTION TOOLS (RAG PIPELINE)
# ============================================================================

@mcp.tool()
def download_and_ingest_sharepoint_files(
    file_names: Optional[List[str]] = None,
    library_name: str = "Documents",
    folder_path: Optional[str] = None,
    temp_download_folder: str = "temp_sharepoint_downloads",
    cleanup_after_ingest: bool = True,
    site_url: Optional[str] = None
) -> str:
    """
    Downloads SharePoint files and ingests them into the vector database (RAG system).
    
    This is a combined operation that:
    1. Downloads PDF files from SharePoint
    2. Processes them through the PDF ingestion pipeline
    3. Adds text chunks and images to vector stores
    4. Optionally cleans up downloaded files
    
    Args:
        file_names: List of specific file names to download and ingest (optional)
                   If None, downloads all PDFs in the specified location
        library_name: Document library name (default: "Documents")
        folder_path: Folder path within library (optional)
        temp_download_folder: Temporary folder for downloads (default: "temp_sharepoint_downloads")
        cleanup_after_ingest: Delete files after successful ingestion (default: True)
        site_url: SharePoint site URL (optional in single-site mode)
    
    Returns:
        JSON string with ingestion results
    
    Example:
        # Ingest specific files
        result = download_and_ingest_sharepoint_files(
            file_names=["TESLA.pdf", "AMAZON.pdf"],
            cleanup_after_ingest=True
        )
        
        # Ingest all PDFs in a folder
        result = download_and_ingest_sharepoint_files(
            folder_path="Financial Reports/2024",
            cleanup_after_ingest=False
        )
    """
    try:
        from pathlib import Path
        
        print(f"\n{'='*70}")
        print(f"🚀 SharePoint Download & Ingest Pipeline Started")
        print(f"{'='*70}")
        
        # Create temporary download directory
        download_path = Path(temp_download_folder)
        download_path.mkdir(exist_ok=True)
        print(f"📁 Temporary download folder: {download_path.absolute()}")
        
        # Step 1: Download files
        print(f"\n{'─'*70}")
        print(f"📥 STEP 1: Downloading files from SharePoint")
        print(f"{'─'*70}")
        
        downloaded_files = []
        
        # Import SharePoint utility functions from local utils
        from sharepoint.utils import download_specific_sharepoint_file, download_pdfs_from_sharepoint
        
        if file_names:
            # Download specific files
            print(f"📋 Downloading {len(file_names)} specific file(s)...")
            
            for file_name in file_names:
                if not file_name.lower().endswith('.pdf'):
                    print(f"⚠️  Skipping {file_name} - Not a PDF file")
                    continue
                
                try:
                    # Use underlying SharePoint function directly
                    local_path = download_specific_sharepoint_file(
                        file_name=file_name,
                        library_name=library_name,
                        folder_path=folder_path or "",
                        local_folder=str(download_path)
                    )
                    
                    if local_path and Path(local_path).exists():
                        file_path = Path(local_path)
                        downloaded_files.append({
                            'file_name': file_name,
                            'local_path': str(file_path),
                            'size_bytes': file_path.stat().st_size
                        })
                        print(f"   ✅ Downloaded: {file_name}")
                    else:
                        print(f"   ❌ Failed: {file_name} - Download returned no path")
                except Exception as e:
                    print(f"   ❌ Failed: {file_name} - {str(e)}")
        else:
            # Download all PDFs
            print(f"📋 Downloading all PDF files from {library_name}/{folder_path or 'root'}...")
            
            try:
                # Use underlying SharePoint function directly
                # Returns list of file paths (strings)
                downloaded_file_paths = download_pdfs_from_sharepoint(
                    library_name=library_name,
                    folder_path=folder_path or "",
                    local_folder=str(download_path)
                )
                
                if downloaded_file_paths:
                    for file_path_str in downloaded_file_paths:
                        file_path = Path(file_path_str)
                        if file_path.exists():
                            downloaded_files.append({
                                'file_name': file_path.name,
                                'local_path': str(file_path),
                                'size_bytes': file_path.stat().st_size
                            })
                    print(f"   ✅ Downloaded {len(downloaded_files)} PDF file(s)")
                else:
                    print(f"   ⚠️  No PDF files found to download")
            except Exception as e:
                print(f"   ❌ Download failed: {str(e)}")
                return json.dumps({
                    "success": False,
                    "error": f"Download failed: {str(e)}"
                })
        
        if not downloaded_files:
            return json.dumps({
                "success": False,
                "error": "No files were downloaded",
                "downloaded": 0,
                "ingested": 0
            })
        
        print(f"\n✅ Downloaded {len(downloaded_files)} file(s) successfully")
        
        # Step 2: Ingest files
        print(f"\n{'─'*70}")
        print(f"🔄 STEP 2: Ingesting files into vector database")
        print(f"{'─'*70}")
        
        processed_files = []
        failed_files = []
        
        # Import PDF processor (add paths for dependencies
        
        from utility.pdf_processor1 import process_pdf_and_stream
        
        for file_info in downloaded_files:
            file_path = Path(file_info['local_path'])
            
            if not file_path.exists():
                failed_files.append({
                    'file': file_info['file_name'],
                    'error': 'File not found after download'
                })
                continue
            
            try:
                print(f"\n📄 Processing: {file_path.name}")
                print(f"   Size: {file_info.get('size_bytes', 0):,} bytes")
                
                processing_successful = False
                processing_messages = []
                
                # Process PDF with streaming output
                for message in process_pdf_and_stream(str(file_path)):
                    processing_messages.append(message)
                    print(f"   {message}")
                    
                    # Check for success indicators
                    if "Added" in message and "chunks" in message:
                        processing_successful = True
                    elif "already ingested" in message.lower():
                        processing_successful = True
                    elif "Error" in message or "Failed" in message:
                        processing_successful = False
                        break
                
                if processing_successful:
                    processed_files.append({
                        'file': file_path.name,
                        'size_bytes': file_info.get('size_bytes', 0),
                        'status': 'ingested',
                        'messages': processing_messages[-3:]  # Last 3 messages
                    })
                    
                    print(f"   ✅ Successfully ingested: {file_path.name}")
                    
                    # Cleanup if requested
                    if cleanup_after_ingest:
                        file_path.unlink()
                        print(f"   🗑️  Deleted: {file_path.name}")
                else:
                    failed_files.append({
                        'file': file_path.name,
                        'error': 'PDF processing failed',
                        'messages': processing_messages[-3:]
                    })
                    print(f"   ❌ Failed to ingest: {file_path.name}")
                    
            except Exception as e:
                failed_files.append({
                    'file': file_info['file_name'],
                    'error': str(e)
                })
                print(f"   ❌ Exception: {str(e)}")
        
        # Step 3: Cleanup
        if cleanup_after_ingest and processed_files:
            try:
                # Remove empty download directory
                if not list(download_path.iterdir()):
                    download_path.rmdir()
                    print(f"\n🗑️  Removed temporary folder: {download_path}")
            except Exception as e:
                print(f"\n⚠️  Could not remove temporary folder: {str(e)}")
        
        # Final summary
        print(f"\n{'='*70}")
        print(f"📊 INGESTION SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Successfully ingested: {len(processed_files)}")
        print(f"❌ Failed: {len(failed_files)}")
        print(f"📁 Total downloaded: {len(downloaded_files)}")
        print(f"{'='*70}\n")
        
        return json.dumps({
            "success": True,
            "downloaded": len(downloaded_files),
            "ingested": len(processed_files),
            "failed": len(failed_files),
            "processed_files": processed_files,
            "failed_files": failed_files,
            "cleanup_performed": cleanup_after_ingest,
            "message": f"Successfully downloaded {len(downloaded_files)} and ingested {len(processed_files)} file(s)"
        }, indent=2)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n❌ Exception in download_and_ingest_sharepoint_files: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        
        return json.dumps({
            "success": False,
            "error": f"Download and ingestion failed: {str(e)}",
            "traceback": error_trace
        })


# ============================================================================
# UTILITY TOOLS
# ============================================================================

@mcp.tool()
def test_sharepoint_connection() -> str:
    """
    Tests SharePoint connection and authentication.
    
    Returns:
        JSON string with connection status and site information
    
    Example:
        status = test_sharepoint_connection()
        # Verifies credentials and lists available libraries
    """
    try:
        from sharepoint.utils import test_sharepoint_connection
        result = test_sharepoint_connection()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
def get_sharepoint_mode() -> str:
    """
    Gets the current SharePoint operation mode.
    
    Returns:
        JSON string with mode information
    
    Example:
        mode = get_sharepoint_mode()
        # Returns: {"mode": "single-site", "env_vars": [...]}
    """
    env_vars = {
        "SHAREPOINT_URL": "✅" if os.getenv("SHAREPOINT_URL") else "❌",
        "SHAREPOINT_SITE_URL": "✅" if os.getenv("SHAREPOINT_SITE_URL") else "❌",
        "TENANT_ID": "✅" if os.getenv("TENANT_ID") else "❌",
        "SHAREPOINT_TENANT_ID": "✅" if os.getenv("SHAREPOINT_TENANT_ID") else "❌",
        "CLIENT_ID": "✅" if os.getenv("CLIENT_ID") else "❌",
        "SHAREPOINT_CLIENT_ID": "✅" if os.getenv("SHAREPOINT_CLIENT_ID") else "❌"
    }
    
    # Determine mode based on environment variables
    if os.getenv("SHAREPOINT_URL"):
        mode = "single-site (SHAREPOINT_URL)"
    elif os.getenv("SHAREPOINT_SITE_URL"):
        mode = "multi-site (SHAREPOINT_SITE_URL)"
    else:
        mode = "not configured"
    
    return json.dumps({
        "mode": mode,
        "env_vars": env_vars,
        "note": "Tools use sharepoint/utils.py for all operations"
    }, indent=2)


# Export the MCP server instance
def get_sharepoint_mcp_server():
    """
    Get the FastMCP server instance for SharePoint operations.
    
    Returns:
        FastMCP server instance with all 13 registered tools
    """
    return mcp


# ============================================================================
# RUN AS HTTP SERVER
# ============================================================================

if __name__ == "__main__":
    """
    Run the SharePoint MCP server as an HTTP server.
    
    Usage:
        python -m sharepoint.sharepoint_mcp
    
    This starts the server on http://localhost:8001/mcp
    """
    import sys
    
    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8002
    
    print("\n" + "="*70)
    print("🚀 Starting SharePoint MCP Server")
    print("="*70)
    print(f"📍 URL: http://localhost:{port}/mcp")
    print(f"🔧 Transport: streamable-http")
    print(f"📚 Tools: 13 SharePoint operations")
    print("="*70)
    print("\n💡 To test the server:")
    print(f"   curl http://localhost:{port}/mcp")
    print("\n📝 To use with agent:")
    print(f"   python test_sharepoint_agent_http.py")
    print("\n⏹️  Press Ctrl+C to stop\n")
    
    # Run the server
    mcp.run(transport='streamable-http', port=port)
