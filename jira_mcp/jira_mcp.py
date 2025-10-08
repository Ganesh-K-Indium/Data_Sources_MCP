"""
Jira MCP Tools - FastMCP 2.0 implementation for Jira operations
"""

import os
import json
from typing import Dict, List, Optional, Any, Literal
from pathlib import Path
from dotenv import load_dotenv

from fastmcp import FastMCP

# Load environment variables
load_dotenv()

from utils import JiraUtils

# Initialize FastMCP server
mcp = FastMCP("Jira Operations")


@mcp.tool()
def list_projects(expand: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all accessible Jira projects.
    
    Args:
        expand: Additional information to include (description, lead, etc.)
    """
    try:
        utils = JiraUtils()
        projects = utils.jira_client.get_projects(expand=expand)
        return projects
    except Exception as e:
        raise Exception(f"Failed to list projects: {str(e)}")


@mcp.tool()
def get_project_info(project_key: str, expand: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed information about a specific project.
    
    Args:
        project_key: Project key (e.g., 'PROJ')
        expand: Additional information to include
    """
    try:
        utils = JiraUtils()
        project = utils.jira_client.get_project(project_key, expand=expand)
        return project
    except Exception as e:
        raise Exception(f"Failed to get project info for {project_key}: {str(e)}")


@mcp.tool()
def search_issues(
    project_key: Optional[str] = None,
    issue_type: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    has_attachments: Optional[bool] = None,
    text_search: Optional[str] = None,
    max_results: int = 50
) -> Dict[str, Any]:
    """
    Search for issues using flexible filters.
    
    Args:
        project_key: Project key to search in
        issue_type: Filter by issue type (Bug, Story, Task, etc.)
        status: Filter by status (Open, In Progress, Done, etc.)
        assignee: Filter by assignee username or display name
        priority: Filter by priority (High, Medium, Low, Critical)
        has_attachments: Filter issues with/without attachments
        text_search: Text to search in summary/description/comments
        max_results: Maximum number of results to return
    """
    try:
        utils = JiraUtils()
        filter_obj = utils.create_issue_filter(
            project_key=project_key,
            issue_type=issue_type,
            status=status,
            assignee=assignee,
            priority=priority,
            has_attachments=has_attachments,
            text_search=text_search
        )
        
        jql = utils.build_jql_from_filter(filter_obj)
        result = utils.jira_client.search_issues(jql=jql, max_results=max_results)
        return result
    except Exception as e:
        raise Exception(f"Failed to search issues: {str(e)}")


@mcp.tool()
def get_issue_details(issue_key: str) -> Dict[str, Any]:
    """
    Get comprehensive details for a specific issue.
    
    Args:
        issue_key: Issue key (e.g., 'PROJ-123')
    """
    try:
        utils = JiraUtils()
        issue = utils.jira_client.get_issue(
            issue_key, 
            expand=['comments', 'changelog', 'attachments']
        )
        enhanced_issue = utils.process_issue_details(issue)
        return enhanced_issue
    except Exception as e:
        raise Exception(f"Failed to get issue details for {issue_key}: {str(e)}")


@mcp.tool()
def list_attachments(
    project_key: Optional[str] = None,
    issue_key: Optional[str] = None,
    file_types: Optional[List[str]] = None,
    max_issues: int = 50
) -> Dict[str, Any]:
    """
    List attachments in a project or specific issue.
    
    Args:
        project_key: Project key to search (if not using issue_key)
        issue_key: Specific issue key to get attachments from
        file_types: List of file extensions to filter by (pdf, png, jpg, etc.)
        max_issues: Maximum number of issues to check (for project search)
    """
    try:
        utils = JiraUtils()
        
        if issue_key:
            attachments = utils.jira_client.get_issue_attachments(issue_key)
            if file_types:
                attachments = utils.filter_attachments_by_type(attachments, file_types)
            
            return {
                'issue_key': issue_key,
                'attachment_count': len(attachments),
                'attachments': [utils.process_attachment_info(att) for att in attachments]
            }
        
        elif project_key:
            return utils.list_project_attachments(project_key, file_types, max_issues)
        
        else:
            raise ValueError("Either project_key or issue_key must be provided")
            
    except Exception as e:
        raise Exception(f"Failed to list attachments: {str(e)}")


@mcp.tool()
def download_attachments(
    project_key: Optional[str] = None,
    issue_key: Optional[str] = None,
    file_types: Optional[List[str]] = None,
    organize_by_type: bool = False,
    base_download_path: str = "jira_attachments"
) -> Dict[str, Any]:
    """
    Download attachments from issues or projects.
    
    Args:
        project_key: Project key to download from (downloads from all issues)
        issue_key: Specific issue key to download from
        file_types: List of file extensions to download (pdf, png, jpg, etc.)
        organize_by_type: Whether to organize files by type in subfolders
        base_download_path: Base directory for downloads
    """
    try:
        utils = JiraUtils()
        
        if issue_key:
            return utils.download_issue_attachments(
                issue_key, file_types, base_download_path, organize_by_type
            )
        
        elif project_key:
            return utils.download_project_attachments(
                project_key, file_types, base_download_path, organize_by_type
            )
        
        else:
            raise ValueError("Either project_key or issue_key must be provided")
            
    except Exception as e:
        raise Exception(f"Failed to download attachments: {str(e)}")


@mcp.tool()
def get_issue_statistics(project_key: str, max_issues: int = 1000) -> Dict[str, Any]:
    """
    Generate comprehensive statistics for issues in a project.
    
    Args:
        project_key: Project key to analyze
        max_issues: Maximum number of issues to analyze
    """
    try:
        utils = JiraUtils()
        filter_obj = utils.create_issue_filter(project_key=project_key)
        
        jql = utils.build_jql_from_filter(filter_obj)
        result = utils.jira_client.search_issues(jql=jql, max_results=max_issues)
        issues = result.get('issues', [])
        
        stats = utils.generate_issue_statistics(issues)
        return stats
    except Exception as e:
        raise Exception(f"Failed to generate statistics for {project_key}: {str(e)}")


@mcp.tool()
def download_and_ingest_issue_attachments(
    issue_key: str,
    file_types: Optional[List[str]] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True
) -> Dict[str, Any]:
    """
    Download attachments from a specific issue and ingest them into vector database.
    
    Args:
        issue_key: Jira issue key (e.g., 'TEST-1')
        file_types: List of file extensions to process (e.g., ['pdf', 'png'])
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete files after successful ingestion
    """
    try:
        utils = JiraUtils()
        
        # Step 1: Download attachments
        download_result = utils.download_issue_attachments(issue_key, file_types)
        
        if not download_result['downloaded']:
            return {
                'success': True,
                'action': 'download_and_ingest',
                'message': f"No files downloaded from issue {issue_key}",
                'download_result': download_result,
                'ingestion_result': None
            }
        
        # Step 2: Process downloaded files
        ingestion_result = _process_issue_files_for_ingestion(
            issue_key, download_result, company_name, cleanup_after_ingest
        )
        
        return {
            'success': True,
            'action': 'download_and_ingest',
            'download_result': download_result,
            'ingestion_result': ingestion_result,
            'summary': f"Downloaded {download_result['downloaded']} files and processed {ingestion_result.get('processed', 0)} files from {issue_key}"
        }
        
    except Exception as e:
        raise Exception(f"Failed to download and ingest from issue {issue_key}: {str(e)}")


@mcp.tool()
def download_and_ingest_project_attachments(
    project_key: str,
    file_types: Optional[List[str]] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True,
    max_issues: int = 50
) -> Dict[str, Any]:
    """
    Download attachments from all issues in a project and ingest them into vector database.
    
    Args:
        project_key: Jira project key (e.g., 'TEST')
        file_types: List of file extensions to process (e.g., ['pdf', 'png'])
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete files after successful ingestion
        max_issues: Maximum number of issues to process
    """
    try:
        utils = JiraUtils()
        
        # Step 1: Download attachments from project
        download_result = utils.download_project_attachments(
            project_key, file_types, organize_by_type=False
        )
        
        if not download_result.get('total_files_downloaded', 0):
            return {
                'success': True,
                'action': 'download_and_ingest',
                'message': f"No files downloaded from project {project_key}",
                'download_result': download_result,
                'ingestion_result': None
            }
        
        # Step 2: Process downloaded files for each issue
        all_ingestion_results = []
        total_processed = 0
        
        for issue_data in download_result.get('issues', []):
            if issue_data.get('downloaded', 0) > 0:
                issue_key = issue_data['issue_key']
                ingestion_result = _process_issue_files_for_ingestion(
                    issue_key, issue_data, company_name, cleanup_after_ingest
                )
                all_ingestion_results.append({
                    'issue_key': issue_key,
                    'result': ingestion_result
                })
                total_processed += ingestion_result.get('processed', 0)
        
        return {
            'success': True,
            'action': 'download_and_ingest',
            'download_result': download_result,
            'ingestion_results': all_ingestion_results,
            'summary': f"Downloaded {download_result.get('total_files_downloaded', 0)} files and processed {total_processed} files from project {project_key}"
        }
        
    except Exception as e:
        raise Exception(f"Failed to download and ingest from project {project_key}: {str(e)}")


def _process_issue_files_for_ingestion(issue_key: str, download_data: dict, 
                                     company_name: Optional[str], cleanup_after_ingest: bool) -> Dict[str, Any]:
    """
    Process downloaded files for a specific issue using image data preparation.
    
    Args:
        issue_key: Jira issue key
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
        
        print(f"🔍 Starting ingestion process for issue {issue_key}")
        
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
        print(f"❌ Exception in _process_issue_files_for_ingestion: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'processed': 0,
            'error': f"Processing failed: {str(e)}"
        }


@mcp.tool()
def create_issue(
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: str = "",
    priority: str = "Medium",
    assignee: Optional[str] = None,
    parent_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new issue in a Jira project.
    
    Args:
        project_key: Jira project key (e.g., 'PROJ')
        summary: Issue summary/title
        issue_type: Type of issue (Task, Bug, Story, etc.)
        description: Detailed description of the issue
        priority: Priority level (Low, Medium, High, Critical)
        assignee: Account ID of the assignee (optional)
        parent_key: Parent issue key for subtasks (optional)
    """
    try:
        utils = JiraUtils()
        result = utils.create_issue(project_key, summary, issue_type, description, priority, assignee, parent_key)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to create issue '{summary}' in project '{project_key}': {str(e)}",
            'project_key': project_key,
            'summary': summary
        }


@mcp.tool()
def create_issue_and_upload_file(
    project_key: str,
    summary: str,
    file_path: str,
    issue_type: str = "Task",
    description: str = "",
    priority: str = "Medium",
    filename: Optional[str] = None,
    assignee: Optional[str] = None,
    parent_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new issue and upload a file to it in one operation.
    
    Args:
        project_key: Jira project key (e.g., 'PROJ')
        summary: Issue summary/title
        file_path: Absolute path to the file to upload
        issue_type: Type of issue (Task, Bug, Story, etc.)
        description: Detailed description of the issue
        priority: Priority level (Low, Medium, High, Critical)
        filename: Optional custom filename (defaults to original filename)
        assignee: Account ID of the assignee (optional)
        parent_key: Parent issue key for subtasks (optional)
    """
    try:
        utils = JiraUtils()
        result = utils.create_issue_and_upload_file(
            project_key, summary, file_path, issue_type, description, priority, filename, assignee, parent_key
        )
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to create issue and upload file: {str(e)}",
            'project_key': project_key,
            'summary': summary,
            'file_path': file_path
        }


@mcp.tool()
def upload_file_to_issue_or_create(
    project_key: str,
    issue_key_or_summary: str,
    file_path: str,
    issue_type: str = "Task",
    description: str = "",
    priority: str = "Medium",
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a file to an issue, creating the issue if it doesn't exist.
    This is the most flexible option for file uploads.
    
    Args:
        project_key: Jira project key (e.g., 'PROJ')
        issue_key_or_summary: Issue key (e.g., 'PROJ-123') or summary for new issue
        file_path: Absolute path to the file to upload
        issue_type: Type of issue if creating new (Task, Bug, Story, etc.)
        description: Description for new issue
        priority: Priority level if creating new (Low, Medium, High, Critical)
        filename: Optional custom filename (defaults to original filename)
    """
    try:
        utils = JiraUtils()
        result = utils.upload_file_to_issue_or_create(
            project_key, issue_key_or_summary, file_path, issue_type, description, priority, filename
        )
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to upload file to issue or create: {str(e)}",
            'project_key': project_key,
            'issue_key_or_summary': issue_key_or_summary,
            'file_path': file_path
        }


@mcp.tool()
def create_issue_and_upload_and_ingest_file(
    project_key: str,
    summary: str,
    file_path: str,
    issue_type: str = "Task",
    description: str = "",
    priority: str = "Medium",
    filename: Optional[str] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True,
    assignee: Optional[str] = None,
    parent_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new issue, upload a file to it, and ingest into vector database (complete workflow).
    
    Args:
        project_key: Jira project key (e.g., 'PROJ')
        summary: Issue summary/title
        file_path: Absolute path to the file to upload
        issue_type: Type of issue (Task, Bug, Story, etc.)
        description: Detailed description of the issue
        priority: Priority level (Low, Medium, High, Critical)
        filename: Optional custom filename (defaults to original filename)
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete the local file after ingestion
        assignee: Account ID of the assignee (optional)
        parent_key: Parent issue key for subtasks (optional)
    """
    try:
        utils = JiraUtils()
        
        # Step 1: Create issue and upload file
        create_upload_result = utils.create_issue_and_upload_file(
            project_key, summary, file_path, issue_type, description, priority, filename, assignee, parent_key
        )
        
        if not create_upload_result['success']:
            return {
                'success': False,
                'action': 'create_issue_upload_and_ingest',
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
            'action': 'create_issue_upload_and_ingest',
            'create_upload_result': create_upload_result,
            'ingestion_result': ingestion_result,
            'summary': f"Created issue '{summary}', uploaded {file_path_obj.name}, and processed for search"
        }
        
    except Exception as e:
        return {
            'success': False,
            'action': 'create_issue_upload_and_ingest',
            'error': f"Failed to create issue, upload, and ingest: {str(e)}",
            'project_key': project_key,
            'summary': summary,
            'file_path': file_path
        }


@mcp.tool()
def upload_and_ingest_file_to_issue_or_create(
    project_key: str,
    issue_key_or_summary: str,
    file_path: str,
    issue_type: str = "Task",
    description: str = "",
    priority: str = "Medium",
    filename: Optional[str] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True
) -> Dict[str, Any]:
    """
    Upload and ingest file to issue, creating the issue if it doesn't exist (most flexible workflow).
    
    Args:
        project_key: Jira project key (e.g., 'PROJ')
        issue_key_or_summary: Issue key (e.g., 'PROJ-123') or summary for new issue
        file_path: Absolute path to the file to upload
        issue_type: Type of issue if creating new (Task, Bug, Story, etc.)
        description: Description for new issue
        priority: Priority level if creating new (Low, Medium, High, Critical)
        filename: Optional custom filename (defaults to original filename)
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete the local file after ingestion
    """
    try:
        utils = JiraUtils()
        
        # Step 1: Upload to issue (create if needed)
        upload_result = utils.upload_file_to_issue_or_create(
            project_key, issue_key_or_summary, file_path, issue_type, description, priority, filename
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
            'summary': f"Uploaded {file_path_obj.name} to issue '{issue_key_or_summary}' and processed for search"
        }
        
    except Exception as e:
        return {
            'success': False,
            'action': 'upload_ingest_or_create',
            'error': f"Failed to upload, ingest, or create: {str(e)}",
            'project_key': project_key,
            'issue_key_or_summary': issue_key_or_summary,
            'file_path': file_path
        }


@mcp.tool()
def upload_file_to_issue(
    issue_key: str,
    file_path: str,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a file to a Jira issue as an attachment.
    
    Args:
        issue_key: Jira issue key (e.g., 'PROJ-123')
        file_path: Absolute path to the file to upload
        filename: Optional custom filename (defaults to original filename)
    """
    try:
        utils = JiraUtils()
        result = utils.upload_file_to_issue(issue_key, file_path, filename)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to upload file to issue {issue_key}: {str(e)}",
            'issue_key': issue_key,
            'file_path': file_path
        }


@mcp.tool()
def upload_multiple_files_to_issue(
    issue_key: str,
    file_paths: List[str]
) -> Dict[str, Any]:
    """
    Upload multiple files to a Jira issue as attachments.
    
    Args:
        issue_key: Jira issue key (e.g., 'PROJ-123')
        file_paths: List of absolute paths to files to upload
    """
    try:
        utils = JiraUtils()
        result = utils.upload_multiple_files_to_issue(issue_key, file_paths)
        return result
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to upload files to issue {issue_key}: {str(e)}",
            'issue_key': issue_key,
            'file_paths': file_paths
        }


@mcp.tool()
def upload_and_ingest_file_to_issue(
    issue_key: str,
    file_path: str,
    filename: Optional[str] = None,
    company_name: Optional[str] = None,
    cleanup_after_ingest: bool = True
) -> Dict[str, Any]:
    """
    Upload a file to a Jira issue and also ingest it into the vector database.
    
    Args:
        issue_key: Jira issue key (e.g., 'PROJ-123')
        file_path: Absolute path to the file to upload
        filename: Optional custom filename (defaults to original filename)
        company_name: Company name for document metadata
        cleanup_after_ingest: Whether to delete the local file after ingestion
    """
    try:
        utils = JiraUtils()
        
        # Step 1: Upload to Jira
        upload_result = utils.upload_file_to_issue(issue_key, file_path, filename)
        
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
            'summary': f"Successfully uploaded {file_path_obj.name} to issue {issue_key}"
        }
        
    except Exception as e:
        return {
            'success': False,
            'action': 'upload_and_ingest',
            'error': f"Failed to upload and ingest file: {str(e)}",
            'issue_key': issue_key,
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
    mcp.run(transport='streamable-http', port=8000)