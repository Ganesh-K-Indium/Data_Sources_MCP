"""
Local PDF MCP Server
Provides 8 MCP tools for local PDF file management and RAG ingestion
"""
import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP
import sys

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from local_pdf.utils import (
    list_pdfs_in_directory,
    read_pdf_content,
    get_pdf_metadata,
    copy_pdf_file,
    move_pdf_file,
    delete_pdf_file,
    ingest_pdfs_to_rag,
    search_pdf_content
)

# Initialize FastMCP server
mcp = FastMCP("Local PDF Manager")


# ============================================================================
# MCP TOOL 1: LIST LOCAL PDFs
# ============================================================================

@mcp.tool()
def list_local_pdfs(
    directory_path: str,
    recursive: bool = False
) -> str:
    """
    List all PDF files in a local directory.
    
    Args:
        directory_path: Absolute path to the directory
        recursive: Whether to search subdirectories
        
    Returns:
        JSON string with list of PDF files
    """
    try:
        pdf_files = list_pdfs_in_directory(directory_path, recursive)
        
        return json.dumps({
            "success": True,
            "directory": directory_path,
            "pdf_count": len(pdf_files),
            "files": pdf_files
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# MCP TOOL 2: READ LOCAL PDF
# ============================================================================

@mcp.tool()
def read_local_pdf(
    file_path: str,
    max_pages: int = 10
) -> str:
    """
    Read content from a specific local PDF file.
    
    Args:
        file_path: Absolute path to the PDF file
        max_pages: Maximum number of pages to read
        
    Returns:
        JSON string with PDF content
    """
    try:
        content = read_pdf_content(file_path, max_pages)
        
        return json.dumps({
            "success": True,
            "file_path": file_path,
            "content": content,
            "pages_read": min(max_pages, content.count('\n\n') + 1)
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# MCP TOOL 3: INGEST LOCAL PDFs 
# ============================================================================

@mcp.tool()
def ingest_local_pdfs(
    file_paths: Optional[List[str]] = None,
    directory_path: Optional[str] = None,
    recursive: bool = False
) -> str:
    """
    Ingest local PDFs into the vector database (RAG system).
    
    This operation:
    1. Processes PDF files through the ingestion pipeline
    2. Extracts text chunks and images
    3. Adds content to vector stores (Qdrant)
    4. Makes documents searchable via RAG queries
    
    Args:
        file_paths: List of absolute paths to specific PDF files to ingest (optional)
        directory_path: Absolute path to directory containing PDFs (optional)
        recursive: Whether to search subdirectories (only used with directory_path)
        
    Returns:
        JSON string with ingestion results
        
    Example:
        # Ingest specific files
        ingest_local_pdfs(file_paths=["/path/to/file1.pdf", "/path/to/file2.pdf"])
        
        # Ingest all PDFs in a directory
        ingest_local_pdfs(directory_path="/path/to/pdfs", recursive=True)
    """
    try:
        import sys
        from pathlib import Path
        
        print(f"\n{'='*70}")
        print(f"🚀 Local PDF Ingestion Pipeline Started")
        print(f"{'='*70}")
        
        # Collect PDF files to process
        pdf_files_to_ingest = []
        
        if file_paths:
            # Use specific file paths
            print(f"📋 Processing {len(file_paths)} specific file(s)...")
            for file_path in file_paths:
                pdf_path = Path(file_path)
                if not pdf_path.exists():
                    print(f"   ⚠️  File not found: {file_path}")
                    continue
                if not pdf_path.suffix.lower() == '.pdf':
                    print(f"   ⚠️  Skipping {pdf_path.name} - Not a PDF file")
                    continue
                pdf_files_to_ingest.append(pdf_path)
                print(f"   ✅ Added: {pdf_path.name}")
                
        elif directory_path:
            # Scan directory for PDFs
            dir_path = Path(directory_path)
            if not dir_path.exists():
                return json.dumps({
                    "success": False,
                    "error": f"Directory not found: {directory_path}"
                })
            
            print(f"📁 Scanning directory: {directory_path}")
            print(f"   Recursive: {recursive}")
            
            if recursive:
                pdf_files_to_ingest = list(dir_path.rglob("*.pdf"))
            else:
                pdf_files_to_ingest = list(dir_path.glob("*.pdf"))
            
            print(f"   ✅ Found {len(pdf_files_to_ingest)} PDF file(s)")
            
        else:
            return json.dumps({
                "success": False,
                "error": "Either 'file_paths' or 'directory_path' must be provided"
            })
        
        if not pdf_files_to_ingest:
            return json.dumps({
                "success": False,
                "error": "No PDF files found to ingest",
                "files_ingested": 0
            })
        
        # Step 1: Ingest files using pdf_processor1
        print(f"\n{'─'*70}")
        print(f"🔄 STEP 1: Ingesting files into vector database")
        print(f"{'─'*70}")
        
        processed_files = []
        failed_files = []
        
        # Import PDF processor (add paths for dependencies)
        parent_dir = os.path.join(os.path.dirname(__file__), '..')
        sys.path.insert(0, parent_dir)
        sys.path.insert(0, os.path.join(parent_dir, 'load_vector_dbs'))
        sys.path.insert(0, os.path.join(parent_dir, 'data_preparation'))
        
        from utility.pdf_processor1 import process_pdf_and_stream
        
        for pdf_path in pdf_files_to_ingest:
            try:
                print(f"\n📄 Processing: {pdf_path.name}")
                print(f"   Size: {pdf_path.stat().st_size:,} bytes")
                
                processing_successful = False
                processing_messages = []
                
                # Process PDF with streaming output
                for message in process_pdf_and_stream(str(pdf_path)):
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
                        'file': pdf_path.name,
                        'path': str(pdf_path),
                        'size_bytes': pdf_path.stat().st_size,
                        'status': 'ingested',
                        'messages': processing_messages[-3:]  # Last 3 messages
                    })
                    print(f"   ✅ Successfully ingested: {pdf_path.name}")
                else:
                    failed_files.append({
                        'file': pdf_path.name,
                        'path': str(pdf_path),
                        'error': 'PDF processing failed',
                        'messages': processing_messages[-3:]
                    })
                    print(f"   ❌ Failed to ingest: {pdf_path.name}")
                    
            except Exception as e:
                failed_files.append({
                    'file': pdf_path.name,
                    'path': str(pdf_path),
                    'error': str(e)
                })
                print(f"   ❌ Exception: {str(e)}")
        
        # Final summary
        print(f"\n{'='*70}")
        print(f"📊 INGESTION SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Successfully ingested: {len(processed_files)}")
        print(f"❌ Failed: {len(failed_files)}")
        print(f"📁 Total processed: {len(pdf_files_to_ingest)}")
        print(f"{'='*70}\n")
        
        return json.dumps({
            "success": True,
            "total_files": len(pdf_files_to_ingest),
            "ingested": len(processed_files),
            "failed": len(failed_files),
            "processed_files": processed_files,
            "failed_files": failed_files,
            "message": f"Successfully ingested {len(processed_files)} of {len(pdf_files_to_ingest)} PDF file(s)"
        }, indent=2)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n❌ Exception in ingest_local_pdfs: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        
        return json.dumps({
            "success": False,
            "error": f"Ingestion failed: {str(e)}",
            "traceback": error_trace
        })


# ============================================================================
# MCP TOOL 4: SEARCH LOCAL PDFs
# ============================================================================

@mcp.tool()
def search_local_pdfs(
    query: str,
    collection_name: str = "local_pdfs",
    top_k: int = 5
) -> str:
    """
    Search through ingested local PDF content.
    
    Args:
        query: Search query string
        collection_name: Name of the RAG collection to search
        top_k: Number of results to return
        
    Returns:
        JSON string with search results
    """
    try:
        results = search_pdf_content(query, collection_name, top_k)
        
        return json.dumps({
            "success": True,
            "query": query,
            "collection": collection_name,
            "results_count": len(results),
            "results": results
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# MCP TOOL 5: GET LOCAL PDF METADATA
# ============================================================================

@mcp.tool()
def get_local_pdf_metadata(file_path: str) -> str:
    """
    Get metadata (size, pages, etc.) of a local PDF.
    
    Args:
        file_path: Absolute path to the PDF file
        
    Returns:
        JSON string with PDF metadata
    """
    try:
        metadata = get_pdf_metadata(file_path)
        
        return json.dumps({
            "success": True,
            "file_path": file_path,
            "metadata": metadata
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# MCP TOOL 6: DELETE LOCAL PDF
# ============================================================================

@mcp.tool()
def delete_local_pdf(file_path: str) -> str:
    """
    Delete a specific local PDF file.
    
    Args:
        file_path: Absolute path to the PDF file to delete
        
    Returns:
        JSON string with deletion result
    """
    try:
        delete_pdf_file(file_path)
        
        return json.dumps({
            "success": True,
            "message": f"Successfully deleted: {file_path}",
            "deleted_file": file_path
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# MCP TOOL 7: MOVE LOCAL PDF
# ============================================================================

@mcp.tool()
def move_local_pdf(
    source_path: str,
    destination_path: str
) -> str:
    """
    Move/rename a local PDF file.
    
    Args:
        source_path: Current absolute path to the PDF file
        destination_path: New absolute path for the PDF file
        
    Returns:
        JSON string with move result
    """
    try:
        move_pdf_file(source_path, destination_path)
        
        return json.dumps({
            "success": True,
            "message": f"Successfully moved file",
            "from": source_path,
            "to": destination_path
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# MCP TOOL 8: COPY LOCAL PDF
# ============================================================================

@mcp.tool()
def copy_local_pdf(
    source_path: str,
    destination_path: str
) -> str:
    """
    Copy a local PDF to another location.
    
    Args:
        source_path: Absolute path to the source PDF file
        destination_path: Absolute path for the copied PDF file
        
    Returns:
        JSON string with copy result
    """
    try:
        copy_pdf_file(source_path, destination_path)
        
        return json.dumps({
            "success": True,
            "message": f"Successfully copied file",
            "from": source_path,
            "to": destination_path
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================

def get_local_pdf_mcp_server():
    """Get the Local PDF MCP server instance"""
    return mcp


# ============================================================================
# RUN AS HTTP SERVER
# ============================================================================

if __name__ == "__main__":
    """
    Run the Local PDF MCP server as an HTTP server.
    
    Usage:
        python -m local_pdf.local_pdf_mcp
    
    This starts the server on http://localhost:8003/mcp
    """
    import sys
    
    # Get port from command line or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8003
    
    print("\n" + "="*70)
    print("🚀 Starting Local PDF MCP Server")
    print("="*70)
    print(f"📍 URL: http://localhost:{port}/mcp")
    print(f"🔧 Transport: streamable-http")
    print(f"📚 Tools: 8 Local PDF operations")
    print("="*70)
    print("\n💡 To test the server:")
    print(f"   curl http://localhost:{port}/mcp")
    print("\n📝 To use with agent:")
    print(f"   python test_local_pdf_agent_http.py")
    print("\n⏹️  Press Ctrl+C to stop\n")
    
    # Run the server
    mcp.run(transport='streamable-http', port=port)
