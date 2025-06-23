"""
Integration Example: SharePoint Change Tracking with Existing Index Manager

This shows how to integrate the SharePointChangeTracker with your existing
sharepoint_index_manager.py for incremental indexing.
"""

import asyncio
import logging
from typing import List, Dict, Any
from sharepoint_change_tracker import SharePointChangeTracker
from sharepoint_index_manager import SharePointIndexManager


class IntegratedSharePointSync:
    """
    Integrates change tracking with the existing SharePoint indexing pipeline.
    Provides incremental indexing capabilities.
    """
    
    def __init__(self):
        self.change_tracker = SharePointChangeTracker()
        self.index_manager = SharePointIndexManager()
    
    def sync_folders_incrementally(self, selected_folders: List[str], index_name: str) -> Dict[str, Any]:
        """
        Perform incremental sync of SharePoint folders.
        
        Args:
            selected_folders: List of folder paths to sync
            index_name: Target Azure Search index
            
        Returns:
            Sync results including counts and errors
        """
        try:
            logging.info(f"Starting incremental sync for {len(selected_folders)} folders")
            
            # Step 1: Get current files from SharePoint
            current_files = self.change_tracker.get_current_sharepoint_files(selected_folders)
            logging.info(f"Found {len(current_files)} files in SharePoint")
            
            # Step 2: Get stored metadata
            stored_files = self.change_tracker.get_stored_file_metadata()
            logging.info(f"Found {len(stored_files)} files in metadata database")
            
            # Step 3: Detect changes
            changes = self.change_tracker.detect_changes(current_files, stored_files)
            
            logging.info(f"Changes detected:")
            logging.info(f"  New: {len(changes['new'])}")
            logging.info(f"  Modified: {len(changes['modified'])}")
            logging.info(f"  Deleted: {len(changes['deleted'])}")
            logging.info(f"  Unchanged: {len(changes['unchanged'])}")
            
            results = {
                'changes': changes,
                'indexed_count': 0,
                'deleted_count': 0,
                'errors': []
            }
            
            # Step 4: Handle deletions using existing purger
            if changes['deleted']:
                try:
                    # Run the existing deletion logic
                    asyncio.run(self.change_tracker.purger.purge_deleted_files())
                    
                    # Remove from metadata database
                    self.change_tracker.remove_file_metadata(changes['deleted'])
                    results['deleted_count'] = len(changes['deleted'])
                    
                    logging.info(f"Successfully deleted {len(changes['deleted'])} files from index")
                except Exception as e:
                    error_msg = f"Error deleting files: {str(e)}"
                    logging.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Step 5: Index new and modified files
            files_to_index = changes['new'] + changes['modified']
            
            if files_to_index:
                logging.info(f"Indexing {len(files_to_index)} new/modified files")
                
                indexed_count = 0
                for file_id in files_to_index:
                    try:
                        file_data = current_files[file_id]
                        
                        # Use existing index manager to process the file
                        # This is a simplified example - you'll need to adapt based on your actual method signatures
                        success = self._index_single_file(file_data, index_name)
                        
                        if success:
                            # Update metadata to mark as indexed
                            self.change_tracker.update_file_metadata(
                                file_id, file_data, True, index_name
                            )
                            indexed_count += 1
                        else:
                            # Update metadata without marking as indexed
                            self.change_tracker.update_file_metadata(
                                file_id, file_data, False, None
                            )
                            results['errors'].append(f"Failed to index file: {file_data.get('name', file_id)}")
                            
                    except Exception as e:
                        error_msg = f"Error indexing file {file_id}: {str(e)}"
                        logging.error(error_msg)
                        results['errors'].append(error_msg)
                
                results['indexed_count'] = indexed_count
                logging.info(f"Successfully indexed {indexed_count}/{len(files_to_index)} files")
            
            # Step 6: Update metadata for unchanged files (keep database current)
            for file_id in changes['unchanged']:
                if file_id in current_files:
                    stored_file = stored_files.get(file_id, {})
                    self.change_tracker.update_file_metadata(
                        file_id, 
                        current_files[file_id], 
                        stored_file.get('indexed_in_search', False),
                        stored_file.get('index_name')
                    )
            
            # Step 7: Record the sync operation
            duration = 0  # You can track this if needed
            status = "success" if not results['errors'] else "partial_success"
            self.change_tracker.record_sync_operation(changes, duration, status)
            
            results['status'] = status
            return results
            
        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            logging.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg,
                'changes': {},
                'indexed_count': 0,
                'deleted_count': 0,
                'errors': [error_msg]
            }
    
    def _index_single_file(self, file_data: Dict, index_name: str) -> bool:
        """
        Index a single file using the existing indexing pipeline.
        
        This is a placeholder method - you'll need to implement this
        based on your actual SharePointIndexManager methods.
        """
        try:
            # Example implementation - adapt to your actual methods
            # The index manager would need methods to handle individual files
            
            # Option 1: If your index manager has a method to index individual files
            # return self.index_manager.index_single_file(file_data, index_name)
            
            # Option 2: If you need to use the existing batch processing
            # You could collect files and process them in batches
            
            # For now, just return True to indicate success
            # You'll need to implement the actual indexing logic here
            logging.info(f"Would index file: {file_data.get('name', 'unknown')}")
            return True
            
        except Exception as e:
            logging.error(f"Error indexing file: {e}")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get the current sync status and recent history."""
        try:
            # Get recent sync history
            history = self.change_tracker.get_sync_history(limit=5)
            
            # Get current metadata counts
            stored_files = self.change_tracker.get_stored_file_metadata()
            indexed_files = sum(1 for f in stored_files.values() if f.get('indexed_in_search', False))
            
            return {
                'total_files_tracked': len(stored_files),
                'indexed_files': indexed_files,
                'unindexed_files': len(stored_files) - indexed_files,
                'recent_syncs': history,
                'status': 'ready'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


# Example usage in Streamlit app
def add_integrated_sync_ui():
    """
    Add this to your main Streamlit app to enable incremental sync features.
    
    Place this in your agentic-rag-demo.py or wherever you handle SharePoint UI.
    """
    import streamlit as st
    
    st.subheader("🔄 Incremental SharePoint Sync")
    
    # Initialize the integrated sync manager
    if 'integrated_sync' not in st.session_state:
        st.session_state.integrated_sync = IntegratedSharePointSync()
    
    sync_manager = st.session_state.integrated_sync
    
    # Show current status
    status = sync_manager.get_sync_status()
    
    if status['status'] == 'ready':
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📁 Total Files", status['total_files_tracked'])
        with col2:
            st.metric("✅ Indexed", status['indexed_files'])
        with col3:
            st.metric("⏳ Unindexed", status['unindexed_files'])
        with col4:
            recent_syncs = len(status['recent_syncs'])
            st.metric("📊 Recent Syncs", recent_syncs)
    else:
        st.error(f"Status Error: {status.get('error', 'Unknown error')}")
    
    # Sync controls
    col1, col2 = st.columns(2)
    
    with col1:
        # Index selection
        index_options = ['ragindex', 'sharepoint-index']  # Replace with your actual indexes
        selected_index = st.selectbox(
            "Target Index",
            options=index_options,
            help="Select the Azure Search index to sync to"
        )
    
    with col2:
        # Sync button
        if st.button("🚀 Run Incremental Sync", type="primary"):
            if 'selected_folders' in st.session_state and st.session_state.selected_folders:
                folders = st.session_state.selected_folders
                
                with st.spinner("Running incremental sync..."):
                    results = sync_manager.sync_folders_incrementally(folders, selected_index)
                
                # Display results
                if results['status'] in ['success', 'partial_success']:
                    st.success("✅ Sync completed!")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🆕 Files Indexed", results['indexed_count'])
                    with col2:
                        st.metric("🗑️ Files Deleted", results['deleted_count'])
                    with col3:
                        if results['errors']:
                            st.metric("⚠️ Errors", len(results['errors']))
                        else:
                            st.metric("✅ Status", "Clean")
                    
                    # Show detailed changes
                    changes = results.get('changes', {})
                    if any(len(changes.get(k, [])) > 0 for k in ['new', 'modified', 'deleted']):
                        with st.expander("📋 Detailed Changes"):
                            if changes.get('new'):
                                st.write(f"**New files ({len(changes['new'])}):** {', '.join(changes['new'][:10])}...")
                            if changes.get('modified'):
                                st.write(f"**Modified files ({len(changes['modified'])}):** {', '.join(changes['modified'][:10])}...")
                            if changes.get('deleted'):
                                st.write(f"**Deleted files ({len(changes['deleted'])}):** {', '.join(changes['deleted'][:10])}...")
                    
                    # Show errors if any
                    if results['errors']:
                        with st.expander("⚠️ Errors"):
                            for error in results['errors']:
                                st.error(error)
                else:
                    st.error(f"❌ Sync failed: {results.get('error', 'Unknown error')}")
            else:
                st.warning("Please select SharePoint folders first")
    
    # Show recent sync history
    if status['status'] == 'ready' and status['recent_syncs']:
        with st.expander("📈 Recent Sync History"):
            for sync in status['recent_syncs']:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"🕐 {sync['sync_datetime'][:19]}")
                with col2:
                    st.write(f"Status: {sync['status']}")
                with col3:
                    total_changes = sync['files_added'] + sync['files_modified'] + sync['files_deleted']
                    st.write(f"Changes: {total_changes}")


if __name__ == "__main__":
    # Example usage
    sync_manager = IntegratedSharePointSync()
    
    # Example folder paths
    folders = ["/sites/YourSite/Shared Documents/Documents"]
    
    # Run incremental sync
    results = sync_manager.sync_folders_incrementally(folders, "ragindex")
    print(f"Sync results: {results}")
