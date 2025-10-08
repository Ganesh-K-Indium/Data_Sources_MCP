"""
Confluence MCP Tools - FastMCP 2.0 implementation for Confluence operations
"""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv

from fastmcp import FastMCP

# Load environment variables
load_dotenv()

from utils import ConfluenceUtils

# Initialize FastMCP server
mcp = FastMCP("Confluence Operations")


@mcp.tool()
def list_spaces(limit: int = 50, expand: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    List all accessible Confluence spaces.
    
    Args:
        limit: Maximum number of spaces to return
        expand: Additional information to include (description, metadata, etc.)
    """
    try:
        utils = ConfluenceUtils()
        spaces_result = utils.confluence_client.get_spaces(limit=limit, expand=expand)
        return spaces_result
    except Exception as e:
        raise Exception(f"Failed to list spaces: {str(e)}")


@mcp.tool()
def get_space_info(space_key: str, expand: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get detailed information about a specific space.
    
    Args:
        space_key: Space key (e.g., 'TEAM')
        expand: Additional information to include
    """
    try:
        utils = ConfluenceUtils()
        space = utils.confluence_client.get_space(space_key, expand=expand)
        return space
    except Exception as e:
        raise Exception(f"Failed to get space info for {space_key}: {str(e)}")


@mcp.tool()
def search_content(
    space_key: Optional[str] = None,
    content_type: Optional[str] = None,
    title_search: Optional[str] = None,
    text_search: Optional[str] = None,
    author: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    modified_after: Optional[str] = None,
    modified_before: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Search for content using flexible filters.
    
    Args:
        space_key: Space key to search in
        content_type: Filter by content type (page, blogpost, comment, attachment)
        title_search: Text to search in titles
        text_search: Text to search in content body
        author: Filter by author username or display name
        created_after: Filter content created after this date (YYYY-MM-DD)
        created_before: Filter content created before this date (YYYY-MM-DD)
        modified_after: Filter content modified after this date (YYYY-MM-DD)
        modified_before: Filter content modified before this date (YYYY-MM-DD)
        limit: Maximum number of results to return
    """
    try:
        utils = ConfluenceUtils()
        filter_obj = utils.create_content_filter(
            space_key=space_key,
            content_type=content_type,
            title_search=title_search,
            text_search=text_search,
            author=author,
            created_after=created_after,
            created_before=created_before,
            modified_after=modified_after,
            modified_before=modified_before
        )
        
        cql = utils.build_cql_from_filter(filter_obj)
        result = utils.confluence_client.search_content(
            cql=cql, 
            limit=limit, 
            expand=['body.storage', 'version', 'space', 'history']
        )
        return result
    except Exception as e:
        raise Exception(f"Failed to search content: {str(e)}")


@mcp.tool()
def get_content_details(content_id: str) -> Dict[str, Any]:
    """
    Get comprehensive details for a specific content item.
    
    Args:
        content_id: Content ID
    """
    try:
        utils = ConfluenceUtils()
        content = utils.confluence_client.get_content(
            content_id, 
            expand=['body.storage', 'version', 'space', 'history', 'children.attachment']
        )
        enhanced_content = utils.process_content_details(content)
        return enhanced_content
    except Exception as e:
        raise Exception(f"Failed to get content details for {content_id}: {str(e)}")


@mcp.tool()
def get_content_by_title(space_key: str, title: str, content_type: str = 'page') -> Dict[str, Any]:
    """
    Get content by title within a space.
    
    Args:
        space_key: Space key to search in
        title: Exact title to search for
        content_type: Type of content (page, blogpost)
    """
    try:
        utils = ConfluenceUtils()
        content = utils.confluence_client.get_content_by_title(space_key, title, content_type)
        
        if not content:
            return {
                'found': False,
                'message': f"No {content_type} found with title '{title}' in space '{space_key}'"
            }
        
        enhanced_content = utils.process_content_details(content)
        enhanced_content['found'] = True
        return enhanced_content
    except Exception as e:
        raise Exception(f"Failed to get content by title: {str(e)}")


@mcp.tool()
def list_attachments(
    space_key: Optional[str] = None,
    content_id: Optional[str] = None,
    file_types: Optional[List[str]] = None,
    max_content: int = 50
) -> Dict[str, Any]:
    """
    List attachments in a space or specific content.
    
    Args:
        space_key: Space key to search (if not using content_id)
        content_id: Specific content ID to get attachments from
        file_types: List of file extensions to filter by (pdf, png, jpg, etc.)
        max_content: Maximum number of content items to check (for space search)
    """
    try:
        utils = ConfluenceUtils()
        
        if content_id:
            attachments_result = utils.confluence_client.get_content_attachments(content_id)
            attachments = attachments_result.get('results', [])
            
            if file_types:
                attachments = utils.filter_attachments_by_type(attachments, file_types)
            
            # Get content info
            try:
                content = utils.confluence_client.get_content(content_id, expand=['space'])
                content_title = content.get('title', '')
                space_key_from_content = content.get('space', {}).get('key', '')
            except Exception:
                content_title = 'Unknown'
                space_key_from_content = 'Unknown'
            
            return {
                'content_id': content_id,
                'content_title': content_title,
                'space_key': space_key_from_content,
                'attachment_count': len(attachments),
                'attachments': [utils.process_attachment_info(att) for att in attachments]
            }
        
        elif space_key:
            return utils.list_space_attachments(space_key, file_types, max_content)
        
        else:
            raise ValueError("Either space_key or content_id must be provided")
            
    except Exception as e:
        raise Exception(f"Failed to list attachments: {str(e)}")


@mcp.tool()
def download_attachments(
    space_key: Optional[str] = None,
    content_id: Optional[str] = None,
    file_types: Optional[List[str]] = None,
    organize_by_type: bool = False,
    base_download_path: str = "confluence_attachments",
    max_content: int = 50
) -> Dict[str, Any]:
    """
    Download attachments from content or spaces.
    
    Args:
        space_key: Space key to download from (downloads from all content)
        content_id: Specific content ID to download from
        file_types: List of file extensions to download (pdf, png, jpg, etc.)
        organize_by_type: Whether to organize files by type in subfolders
        base_download_path: Base directory for downloads
        max_content: Maximum number of content items to process (for space downloads)
    """
    try:
        utils = ConfluenceUtils()
        
        if content_id:
            return utils.download_content_attachments(
                content_id, file_types, base_download_path, organize_by_type
            )
        
        elif space_key:
            return utils.download_space_attachments(
                space_key, file_types, base_download_path, organize_by_type, max_content
            )
        
        else:
            raise ValueError("Either space_key or content_id must be provided")
            
    except Exception as e:
        raise Exception(f"Failed to download attachments: {str(e)}")


@mcp.tool()
def get_space_statistics(space_key: str, max_content: int = 200) -> Dict[str, Any]:
    """
    Generate comprehensive statistics for content in a space.
    
    Args:
        space_key: Space key to analyze
        max_content: Maximum number of content items to analyze
    """
    try:
        utils = ConfluenceUtils()
        stats = utils.generate_space_statistics(space_key, max_content)
        return stats
    except Exception as e:
        raise Exception(f"Failed to generate statistics for {space_key}: {str(e)}")


@mcp.tool()
def download_and_ingest_content_attachments(
    content_id: str,
    file_types: Optional[List[str]] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True
) -> Dict[str, Any]:
    """
    Download attachments from a specific content item and ingest them into vector database.
    
    Args:
        content_id: Confluence content ID
        file_types: List of file extensions to process (e.g., ['pdf', 'png'])
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete files after successful ingestion
    """
    try:
        utils = ConfluenceUtils()
        
        # Step 1: Download attachments
        download_result = utils.download_content_attachments(content_id, file_types)
        
        if not download_result['downloaded']:
            return {
                'success': True,
                'action': 'download_and_ingest',
                'message': f"No files downloaded from content {content_id}",
                'download_result': download_result,
                'ingestion_result': None
            }
        
        # Step 2: Process downloaded files
        ingestion_result = _process_content_files_for_ingestion(
            content_id, download_result, company_name, cleanup_after_ingest
        )
        
        return {
            'success': True,
            'action': 'download_and_ingest',
            'download_result': download_result,
            'ingestion_result': ingestion_result,
            'summary': f"Downloaded {download_result['downloaded']} files and processed {ingestion_result.get('processed', 0)} files from content {content_id}"
        }
        
    except Exception as e:
        raise Exception(f"Failed to download and ingest from content {content_id}: {str(e)}")


@mcp.tool()
def download_and_ingest_space_attachments(
    space_key: str,
    file_types: Optional[List[str]] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True,
    max_content: int = 50
) -> Dict[str, Any]:
    """
    Download attachments from all content in a space and ingest them into vector database.
    
    Args:
        space_key: Confluence space key (e.g., 'TEAM')
        file_types: List of file extensions to process (e.g., ['pdf', 'png'])
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete files after successful ingestion
        max_content: Maximum number of content items to process
    """
    try:
        utils = ConfluenceUtils()
        
        # Step 1: Download attachments from space
        download_result = utils.download_space_attachments(
            space_key, file_types, organize_by_type=False, max_content=max_content
        )
        
        if not download_result.get('total_files_downloaded', 0):
            return {
                'success': True,
                'action': 'download_and_ingest',
                'message': f"No files downloaded from space {space_key}",
                'download_result': download_result,
                'ingestion_result': None
            }
        
        # Step 2: Process downloaded files for each content item
        all_ingestion_results = []
        total_processed = 0
        
        for content_data in download_result.get('content', []):
            if content_data.get('downloaded', 0) > 0:
                content_id = content_data['content_id']
                ingestion_result = _process_content_files_for_ingestion(
                    content_id, content_data, company_name, cleanup_after_ingest
                )
                all_ingestion_results.append({
                    'content_id': content_id,
                    'content_title': content_data.get('content_title', ''),
                    'result': ingestion_result
                })
                total_processed += ingestion_result.get('processed', 0)
        
        return {
            'success': True,
            'action': 'download_and_ingest',
            'download_result': download_result,
            'ingestion_results': all_ingestion_results,
            'summary': f"Downloaded {download_result.get('total_files_downloaded', 0)} files and processed {total_processed} files from space {space_key}"
        }
        
    except Exception as e:
        raise Exception(f"Failed to download and ingest from space {space_key}: {str(e)}")


@mcp.tool()
def get_space_content_list(
    space_key: str,
    content_type: str = 'page',
    limit: int = 50,
    include_body: bool = False
) -> Dict[str, Any]:
    """
    Get a list of content items from a space.
    
    Args:
        space_key: Space key to get content from
        content_type: Type of content (page, blogpost)
        limit: Maximum number of items to return
        include_body: Whether to include content body in results
    """
    try:
        utils = ConfluenceUtils()
        expand = ['version', 'space']
        if include_body:
            expand.append('body.storage')
        
        result = utils.confluence_client.get_space_content(
            space_key, content_type, limit, expand
        )
        
        # Process results
        processed_content = []
        for content in result.get('results', []):
            processed = utils.process_content_details(content)
            processed_content.append(processed)
        
        return {
            'space_key': space_key,
            'content_type': content_type,
            'total_found': len(processed_content),
            'content': processed_content,
            'raw_result': result
        }
        
    except Exception as e:
        raise Exception(f"Failed to get content list for space {space_key}: {str(e)}")


def _process_content_files_for_ingestion(content_id: str, download_data: dict, 
                                       company_name: Optional[str], cleanup_after_ingest: bool) -> Dict[str, Any]:
    """
    Process downloaded files for a specific content item using PDF processing.
    
    Args:
        content_id: Confluence content ID
        download_data: Download result data containing file information
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete files after ingestion
        
    Returns:
        Dict with processing results
    """
    try:
        # Import here to avoid circular imports
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from utility.pdf_processor1 import process_pdf_and_stream
        
        print(f"🔍 Starting ingestion process for content {content_id}")
        
        # Get the download directory
        download_path = Path(download_data.get('download_path', ''))
        print(f"🔍 Download path: {download_path}")
        
        if not download_path.exists():
            print(f"❌ Download path does not exist")
            return {'processed': 0, 'error': 'Download path not found'}
        
        # Process each downloaded file
        processed_files = []
        failed_files = []
        
        files_to_process = download_data.get('files', [])
        print(f"🔍 Found {len(files_to_process)} files to process")
        
        for file_info in files_to_process:
            # Use 'local_path' key from attachment manager
            file_path = Path(file_info['local_path'])
            
            try:
                print(f"📄 Processing {file_path.name} using PDF processor...")
                
                # Check if it's a PDF file
                if not file_path.suffix.lower() == '.pdf':
                    failed_files.append({
                        'file': file_path.name,
                        'error': 'Not a PDF file - only PDFs are supported for ingestion'
                    })
                    continue
                
                # Use the robust PDF processor
                processing_successful = False
                processing_messages = []
                
                for message in process_pdf_and_stream(str(file_path)):
                    processing_messages.append(message)
                    print(f"   {message}")
                    
                    # Check for success indicators
                    if "Added" in message and "chunks" in message:
                        processing_successful = True
                    elif "already ingested" in message:
                        processing_successful = True
                    elif "Error" in message:
                        processing_successful = False
                        break
                
                if processing_successful:
                    processed_files.append({
                        'file': file_path.name,
                        'size_bytes': file_info.get('size_bytes', 0),
                        'status': 'processed',
                        'messages': processing_messages[-3:]  # Keep last 3 messages
                    })
                    
                    print(f"✅ Successfully ingested {file_path.name}")
                    
                    # Cleanup if requested
                    if cleanup_after_ingest:
                        file_path.unlink()
                        print(f"🗑️  Deleted {file_path.name}")
                else:
                    failed_files.append({
                        'file': file_path.name,
                        'error': 'PDF processing failed',
                        'messages': processing_messages[-3:]  # Keep last 3 messages for debugging
                    })
                    
            except Exception as e:
                failed_files.append({
                    'file': file_path.name,
                    'error': str(e)
                })
                print(f"❌ Failed to process {file_path.name}: {str(e)}")
        
        # Cleanup empty directory if all files were processed and cleaned up
        if cleanup_after_ingest and processed_files and not failed_files:
            try:
                download_path.rmdir()
                print(f"🗑️  Removed empty directory {download_path}")
            except OSError:
                pass  # Directory not empty or other issue
        
        return {
            'processed': len(processed_files),
            'failed': len(failed_files),
            'processed_files': processed_files,
            'failed_files': failed_files
        }
        
    except Exception as e:
        print(f"❌ Exception in _process_content_files_for_ingestion: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'processed': 0,
            'error': f"Processing failed: {str(e)}"
        }


@mcp.tool()
def create_page(
    space_key: str,
    title: str,
    content: str = "",
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new page in a Confluence space.
    
    Args:
        space_key: Confluence space key (e.g., 'TEAM')
        title: Title of the new page
        content: HTML content for the page (optional, defaults to basic content)
        parent_id: Optional parent page ID to create this page under
    """
    try:
        utils = ConfluenceUtils()
        result = utils.create_page(space_key, title, content, parent_id)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to create page '{title}' in space '{space_key}': {str(e)}",
            'space_key': space_key,
            'title': title
        }


@mcp.tool()
def create_page_and_upload_file(
    space_key: str,
    page_title: str,
    file_path: str,
    page_content: str = "",
    filename: Optional[str] = None,
    comment: Optional[str] = None,
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new page and upload a file to it in one operation.
    
    Args:
        space_key: Confluence space key (e.g., 'TEAM')
        page_title: Title of the new page to create
        file_path: Absolute path to the file to upload
        page_content: HTML content for the new page (optional)
        filename: Optional custom filename (defaults to original filename)
        comment: Optional comment for the attachment
        parent_id: Optional parent page ID to create this page under
    """
    try:
        utils = ConfluenceUtils()
        result = utils.create_page_and_upload_file(
            space_key, page_title, file_path, page_content, filename, comment, parent_id
        )
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to create page and upload file: {str(e)}",
            'space_key': space_key,
            'page_title': page_title,
            'file_path': file_path
        }


@mcp.tool()
def upload_file_to_page_or_create(
    space_key: str,
    page_title: str,
    file_path: str,
    page_content: str = "",
    filename: Optional[str] = None,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a file to a page, creating the page if it doesn't exist.
    This is the most flexible option for file uploads.
    
    Args:
        space_key: Confluence space key (e.g., 'TEAM')
        page_title: Title of the page (will be created if doesn't exist)
        file_path: Absolute path to the file to upload
        page_content: HTML content for the page if it needs to be created
        filename: Optional custom filename (defaults to original filename)
        comment: Optional comment for the attachment
    """
    try:
        utils = ConfluenceUtils()
        result = utils.upload_file_to_page_or_create(
            space_key, page_title, file_path, page_content, filename, comment
        )
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to upload file to page or create: {str(e)}",
            'space_key': space_key,
            'page_title': page_title,
            'file_path': file_path
        }


@mcp.tool()
def upload_file_to_content(
    content_id: str,
    file_path: str,
    filename: Optional[str] = None,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a file to a Confluence content item as an attachment.
    
    Args:
        content_id: Confluence content ID
        file_path: Absolute path to the file to upload
        filename: Optional custom filename (defaults to original filename)
        comment: Optional comment for the attachment
    """
    try:
        utils = ConfluenceUtils()
        result = utils.upload_file_to_content(content_id, file_path, filename, comment)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to upload file to content {content_id}: {str(e)}",
            'content_id': content_id,
            'file_path': file_path
        }


@mcp.tool()
def upload_file_to_page_by_title(
    space_key: str,
    page_title: str,
    file_path: str,
    filename: Optional[str] = None,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a file to a Confluence page by searching for it by title.
    
    Args:
        space_key: Confluence space key (e.g., 'TEAM')
        page_title: Title of the page to upload to
        file_path: Absolute path to the file to upload
        filename: Optional custom filename (defaults to original filename)
        comment: Optional comment for the attachment
    """
    try:
        utils = ConfluenceUtils()
        result = utils.upload_file_to_page_by_title(space_key, page_title, file_path, filename, comment)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to upload file to page '{page_title}' in space '{space_key}': {str(e)}",
            'space_key': space_key,
            'page_title': page_title,
            'file_path': file_path
        }


@mcp.tool()
def upload_multiple_files_to_content(
    content_id: str,
    file_paths: List[str],
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload multiple files to a Confluence content item as attachments.
    
    Args:
        content_id: Confluence content ID
        file_paths: List of absolute paths to files to upload
        comment: Optional comment for all attachments
    """
    try:
        utils = ConfluenceUtils()
        result = utils.upload_multiple_files_to_content(content_id, file_paths, comment)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to upload files to content {content_id}: {str(e)}",
            'content_id': content_id,
            'file_paths': file_paths
        }


@mcp.tool()
def upload_and_ingest_file_to_content(
    content_id: str,
    file_path: str,
    filename: Optional[str] = None,
    comment: Optional[str] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True
) -> Dict[str, Any]:
    """
    Upload a file to a Confluence content item and also ingest it into the vector database.
    
    Args:
        content_id: Confluence content ID
        file_path: Absolute path to the file to upload
        filename: Optional custom filename (defaults to original filename)
        comment: Optional comment for the attachment
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete the local file after ingestion
    """
    try:
        utils = ConfluenceUtils()
        
        # Step 1: Upload to Confluence
        upload_result = utils.upload_file_to_content(content_id, file_path, filename, comment)
        
        if not upload_result['success']:
            return {
                'success': False,
                'action': 'upload_and_ingest',
                'upload_result': upload_result,
                'ingestion_result': None,
                'error': f"Upload failed: {upload_result.get('error', 'Unknown error')}"
            }
        
        # Step 2: Ingest into vector database (only for PDFs)
        file_path_obj = Path(file_path)
        if file_path_obj.suffix.lower() == '.pdf':
            # Process for ingestion
            ingestion_result = _process_single_file_for_ingestion(
                file_path, company_name, cleanup_after_ingest
            )
        else:
            ingestion_result = {
                'processed': 0,
                'skipped': 1,
                'message': 'File skipped for ingestion - only PDFs are supported'
            }
        
        return {
            'success': True,
            'action': 'upload_and_ingest',
            'upload_result': upload_result,
            'ingestion_result': ingestion_result,
            'summary': f"Successfully uploaded {file_path_obj.name} to content {content_id}"
        }
        
    except Exception as e:
        return {
            'success': False,
            'action': 'upload_and_ingest',
            'error': f"Failed to upload and ingest file: {str(e)}",
            'content_id': content_id,
            'file_path': file_path
        }


@mcp.tool()
def upload_and_ingest_file_to_page_by_title(
    space_key: str,
    page_title: str,
    file_path: str,
    filename: Optional[str] = None,
    comment: Optional[str] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True
) -> Dict[str, Any]:
    """
    Upload a file to a Confluence page by title and also ingest it into the vector database.
    
    Args:
        space_key: Confluence space key (e.g., 'TEAM')
        page_title: Title of the page to upload to
        file_path: Absolute path to the file to upload
        filename: Optional custom filename (defaults to original filename)
        comment: Optional comment for the attachment
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete the local file after ingestion
    """
    try:
        utils = ConfluenceUtils()
        
        # Step 1: Upload to Confluence
        upload_result = utils.upload_file_to_page_by_title(space_key, page_title, file_path, filename, comment)
        
        if not upload_result['success']:
            return {
                'success': False,
                'action': 'upload_and_ingest',
                'upload_result': upload_result,
                'ingestion_result': None,
                'error': f"Upload failed: {upload_result.get('error', 'Unknown error')}"
            }
        
        # Step 2: Ingest into vector database (only for PDFs)
        file_path_obj = Path(file_path)
        if file_path_obj.suffix.lower() == '.pdf':
            # Process for ingestion
            ingestion_result = _process_single_file_for_ingestion(
                file_path, company_name, cleanup_after_ingest
            )
        else:
            ingestion_result = {
                'processed': 0,
                'skipped': 1,
                'message': 'File skipped for ingestion - only PDFs are supported'
            }
        
        return {
            'success': True,
            'action': 'upload_and_ingest',
            'upload_result': upload_result,
            'ingestion_result': ingestion_result,
            'summary': f"Successfully uploaded {file_path_obj.name} to page '{page_title}' in space '{space_key}'"
        }
        
    except Exception as e:
        return {
            'success': False,
            'action': 'upload_and_ingest',
            'error': f"Failed to upload and ingest file: {str(e)}",
            'space_key': space_key,
            'page_title': page_title,
            'file_path': file_path
        }


@mcp.tool()
def create_page_and_upload_and_ingest_file(
    space_key: str,
    page_title: str,
    file_path: str,
    page_content: str = "",
    filename: Optional[str] = None,
    comment: Optional[str] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True,
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new page, upload a file to it, and ingest into vector database (complete workflow).
    
    Args:
        space_key: Confluence space key (e.g., 'TEAM')
        page_title: Title of the new page to create
        file_path: Absolute path to the file to upload
        page_content: HTML content for the new page (optional)
        filename: Optional custom filename (defaults to original filename)
        comment: Optional comment for the attachment
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete the local file after ingestion
        parent_id: Optional parent page ID to create this page under
    """
    try:
        utils = ConfluenceUtils()
        
        # Step 1: Create page and upload file
        create_upload_result = utils.create_page_and_upload_file(
            space_key, page_title, file_path, page_content, filename, comment, parent_id
        )
        
        if not create_upload_result['success']:
            return {
                'success': False,
                'action': 'create_page_upload_and_ingest',
                'create_upload_result': create_upload_result,
                'ingestion_result': None,
                'error': f"Create/upload failed: {create_upload_result.get('error', 'Unknown error')}"
            }
        
        # Step 2: Ingest into vector database (only for PDFs)
        file_path_obj = Path(file_path)
        if file_path_obj.suffix.lower() == '.pdf':
            ingestion_result = _process_single_file_for_ingestion(
                file_path, company_name, cleanup_after_ingest
            )
        else:
            ingestion_result = {
                'processed': 0,
                'skipped': 1,
                'message': 'File skipped for ingestion - only PDFs are supported'
            }
        
        return {
            'success': True,
            'action': 'create_page_upload_and_ingest',
            'create_upload_result': create_upload_result,
            'ingestion_result': ingestion_result,
            'summary': f"Created page '{page_title}', uploaded {file_path_obj.name}, and processed for search"
        }
        
    except Exception as e:
        return {
            'success': False,
            'action': 'create_page_upload_and_ingest',
            'error': f"Failed to create page, upload, and ingest: {str(e)}",
            'space_key': space_key,
            'page_title': page_title,
            'file_path': file_path
        }


@mcp.tool()
def upload_and_ingest_file_to_page_or_create(
    space_key: str,
    page_title: str,
    file_path: str,
    page_content: str = "",
    filename: Optional[str] = None,
    comment: Optional[str] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True
) -> Dict[str, Any]:
    """
    Upload and ingest file to page, creating the page if it doesn't exist (most flexible workflow).
    
    Args:
        space_key: Confluence space key (e.g., 'TEAM')
        page_title: Title of the page (will be created if doesn't exist)
        file_path: Absolute path to the file to upload
        page_content: HTML content for the page if it needs to be created
        filename: Optional custom filename (defaults to original filename)
        comment: Optional comment for the attachment
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete the local file after ingestion
    """
    try:
        utils = ConfluenceUtils()
        
        # Step 1: Upload to page (create if needed)
        upload_result = utils.upload_file_to_page_or_create(
            space_key, page_title, file_path, page_content, filename, comment
        )
        
        if not upload_result['success']:
            return {
                'success': False,
                'action': 'upload_ingest_or_create',
                'upload_result': upload_result,
                'ingestion_result': None,
                'error': f"Upload failed: {upload_result.get('error', 'Unknown error')}"
            }
        
        # Step 2: Ingest into vector database (only for PDFs)
        file_path_obj = Path(file_path)
        if file_path_obj.suffix.lower() == '.pdf':
            ingestion_result = _process_single_file_for_ingestion(
                file_path, company_name, cleanup_after_ingest
            )
        else:
            ingestion_result = {
                'processed': 0,
                'skipped': 1,
                'message': 'File skipped for ingestion - only PDFs are supported'
            }
        
        return {
            'success': True,
            'action': 'upload_ingest_or_create',
            'upload_result': upload_result,
            'ingestion_result': ingestion_result,
            'summary': f"Uploaded {file_path_obj.name} to page '{page_title}' and processed for search"
        }
        
    except Exception as e:
        return {
            'success': False,
            'action': 'upload_ingest_or_create',
            'error': f"Failed to upload, ingest, or create: {str(e)}",
            'space_key': space_key,
            'page_title': page_title,
            'file_path': file_path
        }


def _process_single_file_for_ingestion(file_path: str, company_name: Optional[str], 
                                     cleanup_after_ingest: bool) -> Dict[str, Any]:
    """
    Process a single file for ingestion into vector database.
    
    Args:
        file_path: Path to the file to process
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete the file after ingestion
        
    Returns:
        Dict with processing results
    """
    try:
        # Import here to avoid circular imports
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from utility.pdf_processor1 import process_pdf_and_stream
        
        file_path_obj = Path(file_path)
        print(f"🔍 Starting ingestion process for {file_path_obj.name}")
        
        if not file_path_obj.exists():
            return {'processed': 0, 'error': 'File not found'}
        
        # Check if it's a PDF file
        if not file_path_obj.suffix.lower() == '.pdf':
            return {
                'processed': 0,
                'skipped': 1,
                'message': 'Not a PDF file - only PDFs are supported for ingestion'
            }
        
        # Use the robust PDF processor
        processing_successful = False
        processing_messages = []
        
        for message in process_pdf_and_stream(str(file_path_obj)):
            processing_messages.append(message)
            print(f"   {message}")
            
            # Check for success indicators
            if "Added" in message and "chunks" in message:
                processing_successful = True
            elif "already ingested" in message:
                processing_successful = True
            elif "Error" in message:
                processing_successful = False
                break
        
        if processing_successful:
            print(f"✅ Successfully ingested {file_path_obj.name}")
            
            # Cleanup if requested
            if cleanup_after_ingest:
                file_path_obj.unlink()
                print(f"🗑️  Deleted {file_path_obj.name}")
            
            return {
                'processed': 1,
                'file': file_path_obj.name,
                'status': 'processed',
                'messages': processing_messages[-3:]  # Keep last 3 messages
            }
        else:
            return {
                'processed': 0,
                'file': file_path_obj.name,
                'error': 'PDF processing failed',
                'messages': processing_messages[-3:]  # Keep last 3 messages for debugging
            }
            
    except Exception as e:
        print(f"❌ Exception in _process_single_file_for_ingestion: {str(e)}")
        return {
            'processed': 0,
            'error': f"Processing failed: {str(e)}"
        }


if __name__ == "__main__":
    mcp.run(transport='streamable-http', port=8001)