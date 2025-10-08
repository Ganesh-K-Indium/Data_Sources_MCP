"""
Utils - Helper functions for Jira MCP tools
"""

import os
import json
import requests
import base64
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class IssueFilter:
    """Simple data class for issue filtering."""
    project_key: Optional[str] = None
    issue_type: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    has_attachments: Optional[bool] = None
    text_search: Optional[str] = None


class JiraClient:
    """Simple Jira client for API operations."""
    
    def __init__(self):
        """Initialize with environment variables."""
        self.jira_url = os.getenv('JIRA_URL')
        self.username = os.getenv('JIRA_USERNAME')
        self.api_token = os.getenv('JIRA_API_TOKEN')
        
        if not all([self.jira_url, self.username, self.api_token]):
            raise ValueError("Missing Jira credentials in environment variables")
        
        # Ensure URL format
        if not self.jira_url.startswith(('http://', 'https://')):
            self.jira_url = f"https://{self.jira_url}"
        if not self.jira_url.endswith('/'):
            self.jira_url += '/'
        
        # Setup authentication
        auth_string = f"{self.username}:{self.api_token}"
        self.auth_header = base64.b64encode(auth_string.encode()).decode()
        
        self.headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Jira API."""
        url = urljoin(self.jira_url, endpoint)
        kwargs['headers'] = self.headers
        return requests.request(method, url, **kwargs)
    
    def get_projects(self, expand: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all projects."""
        params = {'expand': expand} if expand else {}
        response = self._make_request('GET', 'rest/api/3/project', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_project(self, project_key: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """Get specific project."""
        params = {'expand': expand} if expand else {}
        response = self._make_request('GET', f'rest/api/3/project/{project_key}', params=params)
        response.raise_for_status()
        return response.json()
    
    def search_issues(self, jql: str, max_results: int = 50, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Search issues using JQL."""
        data = {
            'jql': jql,
            'maxResults': max_results,
            'fields': fields or ['key', 'summary', 'status', 'issuetype', 'priority', 'assignee', 'reporter', 'created', 'updated', 'attachment', 'comment']
        }
        response = self._make_request('POST', 'rest/api/3/search/jql', json=data)
        response.raise_for_status()
        return response.json()
    
    def get_issue(self, issue_key: str, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get specific issue."""
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        response = self._make_request('GET', f'rest/api/3/issue/{issue_key}', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_issue_attachments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get attachments for an issue."""
        issue = self.get_issue(issue_key, expand=['attachment'])
        return issue.get('fields', {}).get('attachment', [])
    
    def download_attachment(self, attachment_url: str, local_path: str) -> bool:
        """Download an attachment."""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            response = self._make_request('GET', attachment_url.replace(self.jira_url, ''))
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception:
            return False
    
    def upload_attachment(self, issue_key: str, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Upload an attachment to an issue."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not filename:
            filename = file_path.name
        
        # Use multipart/form-data for file upload
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'X-Atlassian-Token': 'no-check'  # Required for file uploads
        }
        
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, 'application/octet-stream')}
            
            response = requests.post(
                f"{self.jira_url}rest/api/3/issue/{issue_key}/attachments",
                headers=headers,
                files=files
            )
            response.raise_for_status()
            return response.json()
    
    def create_issue(self, project_key: str, summary: str, issue_type: str = "Task", 
                    description: str = "", priority: str = "Medium", assignee: Optional[str] = None,
                    parent_key: Optional[str] = None) -> Dict[str, Any]:
        """Create a new issue in Jira."""
        issue_data = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description if description else f"Issue created for {summary}"
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": issue_type
                }
            }
        }
        
        # Add priority if specified
        if priority:
            issue_data["fields"]["priority"] = {"name": priority}
        
        # Add assignee if specified
        if assignee:
            issue_data["fields"]["assignee"] = {"accountId": assignee}
        
        # Add parent if this should be a subtask
        if parent_key:
            issue_data["fields"]["parent"] = {"key": parent_key}
            issue_data["fields"]["issuetype"] = {"name": "Subtask"}
        
        response = self._make_request('POST', 'rest/api/3/issue', json=issue_data)
        response.raise_for_status()
        return response.json()
    
    def get_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """Get available issue types for a project."""
        response = self._make_request('GET', f'rest/api/3/project/{project_key}/issuetype')
        response.raise_for_status()
        return response.json()
    
    def get_priorities(self) -> List[Dict[str, Any]]:
        """Get available priorities."""
        response = self._make_request('GET', 'rest/api/3/priority')
        response.raise_for_status()
        return response.json()


class JiraUtils:
    """Utility functions for Jira operations."""
    
    def __init__(self):
        """Initialize utilities."""
        self.jira_client = JiraClient()
    
    def create_issue_filter(self, **kwargs) -> IssueFilter:
        """Create an IssueFilter from keyword arguments."""
        return IssueFilter(**kwargs)
    
    def build_jql_from_filter(self, filter_obj: IssueFilter) -> str:
        """Build JQL query from filter object."""
        parts = []
        
        if filter_obj.project_key:
            parts.append(f'project = {filter_obj.project_key}')
        if filter_obj.issue_type:
            parts.append(f'issuetype = "{filter_obj.issue_type}"')
        if filter_obj.status:
            parts.append(f'status = "{filter_obj.status}"')
        if filter_obj.assignee:
            if filter_obj.assignee.lower() == 'unassigned':
                parts.append('assignee is EMPTY')
            else:
                parts.append(f'assignee = "{filter_obj.assignee}"')
        if filter_obj.priority:
            parts.append(f'priority = "{filter_obj.priority}"')
        if filter_obj.has_attachments is not None:
            if filter_obj.has_attachments:
                parts.append('attachments is not EMPTY')
            else:
                parts.append('attachments is EMPTY')
        if filter_obj.text_search:
            parts.append(f'text ~ "{filter_obj.text_search}"')
        
        jql = ' AND '.join(parts) if parts else 'project is not EMPTY'
        return jql + ' ORDER BY created DESC'
    
    def process_issue_details(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance issue details."""
        fields = issue.get('fields', {})
        
        return {
            'key': issue.get('key'),
            'summary': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'status': fields.get('status', {}).get('name'),
            'issue_type': fields.get('issuetype', {}).get('name'),
            'priority': fields.get('priority', {}).get('name') if fields.get('priority') else None,
            'assignee': fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
            'reporter': fields.get('reporter', {}).get('displayName') if fields.get('reporter') else None,
            'created': fields.get('created'),
            'updated': fields.get('updated'),
            'attachments': self._process_attachments(fields.get('attachment', [])),
            'comments': self._process_comments(fields.get('comment', {}).get('comments', [])),
            'raw_issue': issue
        }
    
    def _process_attachments(self, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process attachment data."""
        return [{
            'id': att.get('id'),
            'filename': att.get('filename'),
            'size': att.get('size'),
            'mimetype': att.get('mimeType'),
            'created': att.get('created'),
            'author': att.get('author', {}).get('displayName'),
            'download_url': att.get('content')
        } for att in attachments]
    
    def _process_comments(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process comment data."""
        return [{
            'id': comment.get('id'),
            'body': comment.get('body'),
            'created': comment.get('created'),
            'author': comment.get('author', {}).get('displayName')
        } for comment in comments]
    
    def process_attachment_info(self, attachment: Dict[str, Any]) -> Dict[str, Any]:
        """Process single attachment info."""
        filename = attachment.get('filename', 'unknown')
        size = attachment.get('size', 0)
        
        return {
            'id': attachment.get('id'),
            'filename': filename,
            'file_extension': Path(filename).suffix.lower(),
            'size_bytes': size,
            'size_human': self._format_file_size(size),
            'mimetype': attachment.get('mimeType', ''),
            'created': attachment.get('created', ''),
            'author': attachment.get('author', {}).get('displayName', ''),
            'download_url': attachment.get('content', '')
        }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def filter_attachments_by_type(self, attachments: List[Dict[str, Any]], file_types: List[str]) -> List[Dict[str, Any]]:
        """Filter attachments by file types."""
        filtered = []
        for att in attachments:
            filename = att.get('filename', '').lower()
            if any(filename.endswith(f'.{ft.lower()}') for ft in file_types):
                filtered.append(att)
        return filtered
    
    def list_project_attachments(self, project_key: str, file_types: Optional[List[str]] = None, max_issues: int = 50) -> Dict[str, Any]:
        """List all attachments in a project."""
        filter_obj = self.create_issue_filter(project_key=project_key, has_attachments=True)
        jql = self.build_jql_from_filter(filter_obj)
        result = self.jira_client.search_issues(jql=jql, max_results=max_issues)
        
        issues = result.get('issues', [])
        total_attachments = 0
        issues_data = []
        
        for issue in issues:
            issue_key = issue.get('key')
            attachments = issue.get('fields', {}).get('attachment', [])
            
            if file_types:
                attachments = self.filter_attachments_by_type(attachments, file_types)
            
            if attachments:
                issues_data.append({
                    'issue_key': issue_key,
                    'summary': issue.get('fields', {}).get('summary', ''),
                    'attachment_count': len(attachments),
                    'attachments': [self.process_attachment_info(att) for att in attachments]
                })
                total_attachments += len(attachments)
        
        return {
            'project_key': project_key,
            'total_issues_with_attachments': len(issues_data),
            'total_attachments': total_attachments,
            'issues': issues_data
        }
    
    def download_issue_attachments(self, issue_key: str, file_types: Optional[List[str]] = None, 
                                 base_path: str = "jira_attachments", organize_by_type: bool = False) -> Dict[str, Any]:
        """Download attachments from a specific issue."""
        attachments = self.jira_client.get_issue_attachments(issue_key)
        
        if file_types:
            attachments = self.filter_attachments_by_type(attachments, file_types)
        
        download_dir = Path(base_path) / issue_key
        download_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'issue_key': issue_key,
            'total_attachments': len(attachments),
            'downloaded': 0,
            'failed': 0,
            'download_path': str(download_dir),
            'files': []
        }
        
        for attachment in attachments:
            filename = attachment.get('filename', 'unknown')
            download_url = attachment.get('content')
            local_path = download_dir / filename
            
            # Handle duplicate filenames
            counter = 1
            original_path = local_path
            while local_path.exists():
                name = original_path.stem
                ext = original_path.suffix
                local_path = download_dir / f"{name}_{counter}{ext}"
                counter += 1
            
            success = self.jira_client.download_attachment(download_url, str(local_path))
            
            file_info = {
                'filename': filename,
                'local_path': str(local_path),
                'size_bytes': attachment.get('size', 0),
                'download_success': success
            }
            
            results['files'].append(file_info)
            
            if success:
                results['downloaded'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def download_project_attachments(self, project_key: str, file_types: Optional[List[str]] = None,
                                   base_path: str = "jira_attachments", organize_by_type: bool = False) -> Dict[str, Any]:
        """Download attachments from all issues in a project."""
        project_dir = Path(base_path) / project_key
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Get issues with attachments
        filter_obj = self.create_issue_filter(project_key=project_key, has_attachments=True)
        jql = self.build_jql_from_filter(filter_obj)
        result = self.jira_client.search_issues(jql=jql, max_results=100)
        issues = result.get('issues', [])
        
        project_results = {
            'project_key': project_key,
            'total_issues_processed': len(issues),
            'total_files_downloaded': 0,
            'total_files_failed': 0,
            'download_path': str(project_dir),
            'issues': []
        }
        
        for issue in issues:
            issue_key = issue.get('key')
            issue_result = self.download_issue_attachments(
                issue_key, file_types, str(project_dir), organize_by_type
            )
            
            project_results['issues'].append(issue_result)
            project_results['total_files_downloaded'] += issue_result['downloaded']
            project_results['total_files_failed'] += issue_result['failed']
        
        return project_results
    
    def generate_issue_statistics(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from a list of issues."""
        if not issues:
            return {'total_issues': 0}
        
        status_counts = {}
        type_counts = {}
        priority_counts = {}
        assignee_counts = {}
        attachments_count = 0
        
        for issue in issues:
            fields = issue.get('fields', {})
            
            # Status counts
            status = fields.get('status', {}).get('name', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Type counts
            issue_type = fields.get('issuetype', {}).get('name', 'Unknown')
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
            
            # Priority counts
            priority = fields.get('priority', {})
            priority_name = priority.get('name', 'None') if priority else 'None'
            priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1
            
            # Assignee counts
            assignee = fields.get('assignee', {})
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            assignee_counts[assignee_name] = assignee_counts.get(assignee_name, 0) + 1
            
            # Attachment counts
            attachments = fields.get('attachment', [])
            if attachments:
                attachments_count += 1
        
        return {
            'total_issues': len(issues),
            'by_status': status_counts,
            'by_type': type_counts,
            'by_priority': priority_counts,
            'by_assignee': assignee_counts,
            'issues_with_attachments': attachments_count
        }
    
    def upload_file_to_issue(self, issue_key: str, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to a Jira issue."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'File not found: {file_path}',
                    'issue_key': issue_key
                }
            
            # Check file size (Jira typically has a 10MB limit)
            file_size = file_path.stat().st_size
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                return {
                    'success': False,
                    'error': f'File too large: {file_size} bytes (max: {max_size} bytes)',
                    'issue_key': issue_key,
                    'file_size': file_size
                }
            
            # Validate issue exists
            try:
                issue = self.jira_client.get_issue(issue_key)
            except Exception:
                return {
                    'success': False,
                    'error': f'Issue not found: {issue_key}',
                    'issue_key': issue_key
                }
            
            # Upload the file
            result = self.jira_client.upload_attachment(issue_key, str(file_path), filename)
            
            if result:
                attachment_info = result[0] if isinstance(result, list) and result else result
                return {
                    'success': True,
                    'issue_key': issue_key,
                    'issue_title': issue.get('fields', {}).get('summary', ''),
                    'attachment_id': attachment_info.get('id'),
                    'filename': attachment_info.get('filename'),
                    'size_bytes': attachment_info.get('size', 0),
                    'upload_time': attachment_info.get('created'),
                    'file_path': str(file_path)
                }
            else:
                return {
                    'success': False,
                    'error': 'Upload failed - no response from server',
                    'issue_key': issue_key
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
                'issue_key': issue_key,
                'file_path': str(file_path) if 'file_path' in locals() else None
            }
    
    def upload_multiple_files_to_issue(self, issue_key: str, file_paths: List[str]) -> Dict[str, Any]:
        """Upload multiple files to a Jira issue."""
        results = {
            'issue_key': issue_key,
            'total_files': len(file_paths),
            'successful_uploads': 0,
            'failed_uploads': 0,
            'files': []
        }
        
        for file_path in file_paths:
            result = self.upload_file_to_issue(issue_key, file_path)
            results['files'].append(result)
            
            if result['success']:
                results['successful_uploads'] += 1
            else:
                results['failed_uploads'] += 1
        
        return results
    
    def create_issue(self, project_key: str, summary: str, issue_type: str = "Task", 
                    description: str = "", priority: str = "Medium", assignee: Optional[str] = None,
                    parent_key: Optional[str] = None) -> Dict[str, Any]:
        """Create a new issue in a Jira project."""
        try:
            # Validate project exists
            try:
                project_info = self.jira_client.get_project(project_key)
            except Exception:
                return {
                    'success': False,
                    'error': f'Project "{project_key}" not found or not accessible'
                }
            
            # Check if issue with same summary already exists
            filter_obj = self.create_issue_filter(project_key=project_key, text_search=summary)
            jql = self.build_jql_from_filter(filter_obj)
            existing_issues = self.jira_client.search_issues(jql=jql, max_results=5)
            
            for issue in existing_issues.get('issues', []):
                if issue.get('fields', {}).get('summary', '').strip().lower() == summary.strip().lower():
                    return {
                        'success': False,
                        'error': f'Issue with summary "{summary}" already exists',
                        'existing_issue': {
                            'key': issue['key'],
                            'summary': issue.get('fields', {}).get('summary', ''),
                            'status': issue.get('fields', {}).get('status', {}).get('name', ''),
                            'web_url': f"{self.jira_client.jira_url}browse/{issue['key']}"
                        }
                    }
            
            # Create the issue
            result = self.jira_client.create_issue(
                project_key, summary, issue_type, description, priority, assignee, parent_key
            )
            
            return {
                'success': True,
                'issue_created': True,
                'issue_key': result['key'],
                'issue_id': result['id'],
                'summary': summary,
                'project_key': project_key,
                'issue_type': issue_type,
                'priority': priority,
                'web_url': f"{self.jira_client.jira_url}browse/{result['key']}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create issue: {str(e)}',
                'project_key': project_key,
                'summary': summary
            }
    
    def create_issue_and_upload_file(self, project_key: str, summary: str, file_path: str, 
                                   issue_type: str = "Task", description: str = "", 
                                   priority: str = "Medium", filename: Optional[str] = None,
                                   assignee: Optional[str] = None, parent_key: Optional[str] = None) -> Dict[str, Any]:
        """Create a new issue and upload a file to it."""
        try:
            # Step 1: Create the issue
            create_result = self.create_issue(project_key, summary, issue_type, description, priority, assignee, parent_key)
            
            if not create_result['success']:
                # If issue already exists, try to upload to it
                if 'already exists' in create_result.get('error', ''):
                    existing_issue = create_result.get('existing_issue', {})
                    issue_key = existing_issue.get('key')
                    if issue_key:
                        print(f"📋 Issue already exists, uploading to existing issue: {issue_key}")
                        upload_result = self.upload_file_to_issue(issue_key, file_path, filename)
                        upload_result['issue_created'] = False
                        upload_result['issue_already_existed'] = True
                        return upload_result
                
                return create_result
            
            # Step 2: Upload file to the newly created issue
            issue_key = create_result['issue_key']
            upload_result = self.upload_file_to_issue(issue_key, file_path, filename)
            
            # Combine results
            if upload_result['success']:
                return {
                    'success': True,
                    'issue_created': True,
                    'issue_key': issue_key,
                    'summary': summary,
                    'project_key': project_key,
                    'web_url': create_result.get('web_url', ''),
                    'upload_result': upload_result,
                    'summary_text': f'Created issue "{summary}" and uploaded {Path(file_path).name}'
                }
            else:
                return {
                    'success': False,
                    'issue_created': True,
                    'issue_key': issue_key,
                    'summary': summary,
                    'error': f'Issue created but upload failed: {upload_result.get("error", "Unknown error")}',
                    'upload_result': upload_result
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create issue and upload file: {str(e)}',
                'project_key': project_key,
                'summary': summary,
                'file_path': file_path
            }
    
    def upload_file_to_issue_or_create(self, project_key: str, issue_key_or_summary: str, file_path: str, 
                                      issue_type: str = "Task", description: str = "", 
                                      priority: str = "Medium", filename: Optional[str] = None) -> Dict[str, Any]:
        """Upload file to issue, creating the issue if it doesn't exist."""
        try:
            # First try to treat it as an issue key and upload
            try:
                # Check if it looks like an issue key (PROJECT-123 format)
                if '-' in issue_key_or_summary and len(issue_key_or_summary.split('-')) == 2:
                    project_part, number_part = issue_key_or_summary.split('-')
                    if number_part.isdigit():
                        # Looks like an issue key, try to upload
                        upload_result = self.upload_file_to_issue(issue_key_or_summary, file_path, filename)
                        if upload_result['success']:
                            upload_result['issue_created'] = False
                            return upload_result
                        elif 'not found' not in upload_result.get('error', '').lower():
                            # If error is not about issue not found, return the error
                            return upload_result
            except Exception:
                pass
            
            # If we get here, either it's not an issue key or the issue doesn't exist
            # Treat it as a summary and create new issue
            print(f"📋 Issue '{issue_key_or_summary}' not found, creating it...")
            return self.create_issue_and_upload_file(
                project_key, issue_key_or_summary, file_path, issue_type, description, priority, filename
            )
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to upload file to issue or create: {str(e)}',
                'project_key': project_key,
                'issue_key_or_summary': issue_key_or_summary,
                'file_path': file_path
            }