"""
Local PDF package for agentic RAG operations
"""

# MCP Server
from .local_pdf_mcp import get_local_pdf_mcp_server

# Intelligent Agent
from .local_pdf_agent import create_local_pdf_agent

# Utilities
from .utils import (
    list_pdfs_in_directory,
    read_pdf_content,
    get_pdf_metadata,
    copy_pdf_file,
    move_pdf_file,
    delete_pdf_file,
    ingest_pdfs_to_rag,
    search_pdf_content,
    test_local_pdf_access
)

__all__ = [
    # MCP Server
    'get_local_pdf_mcp_server',
    
    # Intelligent Agent
    'create_local_pdf_agent',
    
    # Utilities
    'list_pdfs_in_directory',
    'read_pdf_content',
    'get_pdf_metadata',
    'copy_pdf_file',
    'move_pdf_file',
    'delete_pdf_file',
    'ingest_pdfs_to_rag',
    'search_pdf_content',
    'test_local_pdf_access',
]
