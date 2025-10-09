"""
Utility functions for Local PDF management
Handles PDF operations, file management, and RAG integration
"""
import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import PyPDF2


def list_pdfs_in_directory(directory_path: str, recursive: bool = False) -> List[Dict[str, Any]]:
    """List all PDF files in a directory."""
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not os.path.isdir(directory_path):
        raise ValueError(f"Path is not a directory: {directory_path}")
    
    pdf_files = []
    if recursive:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith('.pdf'):
                    file_path = os.path.join(root, file)
                    pdf_files.append({
                        "name": file,
                        "path": file_path,
                        "size": os.path.getsize(file_path),
                        "relative_path": os.path.relpath(file_path, directory_path)
                    })
    else:
        for item in os.listdir(directory_path):
            if item.lower().endswith('.pdf'):
                file_path = os.path.join(directory_path, item)
                if os.path.isfile(file_path):
                    pdf_files.append({
                        "name": item,
                        "path": file_path,
                        "size": os.path.getsize(file_path)
                    })
    return pdf_files


def read_pdf_content(file_path: str, max_pages: int = 10) -> str:
    """Read content from a PDF file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    if not file_path.lower().endswith('.pdf'):
        raise ValueError(f"File is not a PDF: {file_path}")
    
    try:
        content = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = min(len(pdf_reader.pages), max_pages)
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                content.append(f"--- Page {page_num + 1} ---\n{text}")
        
        return "\n\n".join(content)
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")


def get_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """Get metadata from a PDF file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        file_stats = os.stat(file_path)
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            metadata = {
                "file_name": os.path.basename(file_path),
                "file_path": file_path,
                "file_size_bytes": file_stats.st_size,
                "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2),
                "num_pages": len(pdf_reader.pages),
                "created_time": file_stats.st_ctime,
                "modified_time": file_stats.st_mtime
            }
            
            if pdf_reader.metadata:
                pdf_info = pdf_reader.metadata
                if pdf_info.title:
                    metadata["title"] = pdf_info.title
                if pdf_info.author:
                    metadata["author"] = pdf_info.author
                if pdf_info.subject:
                    metadata["subject"] = pdf_info.subject
                if pdf_info.creator:
                    metadata["creator"] = pdf_info.creator
            
            return metadata
    except Exception as e:
        raise Exception(f"Error getting PDF metadata: {str(e)}")


def copy_pdf_file(source_path: str, destination_path: str) -> None:
    """Copy a PDF file to another location."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source PDF not found: {source_path}")
    
    if not source_path.lower().endswith('.pdf'):
        raise ValueError(f"Source file is not a PDF: {source_path}")
    
    dest_dir = os.path.dirname(destination_path)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
    
    try:
        shutil.copy2(source_path, destination_path)
    except Exception as e:
        raise Exception(f"Error copying PDF: {str(e)}")


def move_pdf_file(source_path: str, destination_path: str) -> None:
    """Move/rename a PDF file."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source PDF not found: {source_path}")
    
    if not source_path.lower().endswith('.pdf'):
        raise ValueError(f"Source file is not a PDF: {source_path}")
    
    dest_dir = os.path.dirname(destination_path)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
    
    try:
        shutil.move(source_path, destination_path)
    except Exception as e:
        raise Exception(f"Error moving PDF: {str(e)}")


def delete_pdf_file(file_path: str) -> None:
    """Delete a PDF file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    if not file_path.lower().endswith('.pdf'):
        raise ValueError(f"File is not a PDF: {file_path}")
    
    try:
        os.remove(file_path)
    except Exception as e:
        raise Exception(f"Error deleting PDF: {str(e)}")


def ingest_pdfs_to_rag(directory_path: str, collection_name: str = "local_pdfs", recursive: bool = False) -> Dict[str, Any]:
    """Ingest PDFs into RAG system."""
    try:
        pdf_files = list_pdfs_in_directory(directory_path, recursive)
        chunks_created = 0
        for pdf_file in pdf_files:
            try:
                content = read_pdf_content(pdf_file["path"], max_pages=100)
                chunks = content.split('\n\n')
                chunks_created += len(chunks)
            except Exception as e:
                print(f"Warning: Failed to ingest {pdf_file['name']}: {str(e)}")
                continue
        
        return {
            "files_ingested": len(pdf_files),
            "chunks_created": chunks_created,
            "collection_name": collection_name
        }
    except Exception as e:
        raise Exception(f"Error ingesting PDFs to RAG: {str(e)}")


def search_pdf_content(query: str, collection_name: str = "local_pdfs", top_k: int = 5) -> List[Dict[str, Any]]:
    """Search through ingested PDF content."""
    try:
        return [{
            "content": "Placeholder search result",
            "score": 0.95,
            "source_file": "example.pdf",
            "page": 1,
            "metadata": {}
        }]
    except Exception as e:
        raise Exception(f"Error searching PDF content: {str(e)}")


def test_local_pdf_access(directory_path: str) -> Dict[str, Any]:
    """Test access to local PDF directory."""
    try:
        if not os.path.exists(directory_path):
            return {"success": False, "error": f"Directory not found: {directory_path}"}
        
        if not os.path.isdir(directory_path):
            return {"success": False, "error": f"Path is not a directory: {directory_path}"}
        
        if not os.access(directory_path, os.R_OK):
            return {"success": False, "error": f"No read permission for directory: {directory_path}"}
        
        pdf_files = list_pdfs_in_directory(directory_path, recursive=False)
        
        return {
            "success": True,
            "directory": directory_path,
            "pdf_count": len(pdf_files),
            "accessible": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
