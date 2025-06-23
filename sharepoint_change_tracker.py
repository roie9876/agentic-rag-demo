"""
SharePoint Change Tracker
Implements comprehensive change detection and incremental indexing for SharePoint files.
Tracks new, modified, and deleted files with persistent metadata storage.
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

from connectors.sharepoint.sharepoint_data_reader import SharePointDataReader
from connectors.sharepoint.sharepoint_deleted_files_purger import SharepointDeletedFilesPurger


class SharePointChangeTracker:
    """
    Tracks changes to SharePoint files and manages incremental indexing.
    
    Features:
    - Persistent file metadata storage (SQLite)
    - Change detection (new, modified, deleted files)
    - Integration with existing indexing and purging logic
    - Configurable sync intervals
    - Detailed reporting of changes
    """
    
    def __init__(self, metadata_db_path: str = "sharepoint_metadata.db"):
        self.sharepoint_reader = SharePointDataReader()
        self.purger = SharepointDeletedFilesPurger()
        self.metadata_db_path = metadata_db_path
        self.init_metadata_db()
        
    def init_metadata_db(self):
        """Initialize the SQLite database for storing file metadata."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Create table for tracking file metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_metadata (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                parent_id TEXT,
                size INTEGER,
                modified_datetime TEXT,
                etag TEXT,
                last_indexed_datetime TEXT,
                checksum TEXT,
                indexed_in_search BOOLEAN DEFAULT FALSE,
                index_name TEXT
            )
        ''')
        
        # Create table for tracking sync operations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_datetime TEXT NOT NULL,
                files_added INTEGER DEFAULT 0,
                files_modified INTEGER DEFAULT 0,
                files_deleted INTEGER DEFAULT 0,
                folders_scanned INTEGER DEFAULT 0,
                sync_duration_seconds REAL,
                status TEXT,
                error_message TEXT
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parent_id ON file_metadata(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_modified_datetime ON file_metadata(modified_datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_indexed_status ON file_metadata(indexed_in_search)')
        
        conn.commit()
        conn.close()
        logging.info(f"Initialized metadata database at {self.metadata_db_path}")
    
    def get_current_sharepoint_files(self, folder_paths: List[str]) -> Dict[str, Dict]:
        """
        Get current file metadata from SharePoint for specified folders.
        Returns dict mapping file_id -> file_metadata
        """
        current_files = {}
        
        try:
            self.sharepoint_reader.load_environment_variables_from_env_file()
            
            for folder_path in folder_paths:
                logging.info(f"Scanning SharePoint folder: {folder_path}")
                
                # Get files from this folder (implementation depends on your SharePoint reader)
                # This is a placeholder - you'll need to adapt based on your actual SharePoint reader API
                files = self.sharepoint_reader.get_files_in_folder(folder_path)
                
                for file_info in files:
                    file_id = file_info.get('id')
                    if file_id:
                        current_files[file_id] = {
                            'id': file_id,
                            'name': file_info.get('name', ''),
                            'path': file_info.get('path', ''),
                            'parent_id': file_info.get('parentReference', {}).get('id'),
                            'size': file_info.get('size', 0),
                            'modified_datetime': file_info.get('lastModifiedDateTime', ''),
                            'etag': file_info.get('eTag', ''),
                            'checksum': file_info.get('file', {}).get('hashes', {}).get('sha1Hash', '')
                        }
                        
        except Exception as e:
            logging.error(f"Error getting current SharePoint files: {e}")
            
        return current_files
    
    def get_stored_file_metadata(self) -> Dict[str, Dict]:
        """Get previously stored file metadata from database."""
        stored_files = {}
        
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, path, parent_id, size, modified_datetime, 
                   etag, last_indexed_datetime, checksum, indexed_in_search, index_name
            FROM file_metadata
        ''')
        
        for row in cursor.fetchall():
            file_id = row[0]
            stored_files[file_id] = {
                'id': file_id,
                'name': row[1],
                'path': row[2],
                'parent_id': row[3],
                'size': row[4],
                'modified_datetime': row[5],
                'etag': row[6],
                'last_indexed_datetime': row[7],
                'checksum': row[8],
                'indexed_in_search': bool(row[9]),
                'index_name': row[10]
            }
        
        conn.close()
        return stored_files
    
    def detect_changes(self, current_files: Dict[str, Dict], stored_files: Dict[str, Dict]) -> Dict[str, List]:
        """
        Detect changes between current and stored file states.
        
        Returns:
            {
                'new': [file_ids...],           # Files that don't exist in stored
                'modified': [file_ids...],      # Files with different etag/modified_date
                'deleted': [file_ids...],       # Files in stored but not in current
                'unchanged': [file_ids...]      # Files with no changes
            }
        """
        current_ids = set(current_files.keys())
        stored_ids = set(stored_files.keys())
        
        new_files = list(current_ids - stored_ids)
        deleted_files = list(stored_ids - current_ids)
        
        potentially_modified = current_ids & stored_ids
        modified_files = []
        unchanged_files = []
        
        for file_id in potentially_modified:
            current = current_files[file_id]
            stored = stored_files[file_id]
            
            # Check if file has been modified (using etag and modified datetime)
            if (current.get('etag') != stored.get('etag') or 
                current.get('modified_datetime') != stored.get('modified_datetime')):
                modified_files.append(file_id)
            else:
                unchanged_files.append(file_id)
        
        return {
            'new': new_files,
            'modified': modified_files,
            'deleted': deleted_files,
            'unchanged': unchanged_files
        }
    
    def update_file_metadata(self, file_id: str, file_data: Dict, indexed_in_search: bool = False, index_name: str = None):
        """Update or insert file metadata in database."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO file_metadata 
            (id, name, path, parent_id, size, modified_datetime, etag, 
             last_indexed_datetime, checksum, indexed_in_search, index_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file_id,
            file_data.get('name', ''),
            file_data.get('path', ''),
            file_data.get('parent_id'),
            file_data.get('size', 0),
            file_data.get('modified_datetime', ''),
            file_data.get('etag', ''),
            now if indexed_in_search else file_data.get('last_indexed_datetime'),
            file_data.get('checksum', ''),
            indexed_in_search,
            index_name
        ))
        
        conn.commit()
        conn.close()
    
    def remove_file_metadata(self, file_ids: List[str]):
        """Remove file metadata for deleted files."""
        if not file_ids:
            return
            
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in file_ids])
        cursor.execute(f'DELETE FROM file_metadata WHERE id IN ({placeholders})', file_ids)
        
        conn.commit()
        conn.close()
        logging.info(f"Removed metadata for {len(file_ids)} deleted files")
    
    def record_sync_operation(self, changes: Dict[str, List], sync_duration: float, status: str = "success", error_message: str = None):
        """Record details of a sync operation."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sync_history 
            (sync_datetime, files_added, files_modified, files_deleted, 
             sync_duration_seconds, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(timezone.utc).isoformat(),
            len(changes.get('new', [])),
            len(changes.get('modified', [])),
            len(changes.get('deleted', [])),
            sync_duration,
            status,
            error_message
        ))
        
        conn.commit()
        conn.close()
    
    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """Get recent sync history."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sync_datetime, files_added, files_modified, files_deleted,
                   sync_duration_seconds, status, error_message
            FROM sync_history
            ORDER BY sync_datetime DESC
            LIMIT ?
        ''', (limit,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'sync_datetime': row[0],
                'files_added': row[1],
                'files_modified': row[2],
                'files_deleted': row[3],
                'sync_duration_seconds': row[4],
                'status': row[5],
                'error_message': row[6]
            })
        
        conn.close()
        return history
    
    async def sync_changes(self, folder_paths: List[str], index_name: str, auto_index: bool = True) -> Dict[str, Any]:
        """
        Main method to sync SharePoint changes.
        
        Args:
            folder_paths: List of SharePoint folder paths to sync
            index_name: Target Azure Search index name
            auto_index: Whether to automatically index new/modified files
            
        Returns:
            Dictionary with sync results and statistics
        """
        start_time = datetime.now()
        
        try:
            logging.info(f"Starting SharePoint sync for folders: {folder_paths}")
            
            # Get current state from SharePoint
            current_files = self.get_current_sharepoint_files(folder_paths)
            logging.info(f"Found {len(current_files)} files in SharePoint")
            
            # Get stored state from database
            stored_files = self.get_stored_file_metadata()
            logging.info(f"Found {len(stored_files)} files in metadata database")
            
            # Detect changes
            changes = self.detect_changes(current_files, stored_files)
            
            logging.info(f"Changes detected - New: {len(changes['new'])}, "
                        f"Modified: {len(changes['modified'])}, "
                        f"Deleted: {len(changes['deleted'])}, "
                        f"Unchanged: {len(changes['unchanged'])}")
            
            sync_results = {
                'changes': changes,
                'indexed_files': [],
                'deleted_from_index': [],
                'errors': []
            }
            
            # Handle deleted files first
            if changes['deleted']:
                logging.info(f"Processing {len(changes['deleted'])} deleted files")
                try:
                    # Use the existing purger to remove from search index
                    # This is a simplified approach - you might want to call the purger directly
                    # or implement deletion logic here
                    await self.purger.purge_deleted_files()
                    
                    # Remove from metadata database
                    self.remove_file_metadata(changes['deleted'])
                    sync_results['deleted_from_index'] = changes['deleted']
                    
                except Exception as e:
                    logging.error(f"Error handling deleted files: {e}")
                    sync_results['errors'].append(f"Deletion error: {str(e)}")
            
            # Handle new and modified files
            files_to_index = changes['new'] + changes['modified']
            
            if auto_index and files_to_index:
                logging.info(f"Indexing {len(files_to_index)} new/modified files")
                
                # Import indexing logic from sharepoint_index_manager
                # This would integrate with your existing indexing pipeline
                from sharepoint_index_manager import SharePointIndexManager
                index_manager = SharePointIndexManager()
                
                for file_id in files_to_index:
                    try:
                        file_data = current_files[file_id]
                        
                        # Index the file (you'll need to adapt this to your indexing method)
                        # success = await index_manager.index_file(file_data, index_name)
                        
                        # For now, just update metadata to indicate we attempted indexing
                        self.update_file_metadata(file_id, file_data, True, index_name)
                        sync_results['indexed_files'].append(file_id)
                        
                    except Exception as e:
                        logging.error(f"Error indexing file {file_id}: {e}")
                        sync_results['errors'].append(f"Indexing error for {file_id}: {str(e)}")
                        # Update metadata without marking as indexed
                        self.update_file_metadata(file_id, file_data, False, None)
            
            # Update metadata for unchanged files (to keep database current)
            for file_id in changes['unchanged']:
                if file_id in current_files:
                    stored_file = stored_files[file_id]
                    self.update_file_metadata(
                        file_id, 
                        current_files[file_id], 
                        stored_file.get('indexed_in_search', False),
                        stored_file.get('index_name')
                    )
            
            # Record sync operation
            duration = (datetime.now() - start_time).total_seconds()
            self.record_sync_operation(changes, duration, "success")
            
            sync_results['duration_seconds'] = duration
            sync_results['status'] = 'success'
            
            logging.info(f"SharePoint sync completed successfully in {duration:.2f}s")
            return sync_results
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            logging.error(f"SharePoint sync failed: {error_msg}")
            
            # Record failed sync
            self.record_sync_operation({}, duration, "failed", error_msg)
            
            return {
                'status': 'failed',
                'error': error_msg,
                'duration_seconds': duration,
                'changes': {},
                'indexed_files': [],
                'deleted_from_index': [],
                'errors': [error_msg]
            }


# Integration with Streamlit UI
def add_change_tracking_ui():
    """
    Add change tracking UI components to your Streamlit app.
    Call this from your main Streamlit app to add change tracking features.
    """
    import streamlit as st
    
    st.subheader("📊 SharePoint Change Tracking")
    
    # Initialize change tracker
    if 'change_tracker' not in st.session_state:
        st.session_state.change_tracker = SharePointChangeTracker()
    
    tracker = st.session_state.change_tracker
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Check for Changes", help="Scan SharePoint for file changes"):
            if 'selected_folders' in st.session_state and st.session_state.selected_folders:
                with st.spinner("Scanning for changes..."):
                    # This would be adapted to work with your folder selection
                    folder_paths = st.session_state.selected_folders
                    
                    # Get current and stored files
                    current_files = tracker.get_current_sharepoint_files(folder_paths)
                    stored_files = tracker.get_stored_file_metadata()
                    changes = tracker.detect_changes(current_files, stored_files)
                    
                    # Display results
                    st.success("✅ Change detection completed!")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🆕 New Files", len(changes['new']))
                    with col2:
                        st.metric("📝 Modified Files", len(changes['modified']))
                    with col3:
                        st.metric("🗑️ Deleted Files", len(changes['deleted']))
                    with col4:
                        st.metric("✅ Unchanged Files", len(changes['unchanged']))
                    
                    # Store changes in session state for potential action
                    st.session_state.detected_changes = changes
                    st.session_state.current_files = current_files
            else:
                st.warning("Please select SharePoint folders first")
    
    with col2:
        if st.button("📈 View Sync History", help="Show recent sync operations"):
            history = tracker.get_sync_history(limit=10)
            if history:
                st.write("**Recent Sync Operations:**")
                for sync in history:
                    with st.expander(f"🕐 {sync['sync_datetime'][:19]} - {sync['status'].title()}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Added:** {sync['files_added']}")
                            st.write(f"**Modified:** {sync['files_modified']}")
                        with col2:
                            st.write(f"**Deleted:** {sync['files_deleted']}")
                            st.write(f"**Duration:** {sync['sync_duration_seconds']:.1f}s")
                        with col3:
                            if sync['error_message']:
                                st.error(f"Error: {sync['error_message']}")
                            else:
                                st.success("Completed successfully")
            else:
                st.info("No sync history available")
    
    # Show detected changes if available
    if 'detected_changes' in st.session_state:
        changes = st.session_state.detected_changes
        
        if any(len(changes[key]) > 0 for key in ['new', 'modified', 'deleted']):
            st.subheader("🔍 Detected Changes")
            
            # Option to sync changes
            index_name = st.selectbox(
                "Target Index for Sync",
                options=['ragindex', 'custom-index'],  # Replace with your actual indexes
                help="Select the Azure Search index to sync changes to"
            )
            
            auto_index = st.checkbox("Auto-index new and modified files", value=True)
            
            if st.button("🚀 Sync Changes", type="primary"):
                if index_name:
                    folder_paths = st.session_state.get('selected_folders', [])
                    
                    with st.spinner("Syncing changes..."):
                        # This would need to be adapted for async execution in Streamlit
                        # You might need to use st.empty() and update it, or run in a separate thread
                        st.info("⚠️ Async sync integration needed - see implementation notes")
                        
                        # Placeholder for actual sync
                        # results = asyncio.run(tracker.sync_changes(folder_paths, index_name, auto_index))
                        
                    # st.success("✅ Sync completed!")
                    # Display results...
                else:
                    st.warning("Please select a target index")


if __name__ == "__main__":
    # Example usage
    tracker = SharePointChangeTracker()
    
    # Example: detect changes for specific folders
    folder_paths = ["/sites/YourSite/Shared Documents/Folder1"]
    
    # Run async sync
    # results = asyncio.run(tracker.sync_changes(folder_paths, "ragindex", auto_index=True))
    # print(f"Sync results: {results}")
