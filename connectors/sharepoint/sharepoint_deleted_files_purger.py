import logging
import os
import asyncio
import aiohttp
import re
import urllib.parse
import traceback
from collections import defaultdict
from tools import AISearchClient
from typing import Any, Dict, List, Optional


class SharepointDeletedFilesPurger:
    def __init__(self, index_name: Optional[str] = None, target_folder_path: Optional[str] = None):
        # Initialize configuration from environment variables
        self.connector_enabled = os.getenv("SHAREPOINT_CONNECTOR_ENABLED", "false").lower() == "true"
        self.tenant_id = os.getenv("SHAREPOINT_TENANT_ID")
        self.client_id = os.getenv("SHAREPOINT_CLIENT_ID")
        # Get client secret directly from environment variable instead of KeyVault
        self.client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET")
        # Use provided index name or fall back to environment variable
        self.index_name = index_name or os.getenv("AZURE_SEARCH_SHAREPOINT_INDEX_NAME", "sharepoint-index-1")
        self.site_domain = os.getenv("SHAREPOINT_SITE_DOMAIN")
        # Handle empty site name for root site (consistent with indexer)
        self.site_name = os.getenv("SHAREPOINT_SITE_NAME", "").strip() or None
        # Target folder path - if provided, only check for file existence in this specific folder
        self.target_folder_path = target_folder_path or os.getenv("SHAREPOINT_TARGET_FOLDER_PATH")
        
        # Construct SharePoint host and site for Graph API endpoints
        if self.site_domain:
            self.sharepoint_host = f"https://{self.site_domain}"
            self.sharepoint_site = self.site_name or ""  # Empty string for root site
        else:
            self.sharepoint_host = None
            self.sharepoint_site = None
        
        self.search_client: Optional[AISearchClient] = None
        self.site_id: Optional[str] = None
        self.access_token: Optional[str] = None

    async def initialize_clients(self) -> bool:
        """Initialize AISearchClient and validate configuration."""
        # Check for missing environment variables
        required_vars = {
            "SHAREPOINT_TENANT_ID": self.tenant_id,
            "SHAREPOINT_CLIENT_ID": self.client_id,
            "SHAREPOINT_CLIENT_SECRET": self.client_secret,
            "SHAREPOINT_SITE_DOMAIN": self.site_domain
        }
        
        # SHAREPOINT_SITE_NAME is optional (can be empty for root site)
        optional_vars = {
            "SHAREPOINT_SITE_NAME": self.site_name
        }

        missing_env_vars = [var for var, value in required_vars.items() if not value]

        # Check index name separately since it can come from UI or env var
        if not self.index_name:
            missing_env_vars.append("INDEX_NAME")

        if missing_env_vars:
            logging.error(
                f"[sharepoint_purge_deleted_files] Missing environment variables: {', '.join(missing_env_vars)}. "
                "Please set all required environment variables."
            )
            return False
        
        # Log configuration for debugging
        logging.info(f"[sharepoint_purge_deleted_files] Using index: {self.index_name}")
        if self.index_name != os.getenv("AZURE_SEARCH_SHAREPOINT_INDEX_NAME"):
            logging.info(f"[sharepoint_purge_deleted_files] Index name provided via parameter (UI selection)")
        else:
            logging.info(f"[sharepoint_purge_deleted_files] Index name from environment variable")
        
        # Log optional variable status for debugging
        for var, value in optional_vars.items():
            if not value:
                logging.info(f"[sharepoint_purge_deleted_files] {var} is empty - will use root site")
            else:
                logging.info(f"[sharepoint_purge_deleted_files] {var} = '{value}'")
        
        # Log target folder configuration
        if self.target_folder_path:
            logging.info(f"[sharepoint_purge_deleted_files] Target folder path: {self.target_folder_path}")
            logging.info(f"[sharepoint_purge_deleted_files] Will only check for file existence in the target folder")
        else:
            logging.info(f"[sharepoint_purge_deleted_files] No target folder specified - will check for file existence anywhere in SharePoint")

        # Initialize AISearchClient
        try:
            self.search_client = AISearchClient()
            logging.debug("[sharepoint_purge_deleted_files] Initialized AISearchClient successfully.")
        except ValueError as ve:
            logging.error(f"[sharepoint_purge_deleted_files] AISearchClient initialization failed: {ve}")
            return False
        except Exception as e:
            logging.error(f"[sharepoint_purge_deleted_files] Unexpected error during AISearchClient initialization: {e}")
            return False

        return True

    async def get_graph_access_token(self) -> Optional[str]:
        """Obtain access token for Microsoft Graph API."""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(token_url, headers=headers, data=data) as resp:
                    if resp.status == 200:
                        token_response = await resp.json()
                        access_token = token_response.get("access_token")
                        logging.debug("[sharepoint_purge_deleted_files] Successfully obtained access token for Microsoft Graph API.")
                        return access_token
                    else:
                        error_response = await resp.text()
                        logging.error(f"[sharepoint_purge_deleted_files] Failed to obtain access token: {resp.status} - {error_response}")
                        return None
            except Exception as e:
                logging.error(f"[sharepoint_purge_deleted_files] Exception while obtaining access token: {e}")
                return None

    async def get_site_id(self) -> Optional[str]:
        """Retrieve the SharePoint site ID using Microsoft Graph API."""
        access_token = await self.get_graph_access_token()
        if not access_token:
            return None

        # Construct URL based on whether we're targeting root site or named site
        if self.site_name:
            # For named sites: /sites/{domain}:/sites/{site_name}
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_domain}:/sites/{self.site_name}?$select=id"
        else:
            # For root site: /sites/{domain}
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_domain}?$select=id"
            
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        site_id = data.get("id", None)
                        if site_id:
                            site_type = "root" if not self.site_name else f"'{self.site_name}'"
                            logging.info(f"[sharepoint_purge_deleted_files] Successfully retrieved site ID for {site_type} site.")
                            return site_id
                        else:
                            logging.error("[sharepoint_purge_deleted_files] 'id' field not found in site response.")
                            return None
                    else:
                        error_response = await resp.text()
                        logging.error(f"[sharepoint_purge_deleted_files] Failed to retrieve site ID: {resp.status} - {error_response}")
                        return None
            except Exception as e:
                logging.error(f"[sharepoint_purge_deleted_files] Exception while retrieving site ID: {e}")
                return None

    async def get_drive_id(self, headers: Dict[str, str]) -> Optional[str]:
        """Get the SharePoint drive ID for the configured site."""
        if not self.site_id:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                # Get the default drive for the site
                drive_url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive"
                logging.debug(f"[sharepoint_purge_deleted_files] Getting drive ID from: {drive_url}")
                
                async with session.get(drive_url, headers=headers) as resp:
                    if resp.status == 200:
                        drive_data = await resp.json()
                        drive_id = drive_data.get('id')
                        if drive_id:
                            logging.debug(f"[sharepoint_purge_deleted_files] Got drive ID: {drive_id}")
                            return drive_id
                        else:
                            logging.error(f"[sharepoint_purge_deleted_files] No drive ID found in response")
                    else:
                        error_text = await resp.text()
                        logging.error(f"[sharepoint_purge_deleted_files] Failed to get drive ID: {resp.status} - {error_text}")
                        
        except Exception as e:
            logging.error(f"[sharepoint_purge_deleted_files] Exception while getting drive ID: {e}")
            
        return None

    async def check_file_exists_in_folder(self, parent_id: Any, folder_path: str, headers: Dict[str, str], semaphore: asyncio.Semaphore, file_name: str = None) -> bool:
        """Check if a SharePoint file exists in a specific folder path."""
        if not self.site_id:
            return False
            
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    # Get drive ID first
                    drive_id = await self.get_drive_id(headers)
                    if not drive_id:
                        logging.error(f"[sharepoint_purge_deleted_files] Could not get drive ID for folder check")
                        return False
                    
                    # Build the folder URL - handle both root-relative and absolute paths
                    if folder_path.startswith("/"):
                        folder_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{folder_path}:/children"
                    else:
                        folder_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{folder_path}:/children"
                    
                    logging.debug(f"[sharepoint_purge_deleted_files] Checking folder {folder_path} for file {parent_id} (name: {file_name})")
                    logging.debug(f"[sharepoint_purge_deleted_files] Folder URL: {folder_url}")
                    
                    # Get all files in the target folder
                    async with session.get(folder_url, headers=headers) as resp:
                        if resp.status == 200:
                            folder_data = await resp.json()
                            files_in_folder = folder_data.get('value', [])
                            logging.info(f"[sharepoint_purge_deleted_files] Found {len(files_in_folder)} files in folder {folder_path}")
                            
                            # Log all files in the folder for debugging
                            for file_item in files_in_folder:
                                file_id = file_item.get('id', '')
                                folder_file_name = file_item.get('name', '')
                                logging.debug(f"[sharepoint_purge_deleted_files] Folder file: ID={file_id}, Name={folder_file_name}")
                            
                            # Check if our target file exists in this folder
                            # Primary check: Compare by filename (more reliable than file ID)
                            if file_name:
                                for file_item in files_in_folder:
                                    folder_file_name = file_item.get('name', '')
                                    if folder_file_name.lower() == file_name.lower():
                                        logging.info(f"[sharepoint_purge_deleted_files] ✅ File '{file_name}' FOUND in target folder {folder_path} (by filename)")
                                        return True
                            
                            # Fallback check: Compare by file ID
                            for file_item in files_in_folder:
                                file_id = file_item.get('id', '')
                                folder_file_name = file_item.get('name', '')
                                
                                # Compare both the full ID and just the GUID part
                                if str(file_id) == str(parent_id) or str(file_id).replace('-', '').upper() == str(parent_id).replace('-', '').upper():
                                    logging.info(f"[sharepoint_purge_deleted_files] ✅ File {parent_id} ({folder_file_name}) FOUND in target folder {folder_path} (by file ID)")
                                    return True
                            
                            # File not found
                            if file_name:
                                logging.info(f"[sharepoint_purge_deleted_files] ❌ File '{file_name}' (ID: {parent_id}) NOT found in target folder {folder_path}")
                            else:
                                logging.info(f"[sharepoint_purge_deleted_files] ❌ File {parent_id} NOT found in target folder {folder_path}")
                            logging.info(f"[sharepoint_purge_deleted_files] Available files in folder: {[f.get('name', '') for f in files_in_folder]}")
                            return False
                        elif resp.status == 404:
                            logging.warning(f"[sharepoint_purge_deleted_files] Target folder {folder_path} not found")
                            return False
                        else:
                            error_text = await resp.text()
                            logging.error(f"[sharepoint_purge_deleted_files] Error checking folder {folder_path}: {resp.status} - {error_text}")
                            return False
                            
                except Exception as e:
                    logging.error(f"[sharepoint_purge_deleted_files] Exception checking file {parent_id} in folder {folder_path}: {e}")
                    return False

    async def check_parent_id_exists(self, parent_id: Any, headers: Dict[str, str], semaphore: asyncio.Semaphore, file_name: str = None) -> bool:
        """Check if a SharePoint parent ID exists."""
        
        # If we have a target folder path, check specifically in that folder
        if self.target_folder_path:
            logging.debug(f"[sharepoint_purge_deleted_files] Checking if file {parent_id} (name: {file_name}) exists in target folder: {self.target_folder_path}")
            return await self.check_file_exists_in_folder(parent_id, self.target_folder_path, headers, semaphore, file_name)
        
        # Check if parent_id is a URL (fallback for files that couldn't be converted to proper IDs)
        if isinstance(parent_id, str) and (parent_id.startswith('http://') or parent_id.startswith('https://')):
            logging.debug(f"[sharepoint_purge_deleted_files] Parent ID is a URL, attempting to extract file ID: {parent_id}")
            # Try to extract the file ID from the URL
            file_id = await self.extract_file_id_from_url(parent_id, headers)
            if file_id:
                logging.debug(f"[sharepoint_purge_deleted_files] Successfully extracted file ID {file_id} from URL")
                parent_id = file_id  # Use the extracted file ID
            else:
                # If we can't extract a file ID, the file likely doesn't exist
                logging.debug(f"[sharepoint_purge_deleted_files] Could not extract file ID from URL - file likely doesn't exist")
                return False
        
        # Otherwise, fall back to the original method (check anywhere in SharePoint)
        logging.debug(f"[sharepoint_purge_deleted_files] No target folder specified, checking if file {parent_id} exists anywhere in SharePoint")
        
        # For GUID format IDs extracted from URLs, we need to use the drive/items endpoint
        
        try:
            # Try multiple endpoint formats to find the correct one
            check_urls = []
            
            # Method 1: Use sites/{hostname}:{server-relative-url}:/drive/items/{item-id}
            # This is the recommended approach for SharePoint sites
            if self.sharepoint_host and self.sharepoint_site is not None:
                # Extract hostname and site path from SharePoint URL
                sharepoint_host = self.sharepoint_host.replace('https://', '').replace('http://', '')
                if self.sharepoint_site:  # Non-root site
                    site_path = f"/sites/{self.sharepoint_site}" if not self.sharepoint_site.startswith('/') else self.sharepoint_site
                    check_urls.append(f"https://graph.microsoft.com/v1.0/sites/{sharepoint_host}:{site_path}:/drive/items/{parent_id}")
                else:  # Root site
                    check_urls.append(f"https://graph.microsoft.com/v1.0/sites/{sharepoint_host}:/drive/items/{parent_id}")
            
            # Method 2: Use the composite site ID directly
            if self.site_id and ',' in str(self.site_id):
                check_urls.append(f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/items/{parent_id}")
            
            # Method 3: Get drive ID first, then use drives/{drive-id}/items/{item-id}
            # This is often more reliable than using the site reference
            drive_id = await self.get_drive_id(headers)
            if drive_id:
                check_urls.append(f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}")
            
        except Exception as e:
            logging.error(f"[sharepoint_purge_deleted_files] Error constructing check URLs for {parent_id}: {e}")
            return False
        
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                # Try each URL format until one works or we exhaust all options
                for i, check_url in enumerate(check_urls, 1):
                    try:
                        logging.debug(f"[sharepoint_purge_deleted_files] Trying URL format {i} for {parent_id}: {check_url}")
                        async with session.get(check_url, headers=headers) as resp:
                            if resp.status == 200:
                                logging.info(f"[sharepoint_purge_deleted_files] ✅ SharePoint ID {parent_id} exists (method {i} succeeded).")
                                return True
                            elif resp.status == 404:
                                logging.info(f"[sharepoint_purge_deleted_files] SharePoint ID {parent_id} does not exist (method {i} - 404 Not Found).")
                                return False
                            elif resp.status == 400:
                                # Invalid request - try next URL format
                                error_text = await resp.text()
                                logging.warning(f"[sharepoint_purge_deleted_files] Method {i} failed for {parent_id}: {resp.status} - {error_text}")
                                continue
                            else:
                                error_text = await resp.text()
                                logging.warning(f"[sharepoint_purge_deleted_files] Method {i} unexpected error for {parent_id}: {resp.status} - {error_text}")
                                # For other errors, try next method
                                continue
                    except Exception as e:
                        logging.error(f"[sharepoint_purge_deleted_files] Exception while checking SharePoint ID {parent_id} (method {i}): {e}")
                        continue
                
                # If all methods failed, assume the file doesn't exist
                logging.warning(f"[sharepoint_purge_deleted_files] All check methods failed for {parent_id}, assuming it doesn't exist.")
                return False

    async def purge_deleted_files(self) -> Dict[str, Any]:
        """Main method to purge deleted SharePoint files from Azure Search index."""
        logging.info("[sharepoint_purge_deleted_files] Started SharePoint purge connector function.")
        
        result = {
            "success": False,
            "message": "",
            "documents_checked": 0,
            "documents_deleted": 0,
            "files_checked": 0,
            "files_not_found": 0,
            "errors": []
        }
        
        logging.info(f"[sharepoint_purge_deleted_files] Using index: {self.index_name}, Target folder: {self.target_folder_path}")

        if not self.connector_enabled:
            message = ("SharePoint purge connector is disabled. "
                      "Set SHAREPOINT_CONNECTOR_ENABLED to 'true' to enable the connector.")
            logging.info(f"[sharepoint_purge_deleted_files] {message}")
            result["message"] = message
            return result

        # Initialize clients and configurations        
        if not await self.initialize_clients():
            result["message"] = "Failed to initialize clients"
            result["errors"].append("Failed to initialize Key Vault or Search clients")
            return result

        # Obtain the site_id
        self.site_id = await self.get_site_id()
        if not self.site_id:
            message = "Unable to retrieve site_id. Aborting operation."
            logging.error(f"[sharepoint_purge_deleted_files] {message}")
            result["message"] = message
            result["errors"].append("Could not retrieve SharePoint site ID")
            return result

        # Obtain access token for item checks
        self.access_token = await self.get_graph_access_token()
        if not self.access_token:
            message = "Cannot proceed without access token."
            logging.error(f"[sharepoint_purge_deleted_files] {message}")
            result["message"] = message
            result["errors"].append("Could not obtain Microsoft Graph access token")
            await self.search_client.close()
            return result

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        # Retrieve all documents with SharePoint source from Azure Search
        logging.info("[sharepoint_purge_deleted_files] Retrieving documents from Azure Search index.")
        try:
            # First, get a sample of SharePoint documents to detect available fields
            logging.info("[sharepoint_purge_deleted_files] Detecting available fields in index...")
            
            # Get a sample of documents to detect SharePoint content and available fields
            logging.info("[sharepoint_purge_deleted_files] Getting sample documents to detect SharePoint content...")
            
            sample_search = await self.search_client.search_documents(
                index_name=self.index_name,
                search_text="*",
                select_fields=["*"],  # Get all fields to detect schema
                top=10  # Get more documents to increase chance of finding SharePoint docs
            )
            
            sample_docs = sample_search.get("documents", [])
            if not sample_docs:
                message = "No documents found in the index."
                logging.info(f"[sharepoint_purge_deleted_files] {message}")
                result["success"] = True
                result["message"] = message
                await self.search_client.close()
                return result
            
            # Filter for only SharePoint documents from the sample
            sharepoint_docs = [doc for doc in sample_docs if 
                             doc.get("url", "").find("sharepoint.com") != -1]
            
            if not sharepoint_docs:
                message = "No SharePoint documents found in the index. Documents found but none contain SharePoint URLs."
                logging.info(f"[sharepoint_purge_deleted_files] {message}")
                # Log what we did find for debugging
                for i, doc in enumerate(sample_docs[:3]):
                    url = doc.get("url", "")
                    source = doc.get("source", "")
                    logging.info(f"[sharepoint_purge_deleted_files] Sample doc {i+1}: url='{url[:100] if url else 'None'}...', source='{source}'")
                result["success"] = True
                result["message"] = message
                await self.search_client.close()
                return result
            
            # Analyze available fields from SharePoint documents
            available_fields = list(sharepoint_docs[0].keys())
            logging.info(f"[sharepoint_purge_deleted_files] Available fields: {available_fields}")
            
            # Determine which SharePoint ID field to use based on available fields
            sharepoint_id_field = None
            search_filter = None
            search_text = "*"
            select_fields = ["id"]
            
            # For your index, we'll use the URL field to extract SharePoint file IDs
            if "url" in available_fields:
                sharepoint_id_field = "url"
                # Use text search instead of search.ismatch to avoid searchable field requirement
                search_filter = "url ne null"
                search_text = "sharepoint.com"  # Search for sharepoint.com in all searchable fields
                select_fields.extend(["url"])
            elif "parent_id" in available_fields:
                sharepoint_id_field = "parent_id"
                search_filter = "parent_id ne null"
                search_text = "sharepoint.com"
                select_fields.extend(["parent_id"])
            elif "sharepoint_id" in available_fields:
                sharepoint_id_field = "sharepoint_id"
                search_filter = "sharepoint_id ne null"
                search_text = "sharepoint.com"
                select_fields.extend(["sharepoint_id"])
            elif "metadata_storage_path" in available_fields:
                sharepoint_id_field = "metadata_storage_path"
                search_filter = "source eq 'sharepoint' and metadata_storage_path ne null"
                select_fields.extend(["metadata_storage_path"])
            else:
                # No SharePoint ID field found, can't verify file existence
                message = "No SharePoint file ID field (parent_id, sharepoint_id, url, or metadata_storage_path) found in index schema. Cannot verify file existence."
                logging.warning(f"[sharepoint_purge_deleted_files] {message}")
                logging.warning(f"[sharepoint_purge_deleted_files] Available fields: {available_fields}")
                result["success"] = True
                result["message"] = message
                await self.search_client.close()
                return result
            
            # Add optional metadata fields if available
            if "metadata_storage_name" in available_fields:
                select_fields.append("metadata_storage_name")
            if "metadata_storage_path" in available_fields and "metadata_storage_path" not in select_fields:
                select_fields.append("metadata_storage_path")
            if "source_file" in available_fields:
                select_fields.append("source_file")
            if "filename" in available_fields:
                select_fields.append("filename")
            
            logging.info(f"[sharepoint_purge_deleted_files] Using field '{sharepoint_id_field}' for SharePoint file identification.")
            logging.info(f"[sharepoint_purge_deleted_files] Search text: {search_text}")
            logging.info(f"[sharepoint_purge_deleted_files] Search filter: {search_filter}")
            logging.info(f"[sharepoint_purge_deleted_files] Select fields: {select_fields}")
            
            # Now perform the actual search with detected fields
            # Try search with filter first, if that fails, try just the filter
            try:
                logging.info(f"[sharepoint_purge_deleted_files] Attempting search with text and filter...")
                search_results = await self.search_client.search_documents(
                    index_name=self.index_name,
                    search_text=search_text,
                    filter_str=search_filter,
                    select_fields=select_fields,
                    top=10000  # Get up to 10,000 documents for processing
                )
                logging.info(f"[sharepoint_purge_deleted_files] Search with text+filter returned {len(search_results.get('documents', []))} documents")
                
                # If we get 0 results with both search_text and filter, try just the filter
                if len(search_results.get('documents', [])) == 0:
                    logging.info(f"[sharepoint_purge_deleted_files] No results with text+filter, trying filter only...")
                    search_results = await self.search_client.search_documents(
                        index_name=self.index_name,
                        search_text="*",  # Get all documents
                        filter_str=search_filter,
                        select_fields=select_fields,
                        top=10000
                    )
                    logging.info(f"[sharepoint_purge_deleted_files] Filter-only search returned {len(search_results.get('documents', []))} documents")
                    
            except Exception as search_error:
                logging.warning(f"[sharepoint_purge_deleted_files] Search with filter failed: {search_error}")
                # Fallback to simple text search only
                logging.info(f"[sharepoint_purge_deleted_files] Falling back to text search only...")
                search_results = await self.search_client.search_documents(
                    index_name=self.index_name,
                    search_text=search_text,
                    select_fields=select_fields,
                    top=10000
                )
            logging.info(f"[sharepoint_purge_deleted_files] Search successful, found {len(search_results.get('documents', []))} SharePoint documents.")
                
        except Exception as e:
            message = f"Failed to retrieve documents from Azure Search: {e}"
            logging.error(f"[sharepoint_purge_deleted_files] {message}")
            result["message"] = message
            result["errors"].append(str(e))
            await self.search_client.close()
            return result

        documents = search_results.get("documents", [])
        result["documents_checked"] = len(documents)
        logging.info(f"[sharepoint_purge_deleted_files] Retrieved {len(documents)} SharePoint document chunks.")

        if not documents:
            message = "No SharePoint document chunks found in the index."
            logging.info(f"[sharepoint_purge_deleted_files] {message}")
            result["success"] = True
            result["message"] = message
            await self.search_client.close()
            return result

        # Map SharePoint file IDs to document IDs and file info
        sharepoint_to_doc_ids = defaultdict(list)
        sharepoint_file_info = {}  # Store filename for each file ID
        
        logging.info(f"[sharepoint_purge_deleted_files] Processing documents using field '{sharepoint_id_field}'.")
        
        for doc in documents:
            sharepoint_file_id = doc.get(sharepoint_id_field)
            doc_id = doc.get("id")
            
            if sharepoint_file_id and doc_id:
                # Get the filename from available fields
                file_name = doc.get("metadata_storage_name") or doc.get("source_file") or doc.get("filename")
                # Extract file ID based on the field type
                if sharepoint_id_field == "url":
                    # Extract file ID from SharePoint URL - handle multiple formats
                    try:
                        import re
                        import urllib.parse
                        
                        # First try to extract from sourcedoc parameter (legacy format)
                        # https://mngenvmcap623661.sharepoint.com/_layouts/15/Doc.aspx?sourcedoc=%7B8D2D1065-4B60-49B4-95F6-AB03F1F5FB75%7D&file=...
                        match = re.search(r'sourcedoc=([^&]+)', sharepoint_file_id)
                        if match:
                            encoded_id = match.group(1)
                            # URL decode the file ID
                            decoded_id = urllib.parse.unquote(encoded_id)
                            # Remove the curly braces from GUID format {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
                            sharepoint_file_id = decoded_id.strip('{}')
                            logging.debug(f"[sharepoint_purge_deleted_files] Extracted file ID from sourcedoc URL: {sharepoint_file_id}")
                        else:
                            # Try to extract from direct SharePoint file URL
                            # https://mngenvmcap623661.sharepoint.com/Shared%20Documents/ppt/somatosensory.pdf
                            file_id = await self.extract_file_id_from_url(sharepoint_file_id, headers)
                            if file_id:
                                sharepoint_file_id = file_id
                                logging.debug(f"[sharepoint_purge_deleted_files] Extracted file ID from direct URL: {sharepoint_file_id}")
                            else:
                                # File doesn't exist - this is expected for deleted files
                                # Use the URL itself as the identifier and mark it as non-existent
                                logging.debug(f"[sharepoint_purge_deleted_files] File not found for URL: {sharepoint_file_id} - will treat as deleted")
                                # Use URL as identifier, but we'll mark this as not existing during existence check
                    except Exception as e:
                        logging.warning(f"[sharepoint_purge_deleted_files] Error extracting file ID from URL: {e}")
                        continue
                elif sharepoint_id_field == "metadata_storage_path":
                    # Extract file ID from SharePoint URL pattern
                    try:
                        import re
                        # Look for patterns like /drive/items/{id} in the URL
                        match = re.search(r'/drive/items/([^/]+)', sharepoint_file_id)
                        if match:
                            sharepoint_file_id = match.group(1)
                        else:
                            logging.warning(f"[sharepoint_purge_deleted_files] Could not extract file ID from path: {sharepoint_file_id}")
                            continue
                    except Exception as e:
                        logging.warning(f"[sharepoint_purge_deleted_files] Error extracting file ID from path: {e}")
                        continue
                
                sharepoint_to_doc_ids[sharepoint_file_id].append(doc_id)
                # Store the filename for this file ID
                if file_name and sharepoint_file_id not in sharepoint_file_info:
                    sharepoint_file_info[sharepoint_file_id] = file_name

        sharepoint_file_ids = list(sharepoint_to_doc_ids.keys())
        result["files_checked"] = len(sharepoint_file_ids)
        logging.info(f"[sharepoint_purge_deleted_files] Checking existence of {len(sharepoint_file_ids)} SharePoint document(s).")

        if not sharepoint_file_ids:
            message = "No valid SharePoint file IDs found in documents."
            logging.info(f"[sharepoint_purge_deleted_files] {message}")
            result["success"] = True
            result["message"] = message
            await self.search_client.close()
            return result

        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

        # Create tasks to check if SharePoint file IDs exist
        logging.info(f"[sharepoint_purge_deleted_files] Checking existence of {len(sharepoint_file_ids)} unique SharePoint files.")
        
        existence_tasks = [
            self.check_parent_id_exists(file_id, headers, semaphore, sharepoint_file_info.get(file_id)) 
            for file_id in sharepoint_file_ids
        ]
        
        existence_results = await asyncio.gather(*existence_tasks)

        # Identify all document IDs to delete for non-existing SharePoint files
        doc_ids_to_delete = []
        
        for file_id, exists in zip(sharepoint_file_ids, existence_results):
            file_name = sharepoint_file_info.get(file_id, "Unknown")
            doc_ids_for_file = sharepoint_to_doc_ids[file_id]
            
            if not exists:
                result["files_not_found"] += 1
                doc_ids_to_delete.extend(doc_ids_for_file)

        result["documents_deleted"] = len(doc_ids_to_delete)
        logging.info(f"[sharepoint_purge_deleted_files] {len(doc_ids_to_delete)} document chunks identified for purging (from {result['files_not_found']} deleted files).")

        if doc_ids_to_delete:
            batch_size = 100
            deleted_count = 0
            
            for batch_num, i in enumerate(range(0, len(doc_ids_to_delete), batch_size), 1):
                batch = doc_ids_to_delete[i:i + batch_size]
                
                try:
                    delete_result = await self.search_client.delete_documents(
                        index_name=self.index_name,
                        key_field="id",
                        key_values=batch
                    )
                    
                    deleted_count += len(batch)
                    logging.info(f"[sharepoint_purge_deleted_files] Purged batch of {len(batch)} documents from Azure Search.")
                    
                except Exception as e:
                    error_msg = f"Failed to purge batch starting at index {i}: {e}"
                    logging.error(f"[sharepoint_purge_deleted_files] {error_msg}")
                    result["errors"].append(error_msg)
            
            result["documents_deleted"] = deleted_count
            result["success"] = True
            result["message"] = f"Successfully purged {deleted_count} orphaned document chunks from {result['files_not_found']} deleted files"
        else:
            result["success"] = True
            result["message"] = "No orphaned documents found - index is clean!"

        # Close the AISearchClient
        try:
            await self.search_client.close()
            logging.debug("[sharepoint_purge_deleted_files] Closed AISearchClient successfully.")
        except Exception as e:
            logging.error(f"[sharepoint_purge_deleted_files] Failed to close AISearchClient: {e}")

        logging.info("[sharepoint_purge_deleted_files] Completed SharePoint purge connector function.")
        return result
        logging.info("[sharepoint_purge_deleted_files] Completed SharePoint purge connector function.")
        return result

    async def preview_deleted_files(self) -> Dict[str, Any]:
        """Preview method to show what files would be deleted without actually deleting them."""
        logging.info("[sharepoint_purge_deleted_files] Started SharePoint purge preview.")
        
        result = {
            "success": False,
            "message": "",
            "documents_checked": 0,
            "files_checked": 0,
            "files_not_found": 0,
            "orphaned_files": [],
            "would_delete_count": 0,
            "errors": []
        }

        if not self.connector_enabled:
            message = ("SharePoint purge connector is disabled. "
                      "Set SHAREPOINT_CONNECTOR_ENABLED to 'true' to enable the connector.")
            logging.info(f"[sharepoint_purge_deleted_files] {message}")
            result["message"] = message
            return result

        # Initialize clients and configurations
        if not await self.initialize_clients():
            result["message"] = "Failed to initialize clients"
            result["errors"].append("Failed to initialize Key Vault or Search clients")
            return result

        # Obtain the site_id
        self.site_id = await self.get_site_id()
        if not self.site_id:
            message = "Unable to retrieve site_id. Aborting operation."
            logging.error(f"[sharepoint_purge_deleted_files] {message}")
            result["message"] = message
            result["errors"].append("Could not retrieve SharePoint site ID")
            return result

        # Obtain access token for item checks
        self.access_token = await self.get_graph_access_token()
        if not self.access_token:
            message = "Cannot proceed without access token."
            logging.error(f"[sharepoint_purge_deleted_files] {message}")
            result["message"] = message
            result["errors"].append("Could not obtain Microsoft Graph access token")
            await self.search_client.close()
            return result

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        # Retrieve all documents with SharePoint source from Azure Search
        logging.info("[sharepoint_purge_deleted_files] Retrieving documents from Azure Search index for preview.")
        try:
            # Use the same detection logic as main purge method
            logging.info("[sharepoint_purge_deleted_files] Preview: detecting SharePoint documents...")
            
            # Try different approaches to detect SharePoint documents  
            sample_search = None
            sharepoint_filters = [
                # Try text search for sharepoint.com if url is searchable
                None,  # Will use search_text instead
                # Try simple url filter if url is filterable 
                "url ne null",
                # Fallback to get all documents
                "*"
            ]
            
            sharepoint_search_texts = [
                "sharepoint.com",  # Search for sharepoint.com in all searchable fields
                "*",               # Get all documents for manual filtering
                "*"                # Get all documents for manual filtering
            ]
            
            for i, filter_attempt in enumerate(sharepoint_filters):
                try:
                    search_text = sharepoint_search_texts[i]
                    logging.info(f"[sharepoint_purge_deleted_files] Preview: trying search_text='{search_text}', filter='{filter_attempt}'")
                    sample_search = await self.search_client.search_documents(
                        index_name=self.index_name,
                        search_text=search_text,
                        filter_str=filter_attempt,
                        select_fields=["*"],
                        top=5
                    )
                    
                    sample_docs = sample_search.get("documents", [])
                    if sample_docs:
                        sharepoint_docs = [doc for doc in sample_docs if 
                                         doc.get("url", "").find("sharepoint.com") != -1]
                        
                        if sharepoint_docs:
                            logging.info(f"[sharepoint_purge_deleted_files] Preview: found {len(sharepoint_docs)} SharePoint documents")
                            sample_search = {"documents": sharepoint_docs}
                            break
                except Exception as e:
                    logging.warning(f"[sharepoint_purge_deleted_files] Preview: search failed: search_text='{sharepoint_search_texts[i]}', filter='{filter_attempt}' - {e}")
                    continue
            
            if not sample_search:
                sample_search = await self.search_client.search_documents(
                    index_name=self.index_name,
                    search_text="*",
                    select_fields=["*"],
                    top=1
                )
            
            sample_docs = sample_search.get("documents", [])
            if not sample_docs:
                message = "No documents found in the index."
                logging.info(f"[sharepoint_purge_deleted_files] Preview: {message}")
                result["success"] = True
                result["message"] = message
                await self.search_client.close()
                return result
            
            # Filter for only SharePoint documents
            sharepoint_docs = [doc for doc in sample_docs if 
                             doc.get("url", "").find("sharepoint.com") != -1]
            
            if not sharepoint_docs:
                message = "No SharePoint documents found in the index. Documents found but none contain SharePoint URLs."
                logging.info(f"[sharepoint_purge_deleted_files] Preview: {message}")
                result["success"] = True
                result["message"] = message
                await self.search_client.close()
                return result
            
            # Analyze available fields from SharePoint documents
            available_fields = list(sharepoint_docs[0].keys())
            logging.info(f"[sharepoint_purge_deleted_files] Preview: available fields: {available_fields}")
            
            # Use URL field to extract SharePoint file IDs
            sharepoint_id_field = "url"
            # Use text search instead of search.ismatch to avoid searchable field requirement
            search_filter = "url ne null"
            search_text = "sharepoint.com"  # Search for sharepoint.com in all searchable fields
            select_fields = ["id", "url"]
            
            # Add optional metadata fields if available
            if "metadata_storage_name" in available_fields:
                select_fields.append("metadata_storage_name")
            if "metadata_storage_path" in available_fields:
                select_fields.append("metadata_storage_path")
            if "source_file" in available_fields:
                select_fields.append("source_file")
            if "filename" in available_fields:
                select_fields.append("filename")
            elif "metadata_storage_path" in available_fields:
                sharepoint_id_field = "metadata_storage_path"
                search_filter = "source eq 'sharepoint' and metadata_storage_path ne null"
                select_fields.extend(["metadata_storage_path"])
            else:
                # No SharePoint ID field found, can't verify file existence
                message = "No SharePoint file ID field (parent_id, sharepoint_id, url, or metadata_storage_path) found in index schema. Cannot verify file existence."
                logging.warning(f"[sharepoint_purge_deleted_files] {message}")
                logging.warning(f"[sharepoint_purge_deleted_files] Available fields: {available_fields}")
                result["success"] = True
                result["message"] = message
                await self.search_client.close()
                return result
            
            # Add optional metadata fields if available
            if "metadata_storage_name" in available_fields:
                select_fields.append("metadata_storage_name")
            if "metadata_storage_path" in available_fields and "metadata_storage_path" not in select_fields:
                select_fields.append("metadata_storage_path")
            if "source_file" in available_fields:
                select_fields.append("source_file")
            if "filename" in available_fields:
                select_fields.append("filename")
            
            logging.info(f"[sharepoint_purge_deleted_files] Preview: using field '{sharepoint_id_field}' for SharePoint file identification.")
            logging.info(f"[sharepoint_purge_deleted_files] Preview: search_text: {search_text}")
            logging.info(f"[sharepoint_purge_deleted_files] Preview: search filter: {search_filter}")
            logging.info(f"[sharepoint_purge_deleted_files] Preview: select fields: {select_fields}")
            
            # Now perform the actual search with detected fields
            # Try search with filter first, if that fails, try just the filter
            try:
                logging.info(f"[sharepoint_purge_deleted_files] Preview: Attempting search with text and filter...")
                search_results = await self.search_client.search_documents(
                    index_name=self.index_name,
                    search_text=search_text,
                    filter_str=search_filter,
                    select_fields=select_fields,
                    top=1000  # Get up to 1000 documents for preview
                )
                logging.info(f"[sharepoint_purge_deleted_files] Preview: Search with text+filter returned {len(search_results.get('documents', []))} documents")
                
                # If we get 0 results with both search_text and filter, try just the filter
                if len(search_results.get('documents', [])) == 0:
                    logging.info(f"[sharepoint_purge_deleted_files] Preview: No results with text+filter, trying filter only...")
                    search_results = await self.search_client.search_documents(
                        index_name=self.index_name,
                        search_text="*",  # Get all documents
                        filter_str=search_filter,
                        select_fields=select_fields,
                        top=1000
                    )
                    logging.info(f"[sharepoint_purge_deleted_files] Preview: Filter-only search returned {len(search_results.get('documents', []))} documents")
                    
            except Exception as search_error:
                logging.warning(f"[sharepoint_purge_deleted_files] Preview: Search with filter failed: {search_error}")
                # Fallback to simple text search only
                logging.info(f"[sharepoint_purge_deleted_files] Preview: Falling back to text search only...")
                search_results = await self.search_client.search_documents(
                    index_name=self.index_name,
                    search_text=search_text,
                    select_fields=select_fields,
                    top=1000
                )
            logging.info(f"[sharepoint_purge_deleted_files] Preview: search successful, found {len(search_results.get('documents', []))} SharePoint documents.")
                
        except Exception as e:
            message = f"Failed to retrieve documents from Azure Search: {e}"
            logging.error(f"[sharepoint_purge_deleted_files] {message}")
            result["message"] = message
            result["errors"].append(str(e))
            await self.search_client.close()
            return result

        documents = search_results.get("documents", [])
        result["documents_checked"] = len(documents)
        logging.info(f"[sharepoint_purge_deleted_files] Retrieved {len(documents)} SharePoint document chunks for preview.")

        if not documents:
            message = "No SharePoint document chunks found in the index."
            logging.info(f"[sharepoint_purge_deleted_files] {message}")
            result["success"] = True
            result["message"] = message
            await self.search_client.close()
            return result

        # Map SharePoint file IDs to document info for preview - same logic as main purge
        sharepoint_to_doc_info = {}
        
        logging.info(f"[sharepoint_purge_deleted_files] Preview: processing documents using field '{sharepoint_id_field}'.")
        
        for doc in documents:
            sharepoint_file_id = doc.get(sharepoint_id_field)
            doc_id = doc.get("id")
            
            if sharepoint_file_id and doc_id:
                # Extract file ID and filename based on the field type
                original_file_id = sharepoint_file_id
                filename = None
                
                if sharepoint_id_field == "url":
                    # Extract file ID from SharePoint URL - handle multiple formats
                    try:
                        import re
                        import urllib.parse
                        
                        # First try to extract from sourcedoc parameter (legacy format)
                        # https://mngenvmcap623661.sharepoint.com/_layouts/15/Doc.aspx?sourcedoc=%7B8D2D1065-4B60-49B4-95F6-AB03F1F5FB75%7D&file=...
                        match = re.search(r'sourcedoc=([^&]+)', sharepoint_file_id)
                        if match:
                            encoded_id = match.group(1)
                            # URL decode the file ID
                            decoded_id = urllib.parse.unquote(encoded_id)
                            # Remove the curly braces from GUID format {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
                            sharepoint_file_id = decoded_id.strip('{}')
                            logging.debug(f"[sharepoint_purge_deleted_files] Preview: extracted file ID from sourcedoc URL: {sharepoint_file_id}")
                        else:
                            # For direct SharePoint file URLs, we'll use the full URL as identifier
                            # In preview mode, we don't make API calls to get the actual file ID
                            # https://mngenvmcap623661.sharepoint.com/Shared%20Documents/ppt/somatosensory.pdf
                            logging.debug(f"[sharepoint_purge_deleted_files] Preview: using direct URL as identifier: {sharepoint_file_id}")
                            
                        # Extract filename from URL - handle both formats
                        filename_match = re.search(r'[&?]file=([^&]+)', original_file_id)
                        if filename_match:
                            # Legacy format with file parameter
                            filename = urllib.parse.unquote(filename_match.group(1))
                            logging.debug(f"[sharepoint_purge_deleted_files] Preview: extracted filename from URL parameter: {filename}")
                        else:
                            # Direct URL format - extract filename from path
                            path_parts = original_file_id.split('/')
                            if path_parts:
                                filename = urllib.parse.unquote(path_parts[-1])
                                logging.debug(f"[sharepoint_purge_deleted_files] Preview: extracted filename from URL path: {filename}")
                    except Exception as e:
                        logging.warning(f"[sharepoint_purge_deleted_files] Error extracting file ID from URL: {e}")
                        continue
                elif sharepoint_id_field == "metadata_storage_path":
                    # Extract file ID from SharePoint URL pattern
                    try:
                        import re
                        # Look for patterns like /drive/items/{id} in the URL
                        match = re.search(r'/drive/items/([^/]+)', sharepoint_file_id)
                        if match:
                            sharepoint_file_id = match.group(1)
                        else:
                            logging.warning(f"[sharepoint_purge_deleted_files] Could not extract file ID from path: {sharepoint_file_id}")
                            continue
                    except Exception as e:
                        logging.warning(f"[sharepoint_purge_deleted_files] Error extracting file ID from path: {e}")
                        continue
                
                # Get filename from document metadata if not extracted from URL
                if not filename:
                    filename = doc.get("metadata_storage_name") or doc.get("source_file") or doc.get("filename")
                
                if sharepoint_file_id not in sharepoint_to_doc_info:
                    # Use available fields to get file information
                    file_name = filename or "Unknown"
                    file_path = doc.get("metadata_storage_path") or doc.get("url") or "Unknown"
                    
                    sharepoint_to_doc_info[sharepoint_file_id] = {
                        "file_name": file_name,
                        "file_path": file_path,
                        "filename": filename,  # Store for folder-specific checks
                        "chunk_ids": []
                    }
                sharepoint_to_doc_info[sharepoint_file_id]["chunk_ids"].append(doc_id)

        sharepoint_file_ids = list(sharepoint_to_doc_info.keys())
        result["files_checked"] = len(sharepoint_file_ids)
        logging.info(f"[sharepoint_purge_deleted_files] Checking existence of {len(sharepoint_file_ids)} SharePoint document(s) for preview.")

        if not sharepoint_file_ids:
            message = "No valid SharePoint file IDs found in documents."
            logging.info(f"[sharepoint_purge_deleted_files] {message}")
            result["success"] = True
            result["message"] = message
            await self.search_client.close()
            return result

        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

        # Create tasks to check if SharePoint file IDs exist - use folder-specific check if target_folder_path is set
        if self.target_folder_path:
            logging.info(f"[sharepoint_purge_deleted_files] Preview: using folder-specific existence checks for folder: {self.target_folder_path}")
            existence_tasks = []
            for file_id in sharepoint_file_ids:
                filename = sharepoint_to_doc_info[file_id].get("filename")
                existence_tasks.append(
                    self.check_file_exists_in_folder(file_id, self.target_folder_path, headers, semaphore, filename)
                )
        else:
            logging.info("[sharepoint_purge_deleted_files] Preview: using global existence checks (no target folder specified)")
            existence_tasks = [
                self.check_parent_id_exists(file_id, headers, semaphore) for file_id in sharepoint_file_ids
            ]
        existence_results = await asyncio.gather(*existence_tasks)

        # Identify orphaned files
        orphaned_files = []
        total_chunks_to_delete = 0
        
        for file_id, exists in zip(sharepoint_file_ids, existence_results):
            if not exists:
                file_info = sharepoint_to_doc_info[file_id]
                chunk_count = len(file_info["chunk_ids"])
                total_chunks_to_delete += chunk_count
                
                orphaned_files.append({
                    "parent_id": file_id,
                    "file_name": file_info["file_name"],
                    "file_path": file_info["file_path"],
                    "chunk_count": chunk_count
                })

        result["files_not_found"] = len(orphaned_files)
        result["would_delete_count"] = total_chunks_to_delete
        result["orphaned_files"] = orphaned_files
        result["success"] = True
        
        if orphaned_files:
            result["message"] = f"Found {len(orphaned_files)} orphaned files that would be purged ({total_chunks_to_delete} document chunks)"
        else:
            result["message"] = "No orphaned files found - index is clean!"

        # Close the AISearchClient
        try:
            await self.search_client.close()
            logging.debug("[sharepoint_purge_deleted_files] Closed AISearchClient successfully.")
        except Exception as e:
            logging.error(f"[sharepoint_purge_deleted_files] Failed to close AISearchClient: {e}")

        logging.info("[sharepoint_purge_deleted_files] Completed SharePoint purge preview.")
        return result

    async def run(self) -> Dict[str, Any]:
        """Run the purge process."""
        return await self.purge_deleted_files()

    async def extract_file_id_from_url(self, sharepoint_url: str, headers: Dict[str, str]) -> Optional[str]:
        """
        Extract file ID from a direct SharePoint URL by converting it to Graph API call.
        Handles URLs like: https://mngenvmcap623661.sharepoint.com/Shared%20Documents/ppt/somatosensory.pdf
        """
        try:
            import urllib.parse as urlparse
            
            logging.debug(f"[sharepoint_purge_deleted_files] Starting file ID extraction for URL: {sharepoint_url}")
            
            # Parse the URL to extract the path
            parsed_url = urlparse.urlparse(sharepoint_url)
            url_path = urlparse.unquote(parsed_url.path)
            
            logging.debug(f"[sharepoint_purge_deleted_files] Parsed URL path: {url_path}")
            
            # Remove leading slash and extract the relative path
            if url_path.startswith('/'):
                url_path = url_path[1:]
            
            # For SharePoint URLs, the path typically starts with "Shared Documents" or similar
            # Convert this to the Graph API format: /drives/{drive-id}/root:/{path}
            
            # Get drive ID first
            drive_id = await self.get_drive_id(headers)
            if not drive_id:
                logging.warning(f"[sharepoint_purge_deleted_files] Could not get drive ID for URL: {sharepoint_url}")
                return None
            
            logging.debug(f"[sharepoint_purge_deleted_files] Using drive ID: {drive_id}")
            
            # Construct the Graph API URL to get file info by path
            # Try multiple encoding strategies as SharePoint URLs can be tricky
            strategies = [
                # Strategy 1: Quote the path with safe='/' (preserve path separators)
                urlparse.quote(url_path, safe='/'),
                # Strategy 2: Quote everything including slashes
                urlparse.quote(url_path, safe=''),
                # Strategy 3: Use the path as-is (in case it's already properly encoded)
                url_path,
                # Strategy 4: Handle common SharePoint folder names specially
                url_path.replace('Shared Documents', 'Shared%20Documents') if 'Shared Documents' in url_path else url_path
            ]
            
            # Remove duplicates while preserving order
            unique_strategies = []
            seen = set()
            for strategy in strategies:
                if strategy not in seen:
                    seen.add(strategy)
                    unique_strategies.append(strategy)
            
            # Try each encoding strategy
            for i, encoded_path in enumerate(unique_strategies, 1):
                try:
                    graph_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}"
                    
                    logging.debug(f"[sharepoint_purge_deleted_files] Strategy {i} - Encoded path: {encoded_path}")
                    logging.debug(f"[sharepoint_purge_deleted_files] Strategy {i} - Graph API URL: {graph_url}")
                    
                    # Make the Graph API call to get file information
                    async with aiohttp.ClientSession() as session:
                        async with session.get(graph_url, headers=headers) as response:
                            response_text = await response.text()
                            
                            if response.status == 200:
                                try:
                                    file_info = await response.json()
                                    file_id = file_info.get('id')
                                    if file_id:
                                        logging.info(f"[sharepoint_purge_deleted_files] ✅ Successfully extracted file ID from URL (strategy {i}): {file_id}")
                                        return file_id
                                    else:
                                        logging.debug(f"[sharepoint_purge_deleted_files] No file ID found in response (strategy {i})")
                                        continue
                                except Exception as json_error:
                                    logging.debug(f"[sharepoint_purge_deleted_files] Failed to parse JSON response (strategy {i}): {json_error}")
                                    continue
                            elif response.status == 404:
                                # File not found - this is expected for deleted files
                                logging.debug(f"[sharepoint_purge_deleted_files] File not found (404) with strategy {i} - this is expected for deleted files")
                                return None
                            else:
                                # Log debug info but continue to next strategy
                                logging.debug(f"[sharepoint_purge_deleted_files] Strategy {i} failed with {response.status}: {response_text}")
                                continue
                                
                except Exception as strategy_error:
                    logging.debug(f"[sharepoint_purge_deleted_files] Strategy {i} exception: {strategy_error}")
                    continue
            
            # If all strategies failed, return None silently (file likely doesn't exist)
            logging.debug(f"[sharepoint_purge_deleted_files] All file ID extraction strategies failed for URL: {sharepoint_url} - file likely deleted")
            return None
                        
        except Exception as e:
            logging.warning(f"[sharepoint_purge_deleted_files] Could not extract file ID from URL: {sharepoint_url} - {str(e)}")
            return None
