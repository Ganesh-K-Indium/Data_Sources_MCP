"""
Google Drive Utility Functions
Core functions for interacting with Google Drive API
"""
import os
import json
import io
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GoogleDriveClient:
    """Client for Google Drive operations using Service Account"""
    
    def __init__(self):
        """Initialize Google Drive client with service account credentials"""
        # Define scopes - updated to allow read/write
        self.scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        if credentials_json:
            try:
                creds_info = json.loads(credentials_json)
                self.credentials = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=self.scopes
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in GOOGLE_CREDENTIALS: {credentials_json}")
                

        else:
            self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
            if not os.path.exists(self.credentials_path):
                raise ValueError(
                    f"Service account file not found: {self.credentials_path}\n"
                    f"Please ensure GOOGLE_APPLICATION_CREDENTIALS environment variable "
                    f"points to a valid service account JSON file, or set GOOGLE_CREDENTIALS "
                    f"with the JSON content."
                )
            self.credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.scopes
            )
        
        # Build service
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def list_files(
        self, 
        folder_id: str = 'root',
        file_types: Optional[List[str]] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List files in a Google Drive folder
        
        Args:
            folder_id: Folder ID (default: 'root')
            file_types: Filter by file extensions (e.g., ['pdf', 'docx'])
            page_size: Number of results per page
            
        Returns:
            List of file dictionaries
        """
        query = f"'{folder_id}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'"
        
        if file_types:
            type_queries = [f"name contains '.{ext}'" for ext in file_types]
            query += " and (" + " or ".join(type_queries) + ")"
        
        results = self.service.files().list(
            q=query,
            pageSize=page_size,
            fields="nextPageToken, files(id, name, size, modifiedTime, mimeType, webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        return [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "size": int(f.get("size", 0)),
                "modified": f.get("modifiedTime"),
                "mimeType": f.get("mimeType"),
                "webViewLink": f.get("webViewLink")
            }
            for f in files
        ]
    
    def list_folders(self, parent_folder_id: str = 'root') -> List[Dict[str, Any]]:
        """
        List folders in Google Drive
        
        Args:
            parent_folder_id: Parent folder ID (default: 'root')
            
        Returns:
            List of folder dictionaries
        """
        query = f"'{parent_folder_id}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'"
        
        results = self.service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, modifiedTime, webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        folders = results.get('files', [])
        
        return [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "modified": f.get("modifiedTime"),
                "webViewLink": f.get("webViewLink")
            }
            for f in folders
        ]
    
    def download_file(self, file_id: str, destination_path: str) -> str:
        """
        Download a file from Google Drive
        
        Args:
            file_id: Google Drive file ID
            destination_path: Local path to save file (can be directory or full file path)
            
        Returns:
            Path to downloaded file
        """
        # Get file metadata to get the original filename
        file_metadata = self.service.files().get(
            fileId=file_id, 
            fields='name',
            supportsAllDrives=True
        ).execute()
        original_filename = file_metadata.get('name', 'download')
        
        # If destination_path is a directory, append the filename
        if os.path.isdir(destination_path):
            destination_path = os.path.join(destination_path, original_filename)
        elif not destination_path.endswith(('.pdf', '.txt', '.doc', '.docx')):
            # If path doesn't end with an extension, treat it as a directory
            os.makedirs(destination_path, exist_ok=True)
            destination_path = os.path.join(destination_path, original_filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Download the file
        request = self.service.files().get_media(
            fileId=file_id,
            supportsAllDrives=True
        )
        fh = io.FileIO(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        fh.close()
        return destination_path
    
    def search_files(
        self, 
        query: str,
        folder_id: Optional[str] = None,
        file_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for files in Google Drive
        
        Args:
            query: Search query string
            folder_id: Limit search to specific folder
            file_types: Filter by file extensions
            
        Returns:
            List of matching files
        """
        search_query = f"name contains '{query}' and trashed=false"
        
        if folder_id:
            search_query += f" and '{folder_id}' in parents"
        
        if file_types:
            type_queries = [f"name contains '.{ext}'" for ext in file_types]
            search_query += " and (" + " or ".join(type_queries) + ")"
        
        results = self.service.files().list(
            q=search_query,
            pageSize=50,
            fields="nextPageToken, files(id, name, size, modifiedTime, mimeType, webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        return [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "size": int(f.get("size", 0)),
                "modified": f.get("modifiedTime"),
                "mimeType": f.get("mimeType"),
                "webViewLink": f.get("webViewLink")
            }
            for f in files
        ]
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get detailed metadata for a file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata dictionary
        """
        file = self.service.files().get(
            fileId=file_id,
            fields="id, name, size, mimeType, modifiedTime, createdTime, owners, shared, webViewLink, webContentLink",
            supportsAllDrives=True
        ).execute()
        
        return {
            "id": file.get("id"),
            "name": file.get("name"),
            "size": int(file.get("size", 0)),
            "mimeType": file.get("mimeType"),
            "modified": file.get("modifiedTime"),
            "created": file.get("createdTime"),
            "owners": file.get("owners", []),
            "shared": file.get("shared", False),
            "webViewLink": file.get("webViewLink"),
            "downloadLink": file.get("webContentLink")
        }
    
    def find_file_by_name(
        self, 
        file_name: str,
        folder_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a file by name (optionally within a specific folder)
        
        Args:
            file_name: Name of the file to find
            folder_name: Name of the folder to search in (optional)
            
        Returns:
            File dictionary if found, None otherwise
        """
        # First, find the folder ID if folder_name is provided
        folder_id = None
        if folder_name:
            folder_id = self.find_folder_by_name(folder_name)
            if not folder_id:
                return None
        
        # Search for the file
        query = f"name = '{file_name}' and trashed=false and mimeType!='application/vnd.google-apps.folder'"
        
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            pageSize=1,
            fields="files(id, name, size, modifiedTime, mimeType, webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            f = files[0]
            return {
                "id": f.get("id"),
                "name": f.get("name"),
                "size": int(f.get("size", 0)),
                "modified": f.get("modifiedTime"),
                "mimeType": f.get("mimeType"),
                "webViewLink": f.get("webViewLink")
            }
        
        return None
    
    def find_folder_by_name(
        self, 
        folder_name: str,
        parent_folder_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Find a folder ID by name (includes shared folders)
        
        Args:
            folder_name: Name of the folder to find
            parent_folder_name: Name of parent folder (optional)
            
        Returns:
            Folder ID if found, None otherwise
        """
        # If parent folder specified, search within it
        if parent_folder_name:
            parent_id = self.find_folder_by_name(parent_folder_name)
            if not parent_id:
                return None
            
            # Search for the folder within parent
            query = f"name = '{folder_name}' and trashed=false and mimeType='application/vnd.google-apps.folder'"
            query += f" and '{parent_id}' in parents"
        else:
            # Search globally for the folder (includes shared folders)
            query = f"name = '{folder_name}' and trashed=false and mimeType='application/vnd.google-apps.folder'"
        
        results = self.service.files().list(
            q=query,
            pageSize=10,  # Get up to 10 results in case of duplicates
            fields="files(id, name, shared, owners)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            # If multiple folders found, prefer shared folders
            for folder in folders:
                if folder.get('shared', False):
                    return folder.get('id')
            # If no shared folder, return first result
            return folders[0].get('id')
        
        return None

    def upload_file(
        self, 
        file_path: str,
        folder_id: str = 'root',
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Local path to file to upload
            folder_id: Destination folder ID (default: 'root')
            file_name: Name for the uploaded file (default: original filename)
            
        Returns:
            Dictionary with uploaded file information
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        # Use original filename if not specified
        if not file_name:
            file_name = os.path.basename(file_path)
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, size, mimeType, webViewLink',
            supportsAllDrives=True  # Required for shared folders/drives
        ).execute()
        
        return {
            "id": file.get("id"),
            "name": file.get("name"),
            "size": int(file.get("size", 0)),
            "mimeType": file.get("mimeType"),
            "webViewLink": file.get("webViewLink")
        }
    
    def create_folder(
        self, 
        folder_name: str,
        parent_folder_id: str = 'root'
    ) -> Dict[str, Any]:
        """
        Create a new folder in Google Drive
        
        Args:
            folder_name: Name of the new folder
            parent_folder_id: Parent folder ID (default: 'root')
            
        Returns:
            Dictionary with created folder information
        """
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        
        folder = self.service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        return {
            "id": folder.get("id"),
            "name": folder.get("name"),
            "webViewLink": folder.get("webViewLink")
        }
    
    def test_connection(self) -> bool:
        """
        Test Google Drive connection
        
        Returns:
            True if connection is successful
        """
        try:
            self.service.files().list(pageSize=1).execute()
            return True
        except Exception:
            return False


# Utility functions for MCP tools
def list_gdrive_files(input_json: str = "{}") -> str:
    """List files in Google Drive folder"""
    try:
        params = json.loads(input_json)
        client = GoogleDriveClient()
        files = client.list_files(
            folder_id=params.get("folder_id", "root"),
            file_types=params.get("file_types")
        )
        return json.dumps(files, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def list_gdrive_folders(input_json: str = "{}") -> str:
    """List folders in Google Drive"""
    try:
        params = json.loads(input_json)
        client = GoogleDriveClient()
        folders = client.list_folders(
            parent_folder_id=params.get("parent_folder_id", "root")
        )
        return json.dumps(folders, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def download_gdrive_file(input_json: str) -> str:
    """Download a file from Google Drive"""
    try:
        params = json.loads(input_json)
        client = GoogleDriveClient()
        path = client.download_file(
            file_id=params["file_id"],
            destination_path=params["destination_path"]
        )
        return json.dumps({"success": True, "path": path})
    except Exception as e:
        return json.dumps({"error": str(e)})


def search_gdrive_content(input_json: str) -> str:
    """Search Google Drive content"""
    try:
        params = json.loads(input_json)
        client = GoogleDriveClient()
        results = client.search_files(
            query=params["query"],
            folder_id=params.get("folder_id"),
            file_types=params.get("file_types")
        )
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_gdrive_file_metadata(file_id: str) -> str:
    """Get file metadata from Google Drive"""
    try:
        client = GoogleDriveClient()
        metadata = client.get_file_metadata(file_id)
        return json.dumps(metadata, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
