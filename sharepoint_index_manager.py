"""
SharePoint Index Manager
Handles the SharePoint folder tree view and indexing operations
"""

import streamlit as st
import requests
import os
import base64
from typing import Dict, List, Optional, Any, Tuple
import logging
from connectors.sharepoint.sharepoint_data_reader import SharePointDataReader


class SharePointIndexManager:
    """Manages SharePoint folder tree view and indexing operations"""
    
    def __init__(self):
        self.sharepoint_reader = SharePointDataReader()
        self.cached_folders = {}
        self.cache_timestamps = {}
        self.cache_timeout = 300  # 5 minutes cache timeout
        self.selected_folders = []
    
    def get_sharepoint_auth_status(self) -> Dict[str, Any]:
        """Check SharePoint authentication status"""
        try:
            self.sharepoint_reader.load_environment_variables_from_env_file()
            
            if not self.sharepoint_reader.tenant_id or not self.sharepoint_reader.client_id:
                return {
                    'authenticated': False,
                    'error': 'Missing tenant_id or client_id in environment variables'
                }
            
            # Try to authenticate
            if not self.sharepoint_reader.access_token:
                token = self.sharepoint_reader._msgraph_auth()
                if not token:
                    return {
                        'authenticated': False,
                        'error': 'Failed to authenticate with SharePoint'
                    }
            
            return {
                'authenticated': True,
                'tenant_id': self.sharepoint_reader.tenant_id,
                'client_id': self.sharepoint_reader.client_id
            }
        except Exception as e:
            return {
                'authenticated': False,
                'error': f'Authentication error: {str(e)}'
            }
    
    def get_sharepoint_sites(self, site_domain: str) -> List[Dict[str, Any]]:
        """Get available SharePoint sites"""
        try:
            # Ensure authentication is initialized
            self.sharepoint_reader.load_environment_variables_from_env_file()
            if not self.sharepoint_reader.access_token:
                auth_token = self.sharepoint_reader._msgraph_auth()
                if not auth_token:
                    logging.error("Failed to authenticate with SharePoint")
                    return []
            
            headers = {
                'Authorization': f'Bearer {self.sharepoint_reader.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get sites
            url = f"{self.sharepoint_reader.graph_uri}/v1.0/sites/{site_domain}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                site_data = response.json()
                return [{
                    'id': site_data.get('id', ''),
                    'name': site_data.get('displayName', site_domain),
                    'webUrl': site_data.get('webUrl', ''),
                    'description': site_data.get('description', '')
                }]
            else:
                logging.error(f"Failed to get sites: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logging.error(f"Error getting SharePoint sites: {e}")
            return []
    
    def get_sharepoint_drives(self, site_domain: str, site_name: str) -> List[Dict[str, Any]]:
        """Get available drives/libraries for a site"""
        try:
            # Ensure authentication is initialized
            self.sharepoint_reader.load_environment_variables_from_env_file()
            if not self.sharepoint_reader.access_token:
                auth_token = self.sharepoint_reader._msgraph_auth()
                if not auth_token:
                    logging.error("Failed to authenticate with SharePoint")
                    return []
            
            site_id, _ = self.sharepoint_reader._get_site_and_drive_ids(site_domain, site_name)
            if not site_id:
                return []
            
            headers = {
                'Authorization': f'Bearer {self.sharepoint_reader.access_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.sharepoint_reader.graph_uri}/v1.0/sites/{site_id}/drives"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                drives_data = response.json()
                drives = []
                for drive in drives_data.get('value', []):
                    drives.append({
                        'id': drive.get('id', ''),
                        'name': drive.get('name', ''),
                        'description': drive.get('description', ''),
                        'driveType': drive.get('driveType', ''),
                        'webUrl': drive.get('webUrl', '')
                    })
                return drives
            else:
                logging.error(f"Failed to get drives: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logging.error(f"Error getting SharePoint drives: {e}")
            return []
    
    def get_folder_tree(self, site_domain: str, site_name: str, drive_name: str, parent_path: str = "/", max_depth: int = 2) -> List[Dict[str, Any]]:
        """Get folder tree structure with depth limit and optimized loading"""
        import time
        
        cache_key = f"{site_domain}_{site_name}_{drive_name}_{parent_path}_depth{max_depth}"
        current_time = time.time()
        
        # Check if cache is valid (not expired)
        if (cache_key in self.cached_folders and 
            cache_key in self.cache_timestamps and
            current_time - self.cache_timestamps[cache_key] < self.cache_timeout):
            logging.info(f"Using cached folder tree for {parent_path}")
            return self.cached_folders[cache_key]

        try:
            # Ensure authentication is initialized
            self.sharepoint_reader.load_environment_variables_from_env_file()
            if not self.sharepoint_reader.access_token:
                auth_token = self.sharepoint_reader._msgraph_auth()
                if not auth_token:
                    logging.error("Failed to authenticate with SharePoint")
                    return []

            site_id, drive_id = self.sharepoint_reader._get_site_and_drive_ids(site_domain, site_name, drive_name)
            if not site_id or not drive_id:
                return []

            headers = {
                'Authorization': f'Bearer {self.sharepoint_reader.access_token}',
                'Content-Type': 'application/json'
            }

            # Get folder contents with pagination support
            if parent_path == "/" or parent_path == "":
                url = f"{self.sharepoint_reader.graph_uri}/v1.0/sites/{site_id}/drives/{drive_id}/root/children"
            else:
                encoded_path = requests.utils.quote(parent_path, safe='')
                url = f"{self.sharepoint_reader.graph_uri}/v1.0/sites/{site_id}/drives/{drive_id}/root:/{encoded_path}:/children"

            # Add query parameters for MAXIMUM performance - folders only, minimal data
            url += "?$filter=folder ne null&$select=id,name&$top=50&$orderby=name"

            logging.info(f"Fetching folder tree from: {url}")
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                items_data = response.json()
                folders = []

                for item in items_data.get('value', []):
                    if 'folder' in item or not item.get('file'):  # Only folders, no files
                        folder_path = f"{parent_path.rstrip('/')}/{item['name']}" if parent_path != "/" else f"/{item['name']}"
                        
                        # Ultra-fast folder info - no expensive calculations
                        folder_info = {
                            'id': item.get('id', ''),
                            'name': item['name'],
                            'path': folder_path,
                            'webUrl': '',  # Skip to save bandwidth
                            'childCount': 0,  # Never calculate - performance killer
                            'parentPath': parent_path,
                            'hasChildren': True  # Always assume has children for speed
                        }
                        folders.append(folder_info)

                # Sort folders by name for consistent display
                folders.sort(key=lambda x: x['name'].lower())

                # Cache the results with timestamp
                self.cached_folders[cache_key] = folders
                self.cache_timestamps[cache_key] = current_time
                logging.info(f"Cached {len(folders)} folders for {parent_path}")
                return folders
            else:
                logging.error(f"Failed to get folder tree: {response.status_code} - {response.text}")
                return []

        except requests.Timeout:
            logging.error(f"Timeout getting folder tree for {parent_path}")
            return []
        except Exception as e:
            logging.error(f"Error getting folder tree: {e}")
            return []
    
    def render_folder_tree_optimized(self, site_domain: str, site_name: str, drive_name: str, 
                                    selected_folders: List[str], max_initial_depth: int = 1) -> List[str]:
        """Render optimized folder tree with lazy loading and better performance"""
        
        # Initialize session state for expansion tracking
        if "sp_expanded_folders" not in st.session_state:
            st.session_state.sp_expanded_folders = set()
        
        updated_selected = []
        
        def render_folder_level(parent_path: str, level: int = 0):
            """Recursively render folder levels with performance optimizations"""
            
            # Limit initial depth to reduce load time
            if level >= max_initial_depth and parent_path != "/":
                # Only load deeper levels if explicitly expanded
                expand_key = f"{site_domain}_{site_name}_{drive_name}_{parent_path}"
                if expand_key not in st.session_state.sp_expanded_folders:
                    return
            
            # Get folders for current level with caching
            folders = self.get_folder_tree(site_domain, site_name, drive_name, parent_path)
            if not folders:
                if level == 0:
                    st.info("No folders found or unable to access SharePoint")
                return

            # Use container to batch UI updates
            with st.container():
                for folder in folders:
                    folder_key = f"{site_domain}|{site_name}|{drive_name}|{folder['path']}"
                    is_selected = folder_key in selected_folders
                    expand_key = f"{site_domain}_{site_name}_{drive_name}_{folder['path']}"
                    
                    # Create columns for layout
                    col1, col2, col3 = st.columns([0.08, 0.08, 0.84])
                    
                    # Selection checkbox
                    with col1:
                        checkbox_key = f"folder_select_{folder['id']}_{level}"
                        checkbox_label = "Select folder"
                        
                        if st.checkbox(checkbox_label, value=is_selected, key=checkbox_key, label_visibility="collapsed"):
                            if folder_key not in updated_selected:
                                updated_selected.append(folder_key)
                        else:
                            if folder_key in updated_selected:
                                updated_selected.remove(folder_key)
                    
                    # Expand/collapse button (only if has children)
                    with col2:
                        if folder['hasChildren']:
                            is_expanded = expand_key in st.session_state.sp_expanded_folders
                            expand_symbol = "➖" if is_expanded else "➕"
                            
                            if st.button(expand_symbol, key=f"exp_{folder['id']}_{level}", help="Click to expand/collapse"):
                                if is_expanded:
                                    st.session_state.sp_expanded_folders.discard(expand_key)
                                else:
                                    st.session_state.sp_expanded_folders.add(expand_key)
                                st.rerun()
                        else:
                            st.write("📄")  # File/empty folder icon
                    
                    # Folder name column with optimized display
                    with col3:
                        indent = "　" * level
                        folder_display = f"{indent}{folder['name']}"
                        
                        # Only show file count for selected folders to improve performance
                        if is_selected and folder['childCount'] > 0:
                            folder_display += f" ({folder['childCount']} items)"
                        elif folder['hasChildren'] and not is_selected:
                            folder_display += " 📁"  # Just show folder icon for non-selected folders
                        
                        st.write(folder_display)
                    
                    # Render subfolders if expanded (lazy loading)
                    if folder['hasChildren'] and expand_key in st.session_state.sp_expanded_folders:
                        render_folder_level(folder['path'], level + 1)
        
        # Start rendering from root with performance message
        if max_initial_depth <= 1:
            st.info("📁 Folder tree loaded with performance optimization. Expand folders to see subfolders.")
        
        with st.container():
            render_folder_level("/", 0)
        
        return updated_selected
        
        # Initialize session state for expanded folders
        if "sp_expanded_folders" not in st.session_state:
            st.session_state.sp_expanded_folders = set()
        
        updated_selected = selected_folders.copy()
        
        def render_folder_level(parent_path="/", level=0):
            """Recursively render folder levels with lazy loading"""
            if level > 3:  # Limit depth to prevent infinite recursion
                return
                
            folders = self.get_folder_tree(site_domain, site_name, drive_name, parent_path)
            
            if not folders:
                if level == 0:
                    st.info("No folders found or unable to access SharePoint")
                return
            
            for folder in folders:
                folder_key = f"{site_domain}|{site_name}|{drive_name}|{folder['path']}"
                expand_key = f"expand_{folder['id']}"
                
                # Create container for this folder
                folder_container = st.container()
                
                with folder_container:
                    # Create columns for checkbox, expand button, and folder name
                    if folder['hasChildren']:
                        col1, col2, col3 = st.columns([0.08, 0.08, 0.84])
                    else:
                        col1, col2, col3 = st.columns([0.08, 0.08, 0.84])
                    
                    # Checkbox column
                    with col1:
                        is_selected = folder_key in selected_folders
                        checkbox_key = f"cb_{folder['id']}_{level}_{parent_path}"
                        checkbox_label = f"Select folder {folder['name']}"
                        if st.checkbox(checkbox_label, value=is_selected, key=checkbox_key, label_visibility="collapsed"):
                            if folder_key not in updated_selected:
                                updated_selected.append(folder_key)
                        else:
                            if folder_key in updated_selected:
                                updated_selected.remove(folder_key)
                    
                    # Expand/collapse button column (only if has children)
                    with col2:
                        if folder['hasChildren']:
                            is_expanded = expand_key in st.session_state.sp_expanded_folders
                            expand_symbol = "📂" if is_expanded else "📁"
                            if st.button(expand_symbol, key=f"exp_{folder['id']}_{level}", help="Click to expand/collapse"):
                                if is_expanded:
                                    st.session_state.sp_expanded_folders.discard(expand_key)
                                else:
                                    st.session_state.sp_expanded_folders.add(expand_key)
                                st.rerun()
                        else:
                            st.write("�")  # File/empty folder icon
                    
                    # Folder name column
                    with col3:
                        indent = "　" * level
                        folder_display = f"{indent}{folder['name']}"
                        
                        # Only show file count for selected folders to improve performance
                        folder_key = f"{site_domain}|{site_name}|{drive_name}|{folder['path']}"
                        if folder_key in selected_folders and folder['childCount'] > 0:
                            folder_display += f" ({folder['childCount']} items)"
                        elif folder['hasChildren'] and folder_key not in selected_folders:
                            folder_display += " 📁"  # Just show folder icon for non-selected folders
                        
                        st.write(folder_display)
                
                # Render subfolders if expanded
                if folder['hasChildren'] and expand_key in st.session_state.sp_expanded_folders:
                    render_folder_level(folder['path'], level + 1)
        
        # Start rendering from root
        with st.container():
            render_folder_level("/", 0)
        
        return updated_selected

    def render_folder_tree(self, site_domain: str, site_name: str, drive_name: str, 
                          selected_folders: List[str], parent_path: str = "/", 
                          level: int = 0) -> List[str]:
        """Legacy render folder tree method - kept for compatibility"""
        return self.render_folder_tree_optimized(site_domain, site_name, drive_name, selected_folders)
    
    def get_selected_folder_info(self, selected_folders: List[str]) -> List[Dict[str, Any]]:
        """Parse selected folder keys and return structured info"""
        folder_info = []
        
        for folder_key in selected_folders:
            try:
                parts = folder_key.split('|')
                if len(parts) == 4:
                    folder_info.append({
                        'site_domain': parts[0],
                        'site_name': parts[1],
                        'drive_name': parts[2],
                        'folder_path': parts[3],
                        'display_name': f"{parts[0]}/{parts[1]}/{parts[2]}{parts[3]}"
                    })
            except Exception as e:
                logging.error(f"Error parsing folder key {folder_key}: {e}")
        
        return folder_info
    
    def index_selected_folders(self, selected_folders: List[str], index_name: str, 
                             file_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Index all files from selected folders"""
        folder_info = self.get_selected_folder_info(selected_folders)
        
        if not folder_info:
            return {
                'success': False,
                'error': 'No valid folders selected',
                'processed_files': [],
                'skipped_files': [],
                'total_chunks': 0
            }
        
        # Ensure SharePoint authentication is initialized
        try:
            self.sharepoint_reader.load_environment_variables_from_env_file()
            if not self.sharepoint_reader.access_token:
                auth_token = self.sharepoint_reader._msgraph_auth()
                if not auth_token:
                    return {
                        'success': False,
                        'error': 'Failed to authenticate with SharePoint. Please check your credentials.',
                        'processed_files': [],
                        'skipped_files': [],
                        'total_chunks': 0
                    }
        except Exception as e:
            return {
                'success': False,
                'error': f'SharePoint authentication failed: {str(e)}',
                'processed_files': [],
                'skipped_files': [],
                'total_chunks': 0
            }
        
        total_processed = 0
        total_chunks = 0
        all_processed_files = []
        all_skipped_files = []
        errors = []
        
        for folder in folder_info:
            try:
                # Use existing SharePoint reader which already handles authentication and file retrieval
                files = self.sharepoint_reader.retrieve_sharepoint_files_content(
                    site_domain=folder['site_domain'],
                    site_name=folder['site_name'],
                    folder_path=folder['folder_path'],
                    file_formats=file_types,
                    drive_name=folder['drive_name']
                )
                
                if files:
                    logging.info(f"Retrieved {len(files)} files from folder {folder['display_name']}")
                    # Process files using existing logic
                    folder_result = self._process_folder_files(files, folder, index_name)
                    
                    total_processed += folder_result['processed_count']
                    total_chunks += folder_result['total_chunks']
                    all_processed_files.extend(folder_result['processed_files'])
                    all_skipped_files.extend(folder_result['skipped_files'])
                else:
                    logging.warning(f"No files found in folder {folder['display_name']}")
                    all_skipped_files.append({
                        'name': folder['display_name'],
                        'reason': 'No files found in folder'
                    })
                    
            except Exception as e:
                error_msg = f"Failed to process folder {folder['display_name']}: {str(e)}"
                errors.append(error_msg)
                logging.error(error_msg)
        
        return {
            'success': len(errors) == 0,
            'errors': errors,
            'processed_files': all_processed_files,
            'skipped_files': all_skipped_files,
            'total_processed': total_processed,
            'total_chunks': total_chunks,
            'folders_processed': len(folder_info)
        }
    
    def _process_folder_files(self, files: List[Dict], folder_info: Dict, index_name: str) -> Dict[str, Any]:
        """Process files from a specific folder using existing chunking logic"""
        processed_files = []
        skipped_files = []
        total_chunks = 0
        
        try:
            # Import here to avoid circular imports
            import os
            import io
            from azure.search.documents import SearchIndexingBufferedSender
            from azure.core.credentials import AzureKeyCredential
            from azure.identity import DefaultAzureCredential
            
            # Get environment variables
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
            search_key = os.getenv("AZURE_SEARCH_KEY")
            embed_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
            
            if not search_endpoint:
                raise Exception("AZURE_SEARCH_ENDPOINT not configured")
            
            # Create credential
            if search_key:
                credential = AzureKeyCredential(search_key)
            else:
                credential = DefaultAzureCredential()
            
            # Create sender
            failed_ids = []
            def _on_error(action):
                try:
                    if hasattr(action, 'id'):
                        failed_ids.append(action.id)
                    elif hasattr(action, 'document') and hasattr(action.document, 'get'):
                        failed_ids.append(action.document.get("id", "?"))
                    else:
                        failed_ids.append("?")
                except Exception as exc:
                    logging.error("⚠️  SharePoint on_error callback failed: %s", exc)
                    failed_ids.append("?")
            
            sender = SearchIndexingBufferedSender(
                endpoint=search_endpoint,
                index_name=index_name,
                credential=credential,
                batch_size=100,
                auto_flush_interval=5,
                on_error=_on_error,
            )
            
            # Try to import the chunking function from main app
            try:
                # This will work if called from the main app context
                from __main__ import _chunk_to_docs
                oai_client = None  # Will be created below if needed
            except ImportError:
                _chunk_to_docs = None
                oai_client = None
            
            # Create OpenAI client if not available
            if oai_client is None:
                try:
                    from openai import AzureOpenAI
                    oai_client = AzureOpenAI(
                        api_key=os.getenv("AZURE_OPENAI_KEY"),
                        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
                    )
                except Exception as e:
                    logging.error(f"[index_files] Failed to create OpenAI client: {e}")
                    return "Failed to create OpenAI client"
            
            # If we don't have _chunk_to_docs from main app, create a basic fallback
            if _chunk_to_docs is None:
                def _chunk_to_docs(fname, file_bytes, file_url, client, embed_deployment):
                    """Basic fallback chunking function"""
                    import hashlib
                    # Simple chunking - split text into 1000 char chunks
                    if isinstance(file_bytes, bytes):
                        text = file_bytes.decode('utf-8', errors='ignore')
                    else:
                        text = str(file_bytes)
                    
                    chunks = []
                    chunk_size = 1000
                    for i in range(0, len(text), chunk_size):
                        chunk_text = text[i:i+chunk_size]
                        if chunk_text.strip():
                            # Generate basic embedding
                            try:
                                response = client.embeddings.create(
                                    input=chunk_text,
                                    model=embed_deployment
                                )
                                vector = response.data[0].embedding
                            except:
                                vector = [0.0] * 3072
                            
                            doc = {
                                "id": hashlib.md5(f"{fname}_{i}".encode()).hexdigest(),
                                "page_chunk": f"[{fname}] {chunk_text}",
                                "page_embedding_text_3_large": vector,
                                "content": chunk_text,
                                "page_number": (i // chunk_size) + 1,
                                "source_file": fname,
                                "url": file_url,
                                "extraction_method": "basic_chunker",
                                "filename": fname,
                            }
                            chunks.append(doc)
                    return chunks
            
            # Process files
            for file in files:
                try:
                    file_name = file.get('name', 'Unknown')
                    file_bytes = file.get('content')
                    file_url = file.get('source') or file.get('webUrl')
                    
                    if not file_bytes:
                        skipped_files.append({
                            'name': file_name,
                            'reason': 'No content available',
                            'folder': folder_info['display_name']
                        })
                        continue
                    
                    if not file_name:
                        skipped_files.append({
                            'name': 'Unknown file',
                            'reason': 'No filename available',
                            'folder': folder_info['display_name']
                        })
                        continue
                    
                    # Ensure file_bytes is bytes type
                    if isinstance(file_bytes, str):
                        try:
                            # Try to decode as base64 first
                            file_bytes = base64.b64decode(file_bytes)
                        except Exception:
                            # If not base64, encode as utf-8
                            file_bytes = file_bytes.encode('utf-8')
                    
                    logging.info(f"Processing file {file_name} ({len(file_bytes)} bytes)")
                    
                    # Use the chunking function
                    docs = _chunk_to_docs(
                        file_name,
                        file_bytes,
                        file_url,
                        oai_client,
                        embed_deploy,
                    )
                    
                    if docs and len(docs) > 0:
                        processed_files.append({
                            'name': file_name,
                            'chunks': len(docs),
                            'method': docs[0].get("extraction_method", "unknown") if docs else "unknown",
                            'multimodal': any(doc.get("isMultimodal", False) for doc in docs),
                            'folder': folder_info['display_name']
                        })
                        
                        # Upload to search index
                        sender.upload_documents(documents=docs)
                        total_chunks += len(docs)
                        logging.info(f"Successfully processed {file_name}: {len(docs)} chunks")
                    else:
                        skipped_files.append({
                            'name': file_name,
                            'reason': 'Processing failed - no chunks created',
                            'folder': folder_info['display_name']
                        })
                        logging.warning(f"No chunks created for file {file_name}")
                        
                except Exception as e:
                    error_msg = f"Processing error: {str(e)}"
                    logging.error(f"Error processing file {file.get('name', 'Unknown')}: {error_msg}")
                    skipped_files.append({
                        'name': file.get('name', 'Unknown'),
                        'reason': error_msg,
                        'folder': folder_info['display_name']
                    })
            
            # Close sender to flush remaining documents
            sender.close()
            
        except Exception as e:
            logging.error(f"Error in _process_folder_files: {e}")
            raise
        
        return {
            'processed_count': len(processed_files),
            'total_chunks': total_chunks,
            'processed_files': processed_files,
            'skipped_files': skipped_files
        }
    
    def clear_cache(self):
        """Clear all cached data to force refresh"""
        self.cached_folders.clear()
        
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for performance monitoring"""
        return {
            "cached_folders": len(self.cached_folders)
        }
    
    def preload_folder_structure(self, site_domain: str, site_name: str, drive_name: str, max_depth: int = 2):
        """Preload folder structure in background for better performance"""
        try:
            # Start with root folders
            root_folders = self.get_folder_tree(site_domain, site_name, drive_name, "/", max_depth)
            
            # Preload first level subfolders for better UX
            for folder in root_folders[:10]:  # Limit to first 10 folders to avoid overload
                if folder['hasChildren']:
                    self.get_folder_tree(site_domain, site_name, drive_name, folder['path'], max_depth - 1)
                    
        except Exception as e:
            logging.error(f"Error preloading folder structure: {e}")
    
    def get_files_from_folder(self, site_domain: str, site_name: str, drive_name: str, folder_path: str) -> List[Dict[str, Any]]:
        """Get files from a specific folder for indexing using the existing SharePoint reader"""
        try:
            # Use the existing SharePoint reader which has proven to work
            files = self.sharepoint_reader.retrieve_sharepoint_files_content(
                site_domain=site_domain,
                site_name=site_name,
                folder_path=folder_path,
                drive_name=drive_name,
                file_formats=None  # Get all files
            )
            
            if files:
                logging.info(f"Retrieved {len(files)} files from folder {folder_path}")
                return files
            else:
                logging.warning(f"No files found in folder {folder_path}")
                return []
                
        except Exception as e:
            logging.error(f"Error getting files from folder {folder_path}: {e}")
            return []
    
    def index_files(self, files: List[Dict[str, Any]], index_name: Optional[str] = None) -> Dict[str, Any]:
        """Index a list of files directly (used by scheduler for individual file processing)"""
        if not files:
            return {
                'success': False,
                'message': 'No files provided for indexing',
                'total_chunks': 0,
                'processing_results': []
            }
        
        # Use a default index name if not provided
        if not index_name:
            # Try to get from session state or environment
            import streamlit as st
            import os
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'sp_target_index'):
                index_name = st.session_state.sp_target_index
            elif hasattr(st, 'session_state') and hasattr(st.session_state, 'selected_index'):
                index_name = st.session_state.selected_index
            else:
                index_name = os.getenv('INDEX_NAME', 'default-index')
        
        try:
            # Import required modules for indexing
            import os
            import base64
            from azure.search.documents import SearchIndexingBufferedSender
            from azure.core.credentials import AzureKeyCredential
            from azure.identity import DefaultAzureCredential
            
            # Get environment variables
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
            search_key = os.getenv("AZURE_SEARCH_KEY")
            embed_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
            
            if not search_endpoint:
                return {
                    'success': False,
                    'message': 'AZURE_SEARCH_ENDPOINT not configured',
                    'total_chunks': 0,
                    'processing_results': []
                }
            
            # Create credential
            if search_key:
                credential = AzureKeyCredential(search_key)
            else:
                credential = DefaultAzureCredential()
            
            # Create sender
            failed_ids = []
            def _on_error(action):
                try:
                    if hasattr(action, 'id'):
                        failed_ids.append(action.id)
                    elif hasattr(action, 'document') and hasattr(action.document, 'get'):
                        failed_ids.append(action.document.get("id", "?"))
                    else:
                        failed_ids.append("?")
                except Exception as exc:
                    logging.error("⚠️  SharePoint index_files on_error callback failed: %s", exc)
                    failed_ids.append("?")
            
            sender = SearchIndexingBufferedSender(
                endpoint=search_endpoint,
                index_name=index_name,
                credential=credential,
                batch_size=100,
                auto_flush_interval=5,
                on_error=_on_error,
            )
            
            # Try to get chunking function from main app (consistent with Manage Index tab)
            try:
                # Try to import from main app context
                from __main__ import _chunk_to_docs
                oai_client = None  # Will be created below if needed
                logging.info(f"[index_files] Using main app's _chunk_to_docs function")
            except ImportError:
                # Fallback: import the function directly from the main module
                try:
                    import sys
                    import importlib.util
                    
                    # Get the path to the main agentic-rag-demo.py file
                    main_module_path = os.path.join(os.path.dirname(__file__), 'agentic-rag-demo.py')
                    if os.path.exists(main_module_path):
                        spec = importlib.util.spec_from_file_location("agentic_rag_demo", main_module_path)
                        main_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(main_module)
                        
                        _chunk_to_docs = main_module._chunk_to_docs
                        oai_client = None  # Don't try to import this, create separately
                        logging.info(f"[index_files] Imported _chunk_to_docs from main module")
                    else:
                        raise ImportError("Main module not found")
                        
                except Exception as e:
                    logging.warning(f"[index_files] Could not import main app functions: {e}")
                    _chunk_to_docs = None
                    oai_client = None
                    
            # Create OpenAI client if not available
            if oai_client is None:
                try:
                    from openai import AzureOpenAI
                    
                    oai_client = AzureOpenAI(
                        api_key=os.getenv("AZURE_OPENAI_KEY"),
                        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
                    )
                except Exception as e:
                    logging.error(f"[index_files] Failed to create OpenAI client: {e}")
                    return "Failed to create OpenAI client"
            
            # If we don't have _chunk_to_docs from main app, create a simplified version
            if _chunk_to_docs is None:
                def _chunk_to_docs(fname, file_bytes, file_url, client, embed_deployment):
                    """Simplified chunking function that creates full schema documents"""
                    import hashlib
                    import time
                    from chunking.chunker_factory import ChunkerFactory
                    
                    # Create data structure expected by ChunkerFactory
                    file_data = {
                        "fileName": fname,
                        "documentBytes": base64.b64encode(file_bytes).decode("utf-8"),
                        "documentUrl": file_url,
                        "documentContentType": "",
                    }
                    
                    # Create chunker factory instance and get appropriate chunker
                    factory = ChunkerFactory()
                    chunker = factory.get_chunker(file_data)
                    
                    # Handle base64 decoding for chunkers that need actual bytes
                    if hasattr(chunker, 'document_bytes') and isinstance(file_data["documentBytes"], str):
                        try:
                            decoded_bytes = base64.b64decode(file_data["documentBytes"])
                            chunker.document_bytes = decoded_bytes
                            logging.info(f"[index_files] Decoded base64 bytes for {fname}: {len(decoded_bytes)} bytes")
                        except Exception as e:
                            logging.error(f"[index_files] Failed to decode base64 for {fname}: {e}")
                            raise
                    
                    # Process the file using get_chunks() method
                    chunks = chunker.get_chunks()
                    
                    # Convert to document format that matches index schema
                    docs = []
                    ext = os.path.splitext(fname)[-1].lower()
                    
                    # Determine extraction method and document type
                    extraction_method = {
                        '.pdf': 'document_intelligence',
                        '.docx': 'document_intelligence',
                        '.pptx': 'document_intelligence',
                        '.xlsx': 'spreadsheet_chunker',
                        '.xls': 'spreadsheet_chunker',
                    }.get(ext, 'langchain_chunker')
                    
                    document_type = {
                        '.pdf': 'PDF Document',
                        '.docx': 'Word Document', 
                        '.pptx': 'PowerPoint Presentation',
                        '.xlsx': 'Excel Spreadsheet',
                        '.xls': 'Excel Spreadsheet',
                    }.get(ext, 'Text Document')
                    
                    for i, chunk in enumerate(chunks):
                        content = chunk.get("content", "")
                        if not content:
                            continue
                            
                        # Generate embeddings if not present
                        vector = chunk.get("contentVector", [])
                        if not vector:
                            try:
                                if hasattr(client, 'embeddings'):
                                    response = client.embeddings.create(
                                        input=content,
                                        model=embed_deployment
                                    )
                                    vector = response.data[0].embedding
                                else:
                                    vector = [0.0] * 3072  # Default zero vector
                            except Exception as e:
                                logging.error(f"[index_files] Failed to generate embedding for {fname}: {e}")
                                vector = [0.0] * 3072  # Default zero vector
                        
                        # Create document with full schema to match index
                        doc = {
                            "id": chunk.get("id", hashlib.md5(f"{fname}_{i}".encode()).hexdigest()),
                            "page_chunk": f"[{fname}] {content}",  # Add filename prefix like main app
                            "page_embedding_text_3_large": vector,
                            "content": content,
                            "contentVector": vector,
                            "page_number": chunk.get("page_number", i + 1),
                            "source_file": fname,
                            "source": fname,
                            "url": file_url,
                            "extraction_method": extraction_method,
                            "document_type": document_type,
                            "processing_timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            "filename": fname,
                        }
                        docs.append(doc)
                    
                    return docs
                
                logging.info(f"[index_files] Using fallback _chunk_to_docs with full schema")
            
            # Process files
            total_chunks = 0
            processing_results = []
            errors = []
            
            for file in files:
                try:
                    file_name = file.get('name', 'Unknown')
                    file_content = file.get('content')
                    file_url = file.get('source') or file.get('webUrl', '')
                    
                    if not file_content or not file_name:
                        processing_results.append({
                            'file': file_name,
                            'status': 'failed',
                            'error': 'No content or filename',
                            'chunks': 0
                        })
                        continue
                    
                    # Use the chunking function with same signature as main app
                    docs = _chunk_to_docs(
                        file_name,
                        file_content,
                        file_url,
                        oai_client,
                        embed_deploy,
                    )
                    
                    if docs:
                        # Upload to search index
                        sender.upload_documents(documents=docs)
                        total_chunks += len(docs)
                        
                        processing_results.append({
                            'file': file_name,
                            'status': 'success',
                            'chunks': len(docs),
                            'extraction_method': docs[0].get("extraction_method", "unknown") if docs else "unknown"
                        })
                        
                        logging.info(f"[index_files] Successfully indexed {file_name}: {len(docs)} chunks")
                    else:
                        processing_results.append({
                            'file': file_name,
                            'status': 'failed',
                            'error': 'Processing failed - no chunks created',
                            'chunks': 0
                        })
                        
                except Exception as e:
                    error_msg = f"Error processing file {file.get('name', 'Unknown')}: {str(e)}"
                    errors.append(error_msg)
                    processing_results.append({
                        'file': file.get('name', 'Unknown'),
                        'status': 'failed',
                        'error': str(e),
                        'chunks': 0
                    })
                    logging.error(f"[index_files] {error_msg}")
            
            # Close sender to flush remaining documents
            sender.close()
            
            successful_files = [r for r in processing_results if r['status'] == 'success']
            failed_files = [r for r in processing_results if r['status'] == 'failed']
            
            return {
                'success': len(failed_files) == 0,
                'message': f"Processed {len(files)} files: {len(successful_files)} successful, {len(failed_files)} failed",
                'total_chunks': total_chunks,
                'processing_results': processing_results,
                'files_successful': len(successful_files),
                'files_failed': len(failed_files),
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"File indexing failed: {str(e)}"
            logging.error(f"[index_files] {error_msg}")
            return {
                'success': False,
                'message': error_msg,
                'total_chunks': 0,
                'processing_results': [],
                'errors': [error_msg]
            }
    
    def get_folder_file_count(self, site_domain: str, site_name: str, drive_name: str, folder_path: str) -> int:
        """Get file count for a specific folder (expensive operation - use sparingly)"""
        try:
            # Ensure authentication is initialized
            self.sharepoint_reader.load_environment_variables_from_env_file()
            if not self.sharepoint_reader.access_token:
                auth_token = self.sharepoint_reader._msgraph_auth()
                if not auth_token:
                    return 0

            site_id, drive_id = self.sharepoint_reader._get_site_and_drive_ids(site_domain, site_name, drive_name)
            if not site_id or not drive_id:
                return 0

            headers = {
                'Authorization': f'Bearer {self.sharepoint_reader.access_token}',
                'Content-Type': 'application/json'
            }

            # Get folder contents to count files
            if folder_path == "/" or folder_path == "":
                url = f"{self.sharepoint_reader.graph_uri}/v1.0/sites/{site_id}/drives/{drive_id}/root/children"
            else:
                encoded_path = requests.utils.quote(folder_path, safe='')
                url = f"{self.sharepoint_reader.graph_uri}/v1.0/sites/{site_id}/drives/{drive_id}/root:/{encoded_path}:/children"

            # Only count files
            url += "?$filter=file ne null&$select=id&$count=true"
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return len(data.get('value', []))
            
            return 0
        except Exception as e:
            logging.error(f"Error getting file count for {folder_path}: {e}")
            return 0
