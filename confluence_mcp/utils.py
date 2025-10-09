"""
Utils - Helper functions for Confluence MCP tools
"""

import os
import json
import requests
import base64
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin, quote
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ContentFilter:
    """Simple data class for content filtering."""
    space_key: Optional[str] = None
    content_type: Optional[str] = None  # page, blogpost, comment, attachment
    title_search: Optional[str] = None
    text_search: Optional[str] = None
    author: Optional[str] = None
    has_attachments: Optional[bool] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    modified_after: Optional[str] = None
    modified_before: Optional[str] = None


class ConfluenceClient:
    """Simple Confluence client for API operations."""
    
    def __init__(self):
        """Initialize with environment variables."""
        self.confluence_url = os.getenv('CONFLUENCE_URL')
        self.username = os.getenv('CONFLUENCE_USERNAME')
        self.api_token = os.getenv('CONFLUENCE_API_TOKEN')
        
        
        if not all([self.confluence_url, self.username, self.api_token]):
            raise ValueError("Missing Confluence credentials in environment variables")
        
        # Ensure URL format
        if not self.confluence_url.startswith(('http://', 'https://')):
            self.confluence_url = f"https://{self.confluence_url}"
        if not self.confluence_url.endswith('/'):
            self.confluence_url += '/'
        
        # Setup authentication
        auth_string = f"{self.username}:{self.api_token}"
        self.auth_header = base64.b64encode(auth_string.encode()).decode()
        
        self.headers = {
            'Authorization': f'Basic {self.auth_header}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Confluence API."""
        url = urljoin(self.confluence_url, endpoint)
        kwargs['headers'] = self.headers
        return requests.request(method, url, **kwargs)
    
    def get_spaces(self, limit: int = 50, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get all accessible spaces."""
        params = {'limit': limit}
        if expand:
            params['expand'] = ','.join(expand)
        
        response = self._make_request('GET', 'rest/api/space', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_space(self, space_key: str, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get specific space information."""
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        
        response = self._make_request('GET', f'rest/api/space/{space_key}', params=params)
        response.raise_for_status()
        return response.json()
    
    def search_content(self, cql: str, limit: int = 50, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """Search content using CQL (Confluence Query Language)."""
        params = {
            'cql': cql,
            'limit': limit
        }
        if expand:
            params['expand'] = ','.join(expand)
        
        response = self._make_request('GET', 'rest/api/content/search', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_content(self, content_id: str, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get specific content by ID."""
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        
        response = self._make_request('GET', f'rest/api/content/{content_id}', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_content_attachments(self, content_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get attachments for a content item."""
        params = {'limit': limit}
        response = self._make_request('GET', f'rest/api/content/{content_id}/child/attachment', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_space_content(self, space_key: str, content_type: str = 'page', 
                         limit: int = 50, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get content from a specific space."""
        params = {
            'spaceKey': space_key,
            'type': content_type,
            'limit': limit
        }
        if expand:
            params['expand'] = ','.join(expand)
        
        response = self._make_request('GET', 'rest/api/content', params=params)
        response.raise_for_status()
        return response.json()
    
    def download_attachment(self, download_url: str, local_path: str) -> bool:
        """Download an attachment."""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Handle both absolute and relative URLs
            if download_url.startswith('http'):
                url = download_url
            else:
                url = urljoin(self.confluence_url, download_url.lstrip('/'))
            
            response = requests.get(url, headers={'Authorization': f'Basic {self.auth_header}'})
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Failed to download attachment: {e}")
            return False
    
    def upload_attachment(self, content_id: str, file_path: str, filename: Optional[str] = None, 
                         comment: Optional[str] = None) -> Dict[str, Any]:
        """Upload an attachment to a content item."""
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
            data = {}
            if comment:
                data['comment'] = comment
            
            response = requests.post(
                f"{self.confluence_url}rest/api/content/{content_id}/child/attachment",
                headers=headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
    
    def create_page(self, space_key: str, title: str, content: str = "", parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new page in Confluence."""
        page_data = {
            "type": "page",
            "title": title,
            "space": {
                "key": space_key
            },
            "body": {
                "storage": {
                    "value": content if content else f"<p>This page was created for {title}</p>",
                    "representation": "storage"
                }
            }
        }
        
        if parent_id:
            page_data["ancestors"] = [{"id": parent_id}]
        
        response = self._make_request('POST', 'rest/api/content', json=page_data)
        response.raise_for_status()
        return response.json()
    
    def get_content_by_title(self, space_key: str, title: str, content_type: str = 'page') -> Optional[Dict[str, Any]]:
        """Get content by title within a space."""
        cql = f'space = "{space_key}" and title = "{title}" and type = "{content_type}"'
        result = self.search_content(cql, limit=1, expand=['body.storage', 'version', 'space'])
        
        results = result.get('results', [])
        return results[0] if results else None


class ConfluenceUtils:
    """Utility functions for Confluence operations."""
    
    def __init__(self):
        """Initialize utilities."""
        self.confluence_client = ConfluenceClient()
    
    def create_content_filter(self, **kwargs) -> ContentFilter:
        """Create a ContentFilter from keyword arguments."""
        return ContentFilter(**kwargs)
    
    def build_cql_from_filter(self, filter_obj: ContentFilter) -> str:
        """Build CQL query from filter object."""
        parts = []
        
        if filter_obj.space_key:
            parts.append(f'space = "{filter_obj.space_key}"')
        
        if filter_obj.content_type:
            parts.append(f'type = "{filter_obj.content_type}"')
        
        if filter_obj.title_search:
            parts.append(f'title ~ "{filter_obj.title_search}"')
        
        if filter_obj.text_search:
            parts.append(f'text ~ "{filter_obj.text_search}"')
        
        if filter_obj.author:
            parts.append(f'creator = "{filter_obj.author}"')
        
        if filter_obj.created_after:
            parts.append(f'created >= "{filter_obj.created_after}"')
        
        if filter_obj.created_before:
            parts.append(f'created <= "{filter_obj.created_before}"')
        
        if filter_obj.modified_after:
            parts.append(f'lastModified >= "{filter_obj.modified_after}"')
        
        if filter_obj.modified_before:
            parts.append(f'lastModified <= "{filter_obj.modified_before}"')
        
        cql = ' AND '.join(parts) if parts else 'type = "page"'
        return cql + ' ORDER BY created DESC'
    
    def process_content_details(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance content details."""
        # Construct full web URL
        web_url = content.get('_links', {}).get('webui')
        if web_url and not web_url.startswith('http'):
            web_url = urljoin(self.confluence_client.confluence_url, web_url.lstrip('/'))
        
        return {
            'id': content.get('id'),
            'title': content.get('title', ''),
            'type': content.get('type', ''),
            'status': content.get('status', ''),
            'space': {
                'key': content.get('space', {}).get('key', ''),
                'name': content.get('space', {}).get('name', '')
            },
            'version': {
                'number': content.get('version', {}).get('number'),
                'when': content.get('version', {}).get('when'),
                'by': content.get('version', {}).get('by', {}).get('displayName')
            },
            'created_date': content.get('history', {}).get('createdDate'),
            'created_by': content.get('history', {}).get('createdBy', {}).get('displayName'),
            'last_updated': content.get('version', {}).get('when'),
            'web_url': web_url,
            'body_content': self._extract_body_content(content),
            'attachments_info': self._get_content_attachments_info(content.get('id')),
            'raw_content': content
        }
    
    def _extract_body_content(self, content: Dict[str, Any]) -> str:
        """Extract body content from content object."""
        body = content.get('body', {})
        
        # Try storage format first, then view
        if 'storage' in body:
            return body['storage'].get('value', '')
        elif 'view' in body:
            return body['view'].get('value', '')
        
        return ''
    
    def _get_content_attachments_info(self, content_id: str) -> List[Dict[str, Any]]:
        """Get attachment information for content."""
        if not content_id:
            return []
        
        try:
            result = self.confluence_client.get_content_attachments(content_id)
            attachments = result.get('results', [])
            return [self.process_attachment_info(att) for att in attachments]
        except Exception:
            return []
    
    def process_attachment_info(self, attachment: Dict[str, Any]) -> Dict[str, Any]:
        """Process single attachment info."""
        title = attachment.get('title', 'unknown')
        extensions = attachment.get('extensions', {})
        file_size = extensions.get('fileSize', 0)
        
        # Construct full URLs
        download_url = attachment.get('_links', {}).get('download', '')
        web_url = attachment.get('_links', {}).get('webui', '')
        
        # Convert relative URLs to full URLs
        if download_url and not download_url.startswith('http'):
            download_url = urljoin(self.confluence_client.confluence_url, download_url.lstrip('/'))
        if web_url and not web_url.startswith('http'):
            web_url = urljoin(self.confluence_client.confluence_url, web_url.lstrip('/'))
        
        return {
            'id': attachment.get('id'),
            'title': title,
            'file_extension': Path(title).suffix.lower() if '.' in title else '',
            'size_bytes': file_size,
            'size_human': self._format_file_size(file_size),
            'media_type': extensions.get('mediaType', ''),
            'created_date': attachment.get('version', {}).get('when', ''),
            'created_by': attachment.get('version', {}).get('by', {}).get('displayName', ''),
            'download_url': download_url,
            'web_url': web_url
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
            title = att.get('title', '').lower()
            if any(title.endswith(f'.{ft.lower()}') for ft in file_types):
                filtered.append(att)
        return filtered
    
    def list_space_attachments(self, space_key: str, file_types: Optional[List[str]] = None, 
                              max_content: int = 50) -> Dict[str, Any]:
        """List all attachments in a space."""
        # Get all content from space
        content_result = self.confluence_client.get_space_content(
            space_key, content_type='page', limit=max_content, expand=['version']
        )
        
        content_items = content_result.get('results', [])
        total_attachments = 0
        content_data = []
        
        for content in content_items:
            content_id = content.get('id')
            content_title = content.get('title', '')
            
            try:
                attachments_result = self.confluence_client.get_content_attachments(content_id)
                attachments = attachments_result.get('results', [])
                
                if file_types:
                    attachments = self.filter_attachments_by_type(attachments, file_types)
                
                if attachments:
                    content_data.append({
                        'content_id': content_id,
                        'content_title': content_title,
                        'content_type': content.get('type', ''),
                        'attachment_count': len(attachments),
                        'attachments': [self.process_attachment_info(att) for att in attachments]
                    })
                    total_attachments += len(attachments)
            except Exception as e:
                print(f"Error getting attachments for content {content_id}: {e}")
                continue
        
        return {
            'space_key': space_key,
            'total_content_with_attachments': len(content_data),
            'total_attachments': total_attachments,
            'content': content_data
        }
    
    def download_content_attachments(self, content_id: str, file_types: Optional[List[str]] = None,
                                   base_path: str = "confluence_attachments", organize_by_type: bool = False) -> Dict[str, Any]:
        """Download attachments from a specific content item."""
        # Get content info for folder naming
        try:
            content = self.confluence_client.get_content(content_id, expand=['space', 'version'])
            content_title = content.get('title', content_id)
            space_key = content.get('space', {}).get('key', 'unknown')
        except Exception:
            content_title = content_id
            space_key = 'unknown'
        
        # Sanitize title for folder name
        safe_title = "".join(c for c in content_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50] if safe_title else content_id
        
        attachments_result = self.confluence_client.get_content_attachments(content_id)
        attachments = attachments_result.get('results', [])
        
        if file_types:
            attachments = self.filter_attachments_by_type(attachments, file_types)
        
        download_dir = Path(base_path) / space_key / safe_title
        download_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'content_id': content_id,
            'content_title': content_title,
            'space_key': space_key,
            'total_attachments': len(attachments),
            'downloaded': 0,
            'failed': 0,
            'download_path': str(download_dir),
            'files': []
        }
        
        for attachment in attachments:
            title = attachment.get('title', 'unknown')
            download_url = attachment.get('_links', {}).get('download', '')
            
            if not download_url:
                results['files'].append({
                    'title': title,
                    'local_path': '',
                    'size_bytes': 0,
                    'download_success': False,
                    'error': 'No download URL available'
                })
                results['failed'] += 1
                continue
            
            local_path = download_dir / title
            
            # Handle duplicate filenames
            counter = 1
            original_path = local_path
            while local_path.exists():
                name = original_path.stem
                ext = original_path.suffix
                local_path = download_dir / f"{name}_{counter}{ext}"
                counter += 1
            
            success = self.confluence_client.download_attachment(download_url, str(local_path))
            
            file_info = {
                'title': title,
                'local_path': str(local_path),
                'size_bytes': attachment.get('extensions', {}).get('fileSize', 0),
                'download_success': success
            }
            
            if not success:
                file_info['error'] = 'Download failed'
            
            results['files'].append(file_info)
            
            if success:
                results['downloaded'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def download_space_attachments(self, space_key: str, file_types: Optional[List[str]] = None,
                                 base_path: str = "confluence_attachments", organize_by_type: bool = False,
                                 max_content: int = 50) -> Dict[str, Any]:
        """Download attachments from all content in a space."""
        space_dir = Path(base_path) / space_key
        space_dir.mkdir(parents=True, exist_ok=True)
        
        # Get content with attachments
        content_result = self.confluence_client.get_space_content(
            space_key, content_type='page', limit=max_content, expand=['version']
        )
        content_items = content_result.get('results', [])
        
        space_results = {
            'space_key': space_key,
            'total_content_processed': 0,
            'total_files_downloaded': 0,
            'total_files_failed': 0,
            'download_path': str(space_dir),
            'content': []
        }
        
        for content in content_items:
            content_id = content.get('id')
            
            try:
                # Check if content has attachments first
                attachments_result = self.confluence_client.get_content_attachments(content_id, limit=1)
                if not attachments_result.get('results'):
                    continue  # Skip content without attachments
                
                content_result = self.download_content_attachments(
                    content_id, file_types, str(space_dir), organize_by_type
                )
                
                if content_result['downloaded'] > 0 or content_result['failed'] > 0:
                    space_results['content'].append(content_result)
                    space_results['total_content_processed'] += 1
                    space_results['total_files_downloaded'] += content_result['downloaded']
                    space_results['total_files_failed'] += content_result['failed']
                    
            except Exception as e:
                print(f"Error processing content {content_id}: {e}")
                continue
        
        return space_results
    
    def generate_space_statistics(self, space_key: str, max_content: int = 200) -> Dict[str, Any]:
        """Generate comprehensive statistics for a space."""
        try:
            # Get space info
            space_info = self.confluence_client.get_space(space_key, expand=['description', 'metadata'])
            
            # Get content statistics
            pages_result = self.confluence_client.get_space_content(
                space_key, content_type='page', limit=max_content, expand=['version', 'space']
            )
            
            blogposts_result = self.confluence_client.get_space_content(
                space_key, content_type='blogpost', limit=max_content, expand=['version', 'space']
            )
            
            pages = pages_result.get('results', [])
            blogposts = blogposts_result.get('results', [])
            all_content = pages + blogposts
            
            # Calculate statistics
            stats = {
                'space_info': {
                    'key': space_info.get('key'),
                    'name': space_info.get('name'),
                    'description': space_info.get('description', {}).get('plain', {}).get('value', ''),
                    'type': space_info.get('type'),
                    'status': space_info.get('status')
                },
                'content_counts': {
                    'total_pages': len(pages),
                    'total_blogposts': len(blogposts),
                    'total_content': len(all_content)
                },
                'content_by_author': {},
                'content_by_month': {},
                'attachment_statistics': {'total_content_with_attachments': 0, 'total_attachments': 0}
            }
            
            # Analyze content
            for content in all_content:
                # Author statistics
                author = content.get('version', {}).get('by', {}).get('displayName', 'Unknown')
                stats['content_by_author'][author] = stats['content_by_author'].get(author, 0) + 1
                
                # Monthly statistics
                created_date = content.get('version', {}).get('when', '')
                if created_date:
                    try:
                        month = created_date[:7]  # YYYY-MM format
                        stats['content_by_month'][month] = stats['content_by_month'].get(month, 0) + 1
                    except Exception:
                        pass
                
                # Attachment statistics
                try:
                    attachments_result = self.confluence_client.get_content_attachments(content.get('id'))
                    attachment_count = len(attachments_result.get('results', []))
                    if attachment_count > 0:
                        stats['attachment_statistics']['total_content_with_attachments'] += 1
                        stats['attachment_statistics']['total_attachments'] += attachment_count
                except Exception:
                    pass
            
            return stats
            
        except Exception as e:
            raise Exception(f"Failed to generate statistics for space {space_key}: {str(e)}")
    
    def upload_file_to_content(self, content_id: str, file_path: str, filename: Optional[str] = None, 
                              comment: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to a Confluence content item."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'File not found: {file_path}',
                    'content_id': content_id
                }
            
            # Check file size (Confluence typically has a 25MB limit)
            file_size = file_path.stat().st_size
            max_size = 25 * 1024 * 1024  # 25MB
            if file_size > max_size:
                return {
                    'success': False,
                    'error': f'File too large: {file_size} bytes (max: {max_size} bytes)',
                    'content_id': content_id,
                    'file_size': file_size
                }
            
            # Validate content exists
            try:
                content = self.confluence_client.get_content(content_id, expand=['space'])
            except Exception:
                return {
                    'success': False,
                    'error': f'Content not found: {content_id}',
                    'content_id': content_id
                }
            
            # Upload the file
            result = self.confluence_client.upload_attachment(content_id, str(file_path), filename, comment)
            
            if result and 'results' in result:
                attachment_info = result['results'][0] if result['results'] else {}
                return {
                    'success': True,
                    'content_id': content_id,
                    'content_title': content.get('title', ''),
                    'space_key': content.get('space', {}).get('key', ''),
                    'attachment_id': attachment_info.get('id'),
                    'filename': attachment_info.get('title'),
                    'size_bytes': attachment_info.get('extensions', {}).get('fileSize', 0),
                    'upload_time': attachment_info.get('version', {}).get('when'),
                    'file_path': str(file_path),
                    'comment': comment
                }
            else:
                return {
                    'success': False,
                    'error': 'Upload failed - no response from server',
                    'content_id': content_id
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
                'content_id': content_id,
                'file_path': str(file_path) if 'file_path' in locals() else None
            }
    
    def upload_multiple_files_to_content(self, content_id: str, file_paths: List[str], 
                                        comment: Optional[str] = None) -> Dict[str, Any]:
        """Upload multiple files to a Confluence content item."""
        results = {
            'content_id': content_id,
            'total_files': len(file_paths),
            'successful_uploads': 0,
            'failed_uploads': 0,
            'files': []
        }
        
        for file_path in file_paths:
            result = self.upload_file_to_content(content_id, file_path, comment=comment)
            results['files'].append(result)
            
            if result['success']:
                results['successful_uploads'] += 1
            else:
                results['failed_uploads'] += 1
        
        return results
    
    def upload_file_to_page_by_title(self, space_key: str, page_title: str, file_path: str, 
                                    filename: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to a Confluence page by title."""
        try:
            # Find the page by title
            content = self.confluence_client.get_content_by_title(space_key, page_title, 'page')
            
            if not content:
                return {
                    'success': False,
                    'error': f'Page not found: "{page_title}" in space "{space_key}"',
                    'space_key': space_key,
                    'page_title': page_title
                }
            
            content_id = content['id']
            result = self.upload_file_to_content(content_id, file_path, filename, comment)
            result['page_title'] = page_title
            result['space_key'] = space_key
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
                'space_key': space_key,
                'page_title': page_title,
                'file_path': str(file_path) if 'file_path' in locals() else None
            }
    
    def create_page(self, space_key: str, title: str, content: str = "", parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new page in a Confluence space."""
        try:
            # Check if page already exists
            existing_page = self.confluence_client.get_content_by_title(space_key, title, 'page')
            if existing_page:
                # Construct full web URL for existing page
                existing_web_url = existing_page.get('_links', {}).get('webui', '')
                if existing_web_url and not existing_web_url.startswith('http'):
                    existing_web_url = urljoin(self.confluence_client.confluence_url, existing_web_url.lstrip('/'))
                
                return {
                    'success': False,
                    'error': f'Page with title "{title}" already exists in space "{space_key}"',
                    'existing_page': {
                        'id': existing_page['id'],
                        'title': existing_page['title'],
                        'web_url': existing_web_url
                    }
                }
            
            # Validate space exists
            try:
                space_info = self.confluence_client.get_space(space_key)
            except Exception:
                return {
                    'success': False,
                    'error': f'Space "{space_key}" not found or not accessible'
                }
            
            # Create the page
            result = self.confluence_client.create_page(space_key, title, content, parent_id)
            
            # Construct full web URL
            created_web_url = result.get('_links', {}).get('webui', '')
            if created_web_url and not created_web_url.startswith('http'):
                created_web_url = urljoin(self.confluence_client.confluence_url, created_web_url.lstrip('/'))
            
            return {
                'success': True,
                'page_created': True,
                'page_id': result['id'],
                'title': result['title'],
                'space_key': space_key,
                'web_url': created_web_url,
                'content_length': len(content) if content else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create page: {str(e)}',
                'space_key': space_key,
                'title': title
            }
    
    def create_page_and_upload_file(self, space_key: str, page_title: str, file_path: str, 
                                   page_content: str = "", filename: Optional[str] = None, 
                                   comment: Optional[str] = None, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new page and upload a file to it."""
        try:
            # Step 1: Create the page
            create_result = self.create_page(space_key, page_title, page_content, parent_id)
            
            if not create_result['success']:
                # If page already exists, try to upload to it
                if 'already exists' in create_result.get('error', ''):
                    existing_page = create_result.get('existing_page', {})
                    page_id = existing_page.get('id')
                    if page_id:
                        print(f"📄 Page already exists, uploading to existing page: {page_title}")
                        upload_result = self.upload_file_to_content(page_id, file_path, filename, comment)
                        upload_result['page_created'] = False
                        upload_result['page_already_existed'] = True
                        return upload_result
                
                return create_result
            
            # Step 2: Upload file to the newly created page
            page_id = create_result['page_id']
            upload_result = self.upload_file_to_content(page_id, file_path, filename, comment)
            
            # Combine results
            if upload_result['success']:
                return {
                    'success': True,
                    'page_created': True,
                    'page_id': page_id,
                    'page_title': page_title,
                    'space_key': space_key,
                    'web_url': create_result.get('web_url', ''),
                    'upload_result': upload_result,
                    'summary': f'Created page "{page_title}" and uploaded {Path(file_path).name}'
                }
            else:
                return {
                    'success': False,
                    'page_created': True,
                    'page_id': page_id,
                    'page_title': page_title,
                    'error': f'Page created but upload failed: {upload_result.get("error", "Unknown error")}',
                    'upload_result': upload_result
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create page and upload file: {str(e)}',
                'space_key': space_key,
                'page_title': page_title,
                'file_path': file_path
            }
    
    def upload_file_to_page_or_create(self, space_key: str, page_title: str, file_path: str, 
                                     page_content: str = "", filename: Optional[str] = None, 
                                     comment: Optional[str] = None) -> Dict[str, Any]:
        """Upload file to page, creating the page if it doesn't exist."""
        try:
            # First try to upload to existing page
            upload_result = self.upload_file_to_page_by_title(space_key, page_title, file_path, filename, comment)
            
            # If page not found, create it and upload
            if not upload_result['success'] and 'not found' in upload_result.get('error', '').lower():
                print(f"📄 Page '{page_title}' not found, creating it...")
                return self.create_page_and_upload_file(space_key, page_title, file_path, page_content, filename, comment)
            
            # If upload succeeded or failed for other reasons, return the result
            upload_result['page_created'] = False
            return upload_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to upload file to page or create: {str(e)}',
                'space_key': space_key,
                'page_title': page_title,
                'file_path': file_path
            }