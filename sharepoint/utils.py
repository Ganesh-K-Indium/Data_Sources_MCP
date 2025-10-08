"""
SharePoint Utility Functions (Multi-Site Mode)
Core functions for interacting with SharePoint via Microsoft Graph API

This module provides the SharePointClient for multi-site SharePoint operations.
It requires the following environment variables:
- SHAREPOINT_TENANT_ID: Your Azure AD tenant ID
- SHAREPOINT_CLIENT_ID: Your app registration client ID
- SHAREPOINT_CLIENT_SECRET: Your app registration client secret
- SHAREPOINT_SITE_URL: Base SharePoint URL (optional, for default site)

For single-site mode, see: ingestion_workflow_clean/IngestionGraph/utils/sharepoint.py
"""
import os
import json
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class SharePointClient:
    """
    Client for SharePoint operations using Microsoft Graph API (Multi-Site Mode)
    
    This client supports working with multiple SharePoint sites by accepting
    site_url as a parameter for most operations.
    
    Environment Variables Required:
        SHAREPOINT_TENANT_ID: Azure AD tenant ID
        SHAREPOINT_CLIENT_ID: App registration client ID
        SHAREPOINT_CLIENT_SECRET: App registration client secret
        
    Usage:
        client = SharePointClient()
        sites = client.list_sites()
        files = client.list_files(site_url="https://...", library_name="Documents")
    """
    
    def __init__(self):
        """Initialize SharePoint client with OAuth2 credentials"""
        # Support both new (SHAREPOINT_*) and legacy (TENANT_ID, CLIENT_ID) credential names
        self.tenant_id = os.getenv("SHAREPOINT_TENANT_ID") or os.getenv("TENANT_ID")
        self.client_id = os.getenv("SHAREPOINT_CLIENT_ID") or os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET") or os.getenv("CLIENT_SECRET")
        self.site_url = os.getenv("SHAREPOINT_SITE_URL") or os.getenv("SHAREPOINT_URL")
        
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Missing SharePoint credentials in environment variables")
        
        self.access_token = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Microsoft Graph API"""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        self.access_token = response.json()["access_token"]
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _get_site_id(self, site_url: str) -> str:
        """Get site ID from site URL"""
        # Extract hostname and site path
        parts = site_url.replace("https://", "").split("/")
        hostname = parts[0]
        site_path = "/".join(parts[1:]) if len(parts) > 1 else ""
        
        # Get site by path
        url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{site_path}"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        
        return response.json()["id"]
    
    def list_sites(self) -> List[Dict[str, Any]]:
        """List all accessible SharePoint sites"""
        url = "https://graph.microsoft.com/v1.0/sites?search=*"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        
        sites = response.json().get("value", [])
        return [
            {
                "name": site.get("displayName"),
                "url": site.get("webUrl"),
                "id": site.get("id"),
                "description": site.get("description", "")
            }
            for site in sites
        ]
    
    def list_libraries(self, site_url: str) -> List[Dict[str, Any]]:
        """List document libraries in a site"""
        site_id = self._get_site_id(site_url)
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        
        libraries = response.json().get("value", [])
        return [
            {
                "name": lib.get("name"),
                "id": lib.get("id"),
                "description": lib.get("description", ""),
                "webUrl": lib.get("webUrl")
            }
            for lib in libraries
        ]
    
    def list_files(
        self, 
        site_url: str, 
        library_name: str = "Documents",
        folder_path: str = ""
    ) -> List[Dict[str, Any]]:
        """List files in a library or folder"""
        site_id = self._get_site_id(site_url)
        
        # Get drive ID for library
        libraries = self.list_libraries(site_url)
        library = next((lib for lib in libraries if lib["name"] == library_name), None)
        
        if not library:
            raise ValueError(f"Library '{library_name}' not found")
        
        drive_id = library["id"]
        
        # Build URL for folder or root
        if folder_path:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{folder_path}:/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"
        
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        
        items = response.json().get("value", [])
        files = []
        
        for item in items:
            if "file" in item:  # It's a file, not a folder
                files.append({
                    "name": item.get("name"),
                    "size": item.get("size"),
                    "modified": item.get("lastModifiedDateTime"),
                    "downloadUrl": item.get("@microsoft.graph.downloadUrl"),
                    "webUrl": item.get("webUrl"),
                    "id": item.get("id")
                })
        
        return files
    
    def download_file(self, download_url: str, destination_path: str) -> bool:
        """
        Download a file from SharePoint
        
        Args:
            download_url: Direct download URL for the file
            destination_path: Local path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_path) or ".", exist_ok=True)
            
            with open(destination_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
        except Exception:
            return False
    
    def search_content(
        self, 
        query: str, 
        site_url: Optional[str] = None,
        file_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for content in SharePoint
        
        Args:
            query: Search query string
            site_url: Optional SharePoint site URL to search within
            file_types: Optional list of file extensions to filter (e.g., ['pdf', 'docx'])
            
        Returns:
            List of matching files with metadata
        """
        if site_url:
            site_id = self._get_site_id(site_url)
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/search(q='{query}')"
        else:
            url = f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{query}')"
        
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        
        items = response.json().get("value", [])
        results = []
        
        for item in items:
            if "file" not in item:
                continue
                
            file_name = item.get("name", "")
            
            # Filter by file types if specified
            if file_types:
                file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""
                if file_extension not in [ft.lower().strip(".") for ft in file_types]:
                    continue
            
            results.append({
                "name": file_name,
                "path": item.get("parentReference", {}).get("path"),
                "webUrl": item.get("webUrl"),
                "downloadUrl": item.get("@microsoft.graph.downloadUrl"),
                "modified": item.get("lastModifiedDateTime"),
                "size": item.get("size")
            })
        
        return results
    
    def find_file_by_name(
        self,
        file_name: str,
        site_url: str,
        library_name: str = "Documents",
        folder_path: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Find a file by name in SharePoint
        
        Args:
            file_name: Name of the file to find
            site_url: SharePoint site URL
            library_name: Name of the document library
            folder_path: Path to folder within library
            
        Returns:
            File dictionary if found, None otherwise
        """
        files = self.list_files(site_url, library_name, folder_path)
        
        for file in files:
            if file["name"] == file_name:
                return file
        
        return None
    
    def upload_file(
        self,
        local_file_path: str,
        site_url: str,
        library_name: str = "Documents",
        folder_path: str = "",
        remote_file_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a file to SharePoint
        
        Args:
            local_file_path: Path to local file to upload
            site_url: SharePoint site URL
            library_name: Name of the document library
            folder_path: Path to folder within library
            remote_file_name: Optional remote filename (uses local name if not provided)
            
        Returns:
            File information dictionary if successful, None otherwise
        """
        try:
            site_id = self._get_site_id(site_url)
            
            # Get drive ID for library
            libraries = self.list_libraries(site_url)
            library = next((lib for lib in libraries if lib["name"] == library_name), None)
            
            if not library:
                raise ValueError(f"Library '{library_name}' not found")
            
            drive_id = library["id"]
            
            # Use local filename if remote name not provided
            if not remote_file_name:
                remote_file_name = os.path.basename(local_file_path)
            
            # Build upload URL
            if folder_path:
                upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{folder_path}/{remote_file_name}:/content"
            else:
                upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{remote_file_name}:/content"
            
            # Read file content
            with open(local_file_path, 'rb') as f:
                file_content = f.read()
            
            # Upload file
            headers = self._get_headers()
            headers["Content-Type"] = "application/octet-stream"
            
            response = requests.put(upload_url, headers=headers, data=file_content)
            response.raise_for_status()
            
            file_info = response.json()
            return {
                "name": file_info.get("name"),
                "id": file_info.get("id"),
                "size": file_info.get("size"),
                "webUrl": file_info.get("webUrl"),
                "modified": file_info.get("lastModifiedDateTime")
            }
            
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None


# Utility functions for MCP tools (single-site compatibility mode)
def list_sharepoint_files(library_name: str = "Documents", folder_path: str = "") -> List[Dict[str, Any]]:
    """
    List files in SharePoint library (single-site mode)
    Uses SHAREPOINT_SITE_URL from environment
    """
    try:
        client = SharePointClient()
        if not client.site_url:
            raise ValueError("SHAREPOINT_SITE_URL or SHAREPOINT_URL not set in environment")
        
        files = client.list_files(client.site_url, library_name, folder_path)
        return files
    except Exception as e:
        print(f"Error listing files: {str(e)}")
        return []


def download_specific_sharepoint_file(
    file_name: str,
    library_name: str = "Documents",
    folder_path: str = "",
    local_folder: str = "downloaded_files"
) -> Optional[str]:
    """
    Download a specific file from SharePoint (single-site mode)
    
    Args:
        file_name: Name of the file to download
        library_name: Document library name
        folder_path: Folder path within library
        local_folder: Local folder to save file
        
    Returns:
        Local file path if successful, None otherwise
    """
    try:
        client = SharePointClient()
        if not client.site_url:
            raise ValueError("SHAREPOINT_SITE_URL or SHAREPOINT_URL not set in environment")
        
        # Find the file
        file_info = client.find_file_by_name(file_name, client.site_url, library_name, folder_path)
        
        if not file_info:
            print(f"File '{file_name}' not found")
            return None
        
        # Create local folder
        os.makedirs(local_folder, exist_ok=True)
        local_path = os.path.join(local_folder, file_name)
        
        # Download the file
        if client.download_file(file_info["downloadUrl"], local_path):
            print(f"Downloaded: {file_name} -> {local_path}")
            return local_path
        else:
            print(f"Failed to download: {file_name}")
            return None
            
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return None


def download_pdfs_from_sharepoint(
    library_name: str = "Documents",
    folder_path: str = "",
    local_folder: str = "sharepoint_pdfs"
) -> List[str]:
    """
    Download all PDF files from SharePoint (single-site mode)
    
    Args:
        library_name: Document library name
        folder_path: Folder path within library
        local_folder: Local folder to save PDFs
        
    Returns:
        List of local file paths for downloaded PDFs
    """
    try:
        client = SharePointClient()
        if not client.site_url:
            raise ValueError("SHAREPOINT_SITE_URL or SHAREPOINT_URL not set in environment")
        
        # Create local folder
        os.makedirs(local_folder, exist_ok=True)
        
        # List all files
        files = client.list_files(client.site_url, library_name, folder_path)
        
        # Filter PDF files
        pdf_files = [f for f in files if f["name"].lower().endswith('.pdf')]
        
        if not pdf_files:
            print("No PDF files found")
            return []
        
        downloaded_files = []
        
        for file in pdf_files:
            file_name = file["name"]
            local_path = os.path.join(local_folder, file_name)
            
            print(f"Downloading: {file_name}")
            
            if client.download_file(file["downloadUrl"], local_path):
                downloaded_files.append(local_path)
                print(f"Successfully downloaded: {file_name}")
            else:
                print(f"Failed to download: {file_name}")
        
        return downloaded_files
        
    except Exception as e:
        print(f"Error downloading PDFs: {str(e)}")
        return []


def download_file_by_sharepoint_path(
    file_path: str,
    library_name: str = "Documents",
    local_path: Optional[str] = None
) -> bool:
    """
    Download a file by its SharePoint path (single-site mode)
    
    Args:
        file_path: Full path to file (e.g., "folder/subfolder/file.pdf")
        library_name: Document library name
        local_path: Optional local path to save file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Split path into folder and filename
        parts = file_path.rsplit('/', 1)
        if len(parts) == 2:
            folder_path, file_name = parts
        else:
            folder_path = ""
            file_name = parts[0]
        
        # If no local path specified, use current directory
        if not local_path:
            local_path = file_name
        
        # Create directory if needed
        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        
        # Download the file
        result = download_specific_sharepoint_file(
            file_name=file_name,
            library_name=library_name,
            folder_path=folder_path,
            local_folder=os.path.dirname(local_path) or "."
        )
        
        return result is not None
        
    except Exception as e:
        print(f"Error downloading file by path: {str(e)}")
        return False


def upload_file_to_sharepoint(
    local_file_path: str,
    library_name: str = "Documents",
    folder_path: str = "",
    remote_file_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Upload a file to SharePoint (single-site mode)
    
    Args:
        local_file_path: Path to local file
        library_name: Document library name
        folder_path: Folder path within library
        remote_file_name: Optional remote filename
        
    Returns:
        File information dictionary if successful, None otherwise
    """
    try:
        client = SharePointClient()
        if not client.site_url:
            raise ValueError("SHAREPOINT_SITE_URL or SHAREPOINT_URL not set in environment")
        
        return client.upload_file(
            local_file_path,
            client.site_url,
            library_name,
            folder_path,
            remote_file_name
        )
        
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return None


def bulk_upload_to_sharepoint(
    local_files: List[str],
    library_name: str = "Documents",
    folder_path: str = ""
) -> List[Dict[str, Any]]:
    """
    Upload multiple files to SharePoint (single-site mode)
    
    Args:
        local_files: List of local file paths
        library_name: Document library name
        folder_path: Folder path within library
        
    Returns:
        List of successfully uploaded file information dictionaries
    """
    uploaded_files = []
    
    print(f"Starting bulk upload of {len(local_files)} file(s)...")
    
    for i, local_file in enumerate(local_files, 1):
        print(f"\n[{i}/{len(local_files)}] Uploading: {os.path.basename(local_file)}")
        
        file_info = upload_file_to_sharepoint(local_file, library_name, folder_path)
        
        if file_info:
            uploaded_files.append(file_info)
            print(f"   ✅ Success")
        else:
            print(f"   ❌ Failed")
    
    print(f"\n📊 Upload Summary:")
    print(f"   Total: {len(local_files)} files")
    print(f"   Successful: {len(uploaded_files)} files")
    print(f"   Failed: {len(local_files) - len(uploaded_files)} files")
    
    return uploaded_files


def find_sharepoint_file(
    file_name: str,
    library_name: str = "Documents",
    folder_path: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Find a file in SharePoint (single-site mode)
    
    Args:
        file_name: Name of file to find
        library_name: Document library name
        folder_path: Folder path within library
        
    Returns:
        File information dictionary or None if not found
    """
    try:
        client = SharePointClient()
        if not client.site_url:
            raise ValueError("SHAREPOINT_SITE_URL or SHAREPOINT_URL not set in environment")
        
        return client.find_file_by_name(file_name, client.site_url, library_name, folder_path)
        
    except Exception as e:
        print(f"Error finding file: {str(e)}")
        return None


def test_sharepoint_connection() -> Dict[str, Any]:
    """
    Test SharePoint connection (single-site mode)
    
    Returns:
        Dictionary with connection status and available libraries
    """
    try:
        client = SharePointClient()
        if not client.site_url:
            return {"error": "SHAREPOINT_SITE_URL or SHAREPOINT_URL not set in environment"}
        
        # Try to list libraries
        libraries = client.list_libraries(client.site_url)
        
        return {
            "status": "connected",
            "site_url": client.site_url,
            "libraries": [lib["name"] for lib in libraries]
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }


# Multi-site utility functions for MCP tools
def list_sharepoint_sites() -> str:
    """List all SharePoint sites"""
    try:
        client = SharePointClient()
        sites = client.list_sites()
        return json.dumps(sites, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def list_sharepoint_libraries(site_url: Optional[str] = None) -> str:
    """List libraries in a SharePoint site"""
    try:
        client = SharePointClient()
        if not site_url:
            site_url = client.site_url
        if not site_url:
            return json.dumps({"error": "No site URL provided"})
        
        libraries = client.list_libraries(site_url)
        return json.dumps(libraries, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def search_sharepoint_content(
    query: str,
    site_url: Optional[str] = None,
    file_types: Optional[List[str]] = None
) -> str:
    """Search SharePoint content"""
    try:
        client = SharePointClient()
        results = client.search_content(query, site_url, file_types)
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
