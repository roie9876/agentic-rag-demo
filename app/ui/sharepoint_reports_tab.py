"""
SharePoint Reports Tab Module
============================
Handles the SharePoint indexing reports functionality.
Extracted from main agentic-rag-demo.py to reduce code bloat.
"""

import streamlit as st
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List


def render_sharepoint_reports_tab(
    session_state: Dict[str, Any],
    target_index: str,
    **kwargs
) -> None:
    """
    Render the SharePoint Reports tab with all its functionality.
    
    Args:
        session_state: Streamlit session state dictionary
        target_index: The target Azure Search index name
        **kwargs: Additional arguments
    """
    st.markdown("### 📊 Indexing Reports")
    
    try:
        from sharepoint_scheduler import SharePointScheduler
        scheduler = SharePointScheduler()
        
        # Report management buttons
        report_mgmt_col1, report_mgmt_col2, report_mgmt_col3 = st.columns([2, 1, 1])
        
        with report_mgmt_col1:
            st.markdown("**Report Management**")
        
        with report_mgmt_col2:
            if st.button("🔄 Refresh Reports"):
                # Use session state to trigger reports refresh without full page reload
                if "reports_refresh_counter" not in session_state:
                    session_state.reports_refresh_counter = 0
                session_state.reports_refresh_counter += 1
                st.success("Reports refreshed!", icon="✅")
        
        with report_mgmt_col3:
            # Initialize delete confirmation state
            if "delete_all_reports_confirm" not in session_state:
                session_state.delete_all_reports_confirm = False
            
            if not session_state.delete_all_reports_confirm:
                if st.button("🗑️ Delete All Reports"):
                    session_state.delete_all_reports_confirm = True
            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Confirm", type="primary"):
                        result = scheduler.delete_all_reports()
                        if result["success"]:
                            st.success(f"✅ {result['message']}")
                            st.balloons()
                            session_state.delete_all_reports_confirm = False
                            # Invalidate reports cache
                            session_state.reports_data = None
                            time.sleep(1)
                            # Increment refresh counter to trigger reload
                            if "reports_refresh_counter" not in session_state:
                                session_state.reports_refresh_counter = 0
                            session_state.reports_refresh_counter += 1
                        else:
                            st.error(f"❌ {result['message']}")
                            session_state.delete_all_reports_confirm = False
                with col_b:
                    if st.button("❌ Cancel"):
                        session_state.delete_all_reports_confirm = False
        
        st.divider()
        
        # Initialize reports refresh system
        if "reports_data" not in session_state:
            session_state.reports_data = None
            session_state.reports_last_refresh = 0
        
        # Check if we need to refresh reports data
        current_refresh_counter = session_state.get("reports_refresh_counter", 0)
        if (session_state.reports_data is None or 
            current_refresh_counter > session_state.reports_last_refresh):
            # Load fresh reports data
            session_state.reports_data = scheduler.get_reports()
            session_state.reports_last_refresh = current_refresh_counter
        
        # Use cached reports data
        reports = session_state.reports_data
        
        if not reports:
            st.info("No indexing reports available yet. Run some indexing operations to see reports here.")
        else:
            # Reports summary
            col1, col2, col3, col4 = st.columns(4)
            
            successful_reports = [r for r in reports if r.get('status') == 'completed']
            failed_reports = [r for r in reports if r.get('status') == 'error']
            running_reports = [r for r in reports if r.get('status') == 'running']
            
            with col1:
                st.metric("Total Reports", len(reports))
            with col2:
                st.metric("Successful", len(successful_reports))
            with col3:
                st.metric("Failed", len(failed_reports))
            with col4:
                st.metric("Running", len(running_reports))
            
            # Reports list
            st.markdown("**Report History**")
            
            for report in reports[:10]:  # Show last 10 reports
                _render_report_item(report, scheduler, session_state)
    
    except ImportError:
        st.error("❌ Reports module not available")
    except Exception as e:
        st.error(f"❌ Reports error: {str(e)}")


def _render_report_item(report: Dict[str, Any], scheduler, session_state: Dict[str, Any]) -> None:
    """Render a single report item with all its details."""
    with st.container():
        report_col1, report_col2, report_col3 = st.columns([3, 1, 1])
        
        with report_col1:
            start_time = datetime.fromisoformat(report['start_time'])
            status_icon = {
                'completed': '✅',
                'error': '❌',
                'running': '🔄'
            }.get(report.get('status', 'unknown'), '❓')
            
            st.write(f"{status_icon} {start_time.strftime('%Y-%m-%d %H:%M:%S')} - {report.get('type', 'unknown').title()}")
            if report.get('status') == 'completed':
                caption_text = f"Files: {report.get('files_successful', 0)}/{report.get('files_processed', 0)} | Chunks: {report.get('chunks_created', 0)}"
                
                # Add purge info if available
                if report.get('purge_results'):
                    purge_deleted = report['purge_results'].get('documents_deleted', 0)
                    if purge_deleted > 0:
                        caption_text += f" | Purged: {purge_deleted} docs"
                    else:
                        caption_text += " | Purged: none"
                elif report.get('auto_purge_enabled'):
                    caption_text += " | Auto-purge: enabled"
                
                st.caption(caption_text)
        
        with report_col2:
            # View report details
            if st.button("👁️ View", key=f"view_{report['id']}"):
                session_state[f"show_report_{report['id']}"] = True
        
        with report_col3:
            # Delete report
            if st.button("🗑️ Delete", key=f"delete_{report['id']}"):
                result = scheduler.delete_report(report['id'])
                if result['success']:
                    st.success(f"Report deleted: {report['id']}")
                    # Invalidate reports cache
                    session_state.reports_data = None
                    # Increment refresh counter to trigger reload
                    if "reports_refresh_counter" not in session_state:
                        session_state.reports_refresh_counter = 0
                    session_state.reports_refresh_counter += 1
                else:
                    st.error(result['message'])
    
    # Show report details if requested
    if session_state.get(f"show_report_{report['id']}", False):
        _render_report_details(report, session_state)
    
    st.divider()


def _render_report_details(report: Dict[str, Any], session_state: Dict[str, Any]) -> None:
    """Render detailed view of a report."""
    with st.expander(f"📋 Report Details - {report['id']}", expanded=True):
        
        # Close button
        if st.button("❌ Close", key=f"close_{report['id']}"):
            session_state[f"show_report_{report['id']}"] = False
            st.rerun()
        
        # Report details
        detail_col1, detail_col2 = st.columns(2)
        
        start_time = datetime.fromisoformat(report['start_time'])
        
        with detail_col1:
            st.markdown("**General Info**")
            st.write(f"**Report ID:** {report['id']}")
            st.write(f"**Type:** {report.get('type', 'unknown').title()}")
            st.write(f"**Status:** {report.get('status', 'unknown').title()}")
            st.write(f"**Start Time:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if report.get('end_time'):
                end_time = datetime.fromisoformat(report['end_time'])
                duration = (end_time - start_time).total_seconds()
                st.write(f"**Duration:** {duration:.1f} seconds")
        
        with detail_col2:
            st.markdown("**Processing Summary**")
            st.write(f"**Files Processed:** {report.get('files_processed', 0)}")
            st.write(f"**Files Successful:** {report.get('files_successful', 0)}")
            st.write(f"**Files Failed:** {report.get('files_failed', 0)}")
            st.write(f"**Chunks Created:** {report.get('chunks_created', 0)}")
        
        # Folders
        if report.get('folders'):
            st.markdown("**Folders Processed**")
            for folder in report['folders']:
                st.write(f"📁 {folder}")
        
        # Processing details
        if report.get('processing_details'):
            st.markdown("**File Processing Details**")
            for detail in report['processing_details']:
                if detail.get('status') == 'success':
                    st.write(f"✅ {detail['file']} - {detail.get('chunks', 0)} chunks ({detail.get('method', 'unknown')})")
                else:
                    st.write(f"❌ {detail['file']} - {detail.get('error', 'Unknown error')}")
        
        # Errors
        if report.get('errors'):
            st.markdown("**Errors**")
            for error in report['errors']:
                st.error(error)
        
        # Auto-purge results
        if report.get('purge_results'):
            _render_purge_results(report['purge_results'])
        elif report.get('auto_purge_enabled'):
            st.info("🗑️ Auto-purge was enabled but no purge results available (likely due to indexing failure)")
        else:
            st.info("🗑️ Auto-purge was disabled for this operation")


def _render_purge_results(purge_results: Dict[str, Any]) -> None:
    """Render auto-purge results section."""
    st.markdown("**🗑️ Auto-Purge Results**")
    
    purge_col1, purge_col2 = st.columns(2)
    
    with purge_col1:
        st.write(f"**Purge Success:** {'✅ Yes' if purge_results.get('success') else '❌ No'}")
        st.write(f"**Documents Checked:** {purge_results.get('documents_checked', 0)}")
        st.write(f"**Files Checked:** {purge_results.get('files_checked', 0)}")
    
    with purge_col2:
        st.write(f"**Files Not Found:** {purge_results.get('files_not_found', 0)}")
        st.write(f"**Documents Deleted:** {purge_results.get('documents_deleted', 0)}")
        st.write(f"**Purge Message:** {purge_results.get('message', 'No message')}")
    
    if purge_results.get('errors'):
        st.markdown("**Purge Errors**")
        for error in purge_results['errors']:
            st.error(f"Purge: {error}")


def render_sharepoint_purge_section(
    session_state: Dict[str, Any], 
    target_index: str,
    **kwargs
) -> None:
    """
    Render the SharePoint file purge section.
    
    Args:
        session_state: Streamlit session state dictionary
        target_index: The target Azure Search index name
        **kwargs: Additional arguments
    """
    st.divider()
    st.subheader("🗑️ Purge Deleted Files")
    
    with st.expander("💡 About File Deletion Purging", expanded=False):
        st.markdown("""
        **What this does:**
        - Scans your Azure Search index for SharePoint documents
        - Checks if each file still exists in SharePoint
        - Removes orphaned documents (files that were deleted from SharePoint but still exist in the index)
        
        **When to use:**
        - After deleting files from SharePoint
        - When you notice search results showing files that no longer exist
        - As periodic maintenance to keep the index clean
        
        **How it works:**
        - Uses Microsoft Graph API to verify file existence
        - Processes files in batches for efficiency
        - Provides detailed logging of deletion operations
        """)
    
    # Purge controls
    purge_col1, purge_col2 = st.columns([2, 1])
    
    with purge_col1:
        st.markdown("**Run deletion purge for the current index:**")
        st.info(f"🎯 Target index: **{target_index}**")
        
        # Show which folder will be used for folder-specific purging
        if hasattr(session_state, 'sp_selected_folders') and session_state.sp_selected_folders:
            raw_folder = session_state.sp_selected_folders[0]
            # Parse folder path to extract just the folder part
            if '|' in raw_folder:
                target_folder = raw_folder.split('|')[-1]
            else:
                target_folder = raw_folder
            st.info(f"📁 Target folder: **{target_folder}** (folder-specific purging)")
            st.caption("Only files missing from this specific folder will be considered orphaned")
        else:
            st.info(f"📁 Target folder: **/ppt** (default folder-specific purging)")
            st.caption("Only files missing from the /ppt folder will be considered orphaned")
        
        # Show warning about the operation
        st.warning("⚠️ This will permanently delete orphaned documents from the search index. Make sure you have backups if needed.")
        
        # Purge options
        show_preview = st.checkbox("Preview orphaned files before deletion", value=True)
        
    with purge_col2:
        st.markdown("**Purge Status**")
        
        # Initialize purge status in session state
        if "purge_status" not in session_state:
            session_state.purge_status = {
                "is_running": False,
                "last_run": None,
                "last_result": None
            }
        
        status = session_state.purge_status
        
        if status["is_running"]:
            st.info("🔄 Purge Running...")
        elif status["last_run"]:
            st.success("✅ Last Run Complete")
            st.caption(f"Time: {status['last_run']}")
        else:
            st.info("🟡 Ready to Run")
    
    # Purge action buttons
    st.markdown("---")
    purge_action_col1, purge_action_col2 = st.columns(2)
    
    with purge_action_col1:
        if st.button("🔍 Preview Orphaned Files", disabled=status["is_running"]):
            _handle_preview_orphaned_files(session_state, target_index)
    
    with purge_action_col2:
        if st.button("🗑️ Run Purge Now", type="primary", disabled=status["is_running"]):
            _handle_run_purge_now(session_state, target_index, show_preview)
    
    # Show purge history if available
    if status["last_result"]:
        _render_purge_history(status, session_state)


def _handle_preview_orphaned_files(session_state: Dict[str, Any], target_index: str) -> None:
    """Handle the preview orphaned files operation."""
    with st.spinner("Scanning for orphaned files..."):
        try:
            from connectors.sharepoint.sharepoint_deleted_files_purger import SharepointDeletedFilesPurger
            
            # Get the target folder path from session state or use /ppt as default
            target_folder_path = _get_target_folder_path(session_state)
            
            # Initialize and run the purger in preview mode with UI-selected index and folder
            purger = SharepointDeletedFilesPurger(index_name=target_index, target_folder_path=target_folder_path)
            
            # Run the async preview operation
            async def run_preview():
                return await purger.preview_deleted_files()
            
            # Execute the preview and get results
            preview_result = asyncio.run(run_preview())
            
            if preview_result["success"]:
                _display_preview_results(preview_result)
            else:
                _display_preview_error(preview_result, target_index)
                
        except Exception as e:
            _display_preview_exception(e, target_index)


def _handle_run_purge_now(session_state: Dict[str, Any], target_index: str, show_preview: bool) -> None:
    """Handle the run purge now operation."""
    print("🚀 [UI DEBUG] PURGE BUTTON CLICKED! Starting purge directly...")
    
    # Show warning but proceed directly
    if show_preview:
        st.warning("⚠️ Running purge - this will delete orphaned files from the search index.")
    
    # Run the actual purge
    print("🚀 [UI DEBUG] Setting purge_status is_running = True")
    session_state.purge_status["is_running"] = True
    
    with st.spinner("🗑️ Running deletion purge... This may take a few minutes."):
        try:
            from connectors.sharepoint.sharepoint_deleted_files_purger import SharepointDeletedFilesPurger
            
            # Get the target folder path from session state or use /ppt as default
            target_folder_path = _get_target_folder_path(session_state)
            
            # Initialize and run the purger with UI-selected index and folder
            print(f"🚀 [UI DEBUG] STARTING PURGE FROM UI:")
            print(f"🚀 [UI DEBUG] Target index: {target_index}")
            print(f"🚀 [UI DEBUG] Target folder: {target_folder_path}")
            print(f"🚀 [UI DEBUG] Creating SharepointDeletedFilesPurger...")
            
            purger = SharepointDeletedFilesPurger(index_name=target_index, target_folder_path=target_folder_path)
            
            # Run the async purge operation and capture result
            async def run_purge():
                print(f"🚀 [UI DEBUG] About to call purge_deleted_files()...")
                result = await purger.purge_deleted_files()
                print(f"🚀 [UI DEBUG] Purge operation returned: {result}")
                return result
            
            # Execute the purge and get results
            print(f"🚀 [UI DEBUG] Running asyncio.run(run_purge())...")
            purge_result = asyncio.run(run_purge())
            print(f"🚀 [UI DEBUG] Purge completed, result: {purge_result}")
            
            # Update status based on result
            if purge_result["success"]:
                _handle_purge_success(session_state, purge_result)
            else:
                _handle_purge_failure(session_state, purge_result)
                
        except Exception as e:
            _handle_purge_exception(session_state, e, target_index)
    
    st.rerun()


def _get_target_folder_path(session_state: Dict[str, Any]) -> str:
    """Get the target folder path from session state or default."""
    if hasattr(session_state, 'sp_selected_folders') and session_state.sp_selected_folders:
        # Parse the first selected folder path to extract just the folder part
        raw_folder = session_state.sp_selected_folders[0]
        # Format: domain||site|folder_path - extract just the folder_path
        if '|' in raw_folder:
            return raw_folder.split('|')[-1]  # Get the last part
        else:
            return raw_folder
    else:
        # Default to /ppt folder for folder-specific purging
        return "/ppt"


def _display_preview_results(preview_result: Dict[str, Any]) -> None:
    """Display preview results."""
    st.success("✅ Preview completed successfully!")
    
    # Show preview results
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Files Checked", preview_result["files_checked"])
    with col2:
        st.metric("Orphaned Files", preview_result["files_not_found"])
    with col3:
        st.metric("Chunks to Delete", preview_result["would_delete_count"])
    
    st.info(f"💡 {preview_result['message']}")
    
    # Show orphaned files details if any
    if preview_result["orphaned_files"]:
        st.markdown("**🗑️ Orphaned Files (would be deleted):**")
        
        for i, file_info in enumerate(preview_result["orphaned_files"][:10]):  # Show max 10
            with st.expander(f"📄 {file_info['file_name']} ({file_info['chunk_count']} chunks)", expanded=False):
                st.write(f"**File:** {file_info['file_name']}")
                st.write(f"**Path:** {file_info['file_path']}")
                st.write(f"**Parent ID:** {file_info['parent_id']}")
                st.write(f"**Chunks:** {file_info['chunk_count']}")
                st.caption("This file no longer exists in SharePoint but has indexed chunks in the search index.")
        
        if len(preview_result["orphaned_files"]) > 10:
            st.caption(f"... and {len(preview_result['orphaned_files']) - 10} more files")
        
        st.warning("⚠️ These files would be permanently deleted from the search index if you run the purge.")
    else:
        st.success("🎉 No orphaned files found! Your index is clean.")


def _display_preview_error(preview_result: Dict[str, Any], target_index: str) -> None:
    """Display preview error."""
    st.error(f"❌ Preview failed: {preview_result['message']}")
    
    # Show error details
    if preview_result.get("errors"):
        st.markdown("**Error Details:**")
        for error in preview_result["errors"]:
            st.error(f"• {error}")


def _display_preview_exception(e: Exception, target_index: str) -> None:
    """Display preview exception."""
    st.error(f"❌ Preview failed: {str(e)}")
    st.markdown(f"""
    **Troubleshooting:**
    - Check SharePoint authentication credentials in `.env` file:
      - `SHAREPOINT_CONNECTOR_ENABLED=true`
      - `SHAREPOINT_TENANT_ID=your-tenant-id`
      - `SHAREPOINT_CLIENT_ID=your-client-id`
      - `SHAREPOINT_CLIENT_SECRET=your-client-secret`
      - `SHAREPOINT_SITE_DOMAIN=your-domain.sharepoint.com`
      - `SHAREPOINT_SITE_NAME=your-site-name` (optional for root site)
    - Verify Azure Search index permissions
    - Verify the search index contains SharePoint documents with `source='sharepoint'`
    - Index name is taken from UI selection: **{target_index}**
    """)


def _handle_purge_success(session_state: Dict[str, Any], purge_result: Dict[str, Any]) -> None:
    """Handle successful purge operation."""
    session_state.purge_status.update({
        "is_running": False,
        "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_result": "success"
    })
    
    # Store detailed results for history display
    session_state.last_purge_details = {
        'files_checked': purge_result["files_checked"],
        'files_not_found': purge_result["files_not_found"],
        'documents_deleted': purge_result["documents_deleted"],
        'documents_checked': purge_result["documents_checked"]
    }
    
    st.success("✅ Purge completed successfully!")
    
    # Show detailed results
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Documents Checked", purge_result["documents_checked"])
    with col2:
        st.metric("Files Checked", purge_result["files_checked"])
    with col3:
        st.metric("Files Not Found", purge_result["files_not_found"])
    with col4:
        st.metric("Chunks Deleted", purge_result["documents_deleted"])
    
    st.info(f"📊 {purge_result['message']}")
    
    # Show next steps
    st.markdown("""
    **What happened:**
    - Scanned SharePoint documents in the search index
    - Checked each file's existence in SharePoint using Microsoft Graph API
    - Removed orphaned documents from the search index
    
    **Next steps:**
    - Run a test search to verify cleanup
    - Monitor your search index size for space savings
    """)


def _handle_purge_failure(session_state: Dict[str, Any], purge_result: Dict[str, Any]) -> None:
    """Handle failed purge operation."""
    session_state.purge_status.update({
        "is_running": False,
        "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_result": f"error: {purge_result['message']}"
    })
    
    st.error(f"❌ Purge failed: {purge_result['message']}")
    
    # Show error details
    if purge_result.get("errors"):
        st.markdown("**Error Details:**")
        for error in purge_result["errors"]:
            st.error(f"• {error}")


def _handle_purge_exception(session_state: Dict[str, Any], e: Exception, target_index: str) -> None:
    """Handle purge operation exception."""
    session_state.purge_status.update({
        "is_running": False,
        "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_result": f"error: {str(e)}"
    })
    
    st.error(f"❌ Purge failed: {str(e)}")
    
    # Show troubleshooting tips
    st.markdown(f"""
    **Troubleshooting:**
    - Check SharePoint authentication credentials in `.env` file:
      - `SHAREPOINT_CONNECTOR_ENABLED=true`
      - `SHAREPOINT_TENANT_ID=your-tenant-id`
      - `SHAREPOINT_CLIENT_ID=your-client-id`
      - `SHAREPOINT_CLIENT_SECRET=your-client-secret`
      - `SHAREPOINT_SITE_DOMAIN=your-domain.sharepoint.com`
      - `SHAREPOINT_SITE_NAME=your-site-name` (optional for root site)
    - Verify Azure Search index permissions
    - Verify the search index contains SharePoint documents with `source='sharepoint'`
    - Index name is taken from UI selection: **{target_index}**
    """)


def _render_purge_history(status: Dict[str, Any], session_state: Dict[str, Any]) -> None:
    """Render purge history section."""
    with st.expander("📊 Purge History", expanded=False):
        if status["last_result"] == "success":
            st.success(f"✅ Last purge successful at {status['last_run']}")
            
            # Try to show additional details if they exist in session state
            if hasattr(session_state, 'last_purge_details'):
                details = session_state.last_purge_details
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Files Checked", details.get('files_checked', 'N/A'))
                with col2:
                    st.metric("Files Deleted", details.get('files_not_found', 'N/A'))
                with col3:
                    st.metric("Chunks Removed", details.get('documents_deleted', 'N/A'))
        else:
            st.error(f"❌ Last purge failed at {status['last_run']}")
            st.error(f"Error: {status['last_result']}")
        
        st.markdown("""
        **For detailed purge logs:**
        - Check the application console output
        - Look for `[sharepoint_purge_deleted_files]` log entries
        - Monitor Azure Search index size before/after purge
        
        **Understanding the results:**
        - **Files Checked**: Number of unique SharePoint files found in the index
        - **Files Deleted**: Number of files that no longer exist in SharePoint
        - **Chunks Removed**: Number of document chunks purged from the search index
        """)