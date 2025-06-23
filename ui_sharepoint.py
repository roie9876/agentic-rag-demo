"""
SharePoint Index UI
Streamlit interface for SharePoint folder selection and indexing
"""

import streamlit as st
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from sharepoint_index_manager import SharePointIndexManager
from sharepoint_scheduler import SharePointScheduler
from sharepoint_reports import SharePointReports
from ui_performance_optimizer import ui_perf_optimizer, optimized_folder_renderer
from ultra_fast_sharepoint_ui import UltraFastSharePointUI


class SharePointIndexUI:
    """Streamlit UI for SharePoint indexing operations"""
    
    def __init__(self):
        self.manager = SharePointIndexManager()
        self.scheduler = SharePointScheduler()
        self.reports = SharePointReports()
        self.perf_optimizer = ui_perf_optimizer
        
        # Initialize session state
        if 'sp_selected_folders' not in st.session_state:
            st.session_state.sp_selected_folders = []
        if 'sp_auth_checked' not in st.session_state:
            st.session_state.sp_auth_checked = False
        if 'sp_auth_status' not in st.session_state:
            st.session_state.sp_auth_status = {}
    
    def render_sharepoint_index_tab(self):
        """Render the main SharePoint Index tab"""
        st.header("📁 SharePoint Index")
        st.markdown("Select multiple SharePoint folders and manage automated indexing schedules.")
        
        # Performance debug info (optional)
        self.perf_optimizer.render_performance_debug()
        
        # Check authentication with caching
        if not st.session_state.sp_auth_checked:
            with st.spinner("Checking SharePoint authentication..."):
                auth_status = self.perf_optimizer.cache_expensive_operation(
                    "sharepoint_auth_status",
                    self.manager.get_sharepoint_auth_status
                )
                st.session_state.sp_auth_status = auth_status
                st.session_state.sp_auth_checked = True
        
        auth_status = st.session_state.sp_auth_status
        
        if not auth_status.get('authenticated', False):
            st.error(f"❌ SharePoint Authentication Failed: {auth_status.get('error', 'Unknown error')}")
            st.markdown("""
            **Please ensure your environment variables are configured:**
            - `SHAREPOINT_TENANT_ID`
            - `SHAREPOINT_CLIENT_ID`
            - `SHAREPOINT_CLIENT_SECRET`
            """)
            if st.button("🔄 Retry Authentication"):
                # Clear auth cache and retry
                self.perf_optimizer.clear_cache("sharepoint_auth_status")
                st.session_state.sp_auth_checked = False
                self.perf_optimizer.smart_rerun()
            return
        
        st.success(f"✅ Connected to SharePoint (Tenant: {auth_status.get('tenant_id', 'Unknown')})")
        
        # Create tabs for different sections
        tab_select, tab_schedule, tab_reports = st.tabs([
            "📁 Select Folders", 
            "⏰ Scheduling", 
            "📊 Reports"
        ])
        
        with tab_select:
            self.render_folder_selection()
        
        with tab_schedule:
            self.render_scheduling()
        
        with tab_reports:
            self.render_reports()
    
    def render_folder_selection(self):
        """Render folder selection interface"""
        st.subheader("📁 SharePoint Folder Selection")
        
        # Site and drive selection
        col1, col2 = st.columns(2)
        
        with col1:
            site_domain = st.text_input(
                "Site Domain", 
                value=st.session_state.get('sp_site_domain', ''),
                placeholder="contoso.sharepoint.com",
                help="The SharePoint site domain"
            )
            st.session_state.sp_site_domain = site_domain
        
        with col2:
            site_name = st.text_input(
                "Site Name", 
                value=st.session_state.get('sp_site_name', ''),
                placeholder="sites/TeamSite",
                help="The SharePoint site name"
            )
            st.session_state.sp_site_name = site_name
        
        if not site_domain or not site_name:
            st.info("Please enter both site domain and site name to continue.")
            return
        
        # Get drives/libraries with caching
        with st.spinner("Loading SharePoint drives..."):
            drives = self.perf_optimizer.cache_expensive_operation(
                f"sharepoint_drives_{site_domain}_{site_name}",
                self.manager.get_sharepoint_drives,
                site_domain, site_name
            )
        
        if not drives:
            st.warning("No drives found. Please check your site domain and name.")
            return
        
        # Drive selection
        drive_options = {drive['name']: drive['id'] for drive in drives}
        selected_drive_name = st.selectbox(
            "📚 Select Document Library/Drive",
            options=list(drive_options.keys()),
            help="Choose the document library to browse"
        )
        
        if not selected_drive_name:
            return
        
        st.session_state.sp_drive_name = selected_drive_name
        
        # File type selection
        st.subheader("📄 File Types to Index")
        file_types = st.multiselect(
            "Select file types to include",
            options=[".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".txt", ".md"],
            default=[".pdf", ".docx", ".pptx"],
            help="Choose which file types to include in indexing"
        )
        
        # Index selection
        if 'selected_index' not in st.session_state or not st.session_state.selected_index:
            st.warning("⚠️ Please select a search index in the 'Manage Index' tab first.")
            return
        
        st.info(f"📂 Target Index: **{st.session_state.selected_index}**")
        
        # Folder tree
        st.subheader("🌲 Ultra-Fast Folder Tree")
        st.markdown("Select folders for indexing. **File counts disabled for maximum speed.**")
        
        # Performance mode selector
        perf_mode = st.radio(
            "Performance Mode:",
            ["Ultra-Fast (No file counts)", "Standard (With file counts for selected)"],
            index=0,
            help="Ultra-Fast mode loads instantly but doesn't show file counts"
        )
        
        with st.container():
            # Use ultra-fast folder tree for maximum performance
            if perf_mode == "Ultra-Fast (No file counts)":
                try:
                    updated_folders = UltraFastSharePointUI.render_ultra_fast_folder_tree(
                        manager=self.manager,
                        site_domain=site_domain,
                        site_name=site_name,
                        drive_name=selected_drive_name,
                        selected_folders=st.session_state.sp_selected_folders
                    )
                    st.session_state.sp_selected_folders = updated_folders
                    
                except Exception as e:
                    st.error(f"Error loading ultra-fast folder tree: {e}")
                    logging.error(f"Ultra-fast folder tree error: {e}")
            
            else:
                # Standard mode with optimizations
                try:
                    updated_folders = optimized_folder_renderer.render_folder_tree_ultra_optimized(
                        site_domain=site_domain,
                        site_name=site_name,
                        drive_name=selected_drive_name,
                        selected_folders=st.session_state.sp_selected_folders,
                        folder_manager=self.manager
                    )
                    st.session_state.sp_selected_folders = updated_folders
                    
                except Exception as e:
                    st.error(f"Error loading optimized folder tree: {e}")
                    logging.error(f"Optimized folder tree error: {e}")
                    
                    # Final fallback to original
                    try:
                        updated_folders = self.manager.render_folder_tree(
                            site_domain=site_domain,
                            site_name=site_name,
                            drive_name=selected_drive_name,
                            selected_folders=st.session_state.sp_selected_folders
                        )
                        st.session_state.sp_selected_folders = updated_folders
                    except Exception as fallback_error:
                        st.error(f"All folder tree methods failed: {fallback_error}")
                        logging.error(f"All folder tree methods failed: {fallback_error}")
        
        # Show selected folders with cached info
        if st.session_state.sp_selected_folders:
            st.subheader("✅ Selected Folders")
            
            # Show selected folder names first (fast)
            for i, folder_key in enumerate(st.session_state.sp_selected_folders):
                parts = folder_key.split('|', 3)
                if len(parts) == 4:
                    folder_path = parts[3]
                    st.write(f"📁 {folder_path}")
            
            # Option to get file counts on demand
            if perf_mode == "Ultra-Fast (No file counts)":
                if st.button("📊 Get File Counts for Selected Folders", help="This will take some time"):
                    file_counts = UltraFastSharePointUI.get_file_count_for_selected(
                        self.manager, st.session_state.sp_selected_folders
                    )
                    
                    st.success("File counts loaded!")
                    for folder_key, count in file_counts.items():
                        parts = folder_key.split('|', 3)
                        if len(parts) == 4:
                            folder_path = parts[3]
                            st.write(f"📁 {folder_path}: **{count} files**")
            else:
                # Cache folder info to avoid repeated API calls
                folder_info = self.perf_optimizer.cache_expensive_operation(
                    f"selected_folder_info_{hash(str(st.session_state.sp_selected_folders))}",
                    self.manager.get_selected_folder_info,
                    st.session_state.sp_selected_folders
                )
                
                for folder in folder_info:
                    st.write(f"📁 {folder['display_name']}")
            
            # Manual indexing button
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("🚀 Index Now", type="primary", use_container_width=True):
                    # Create simple folder info for indexing
                    folder_info = []
                    for folder_key in st.session_state.sp_selected_folders:
                        parts = folder_key.split('|', 3)
                        if len(parts) == 4:
                            folder_info.append({
                                'display_name': parts[3],
                                'folder_key': folder_key
                            })
                    self.run_manual_indexing(folder_info, file_types)
            
            with col2:
                if st.button("⏰ Create Schedule", use_container_width=True):
                    st.session_state.show_create_schedule = True
        else:
            st.info("Select folders from the tree above to enable indexing options.")
        
        # Create schedule modal
        if st.session_state.get('show_create_schedule', False):
            self.render_create_schedule_modal(file_types)
    
    def render_create_schedule_modal(self, file_types: List[str]):
        """Render the create schedule modal"""
        with st.container():
            st.subheader("⏰ Create Indexing Schedule")
            
            schedule_name = st.text_input(
                "Schedule Name",
                placeholder="My SharePoint Index Schedule",
                help="Give your schedule a descriptive name"
            )
            
            # Interval selection
            col1, col2 = st.columns(2)
            
            with col1:
                interval_type = st.selectbox(
                    "Interval Type",
                    options=["Minutes", "Hours"],
                    index=1
                )
            
            with col2:
                if interval_type == "Minutes":
                    interval_value = st.slider(
                        "Every X minutes",
                        min_value=1,
                        max_value=60,
                        value=5,
                        help="How often to run the indexing (1-60 minutes)"
                    )
                    interval_minutes = interval_value
                else:
                    interval_value = st.slider(
                        "Every X hours",
                        min_value=1,
                        max_value=24,
                        value=1,
                        help="How often to run the indexing (1-24 hours)"
                    )
                    interval_minutes = interval_value * 60
            
            # Buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Create Schedule", type="primary"):
                    if schedule_name:
                        schedule_id = self.scheduler.create_schedule(
                            name=schedule_name,
                            selected_folders=st.session_state.sp_selected_folders,
                            index_name=st.session_state.selected_index,
                            file_types=file_types,
                            interval_minutes=interval_minutes
                        )
                        st.success(f"Schedule '{schedule_name}' created successfully!")
                        st.session_state.show_create_schedule = False
                        self.perf_optimizer.smart_rerun()
                    else:
                        st.error("Please enter a schedule name.")
            
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.show_create_schedule = False
                    self.perf_optimizer.smart_rerun()
    
    def render_scheduling(self):
        """Render scheduling management interface"""
        st.subheader("⏰ Indexing Schedules")
        
        # Cleanup finished jobs
        self.scheduler.cleanup_finished_jobs()
        
        schedules = self.scheduler.get_all_schedules()
        
        if not schedules:
            st.info("No schedules created yet. Go to 'Select Folders' tab to create one.")
            return
        
        # Schedule management
        for schedule in schedules:
            status = self.scheduler.get_schedule_status(schedule.id)
            
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
                
                with col1:
                    running_icon = "🟢" if status['is_running'] else "🔴"
                    enabled_icon = "✅" if schedule.enabled else "⏸️"
                    st.write(f"{running_icon} {enabled_icon} **{schedule.name}**")
                    st.caption(f"Every {schedule.interval_minutes} minutes")
                
                with col2:
                    if schedule.last_run:
                        last_run = datetime.fromisoformat(schedule.last_run)
                        st.write(f"Last: {last_run.strftime('%H:%M')}")
                    else:
                        st.write("Never run")
                
                with col3:
                    if schedule.next_run and schedule.enabled:
                        next_run = datetime.fromisoformat(schedule.next_run)
                        st.write(f"Next: {next_run.strftime('%H:%M')}")
                    else:
                        st.write("Not scheduled")
                
                with col4:
                    button_col1, button_col2, button_col3, button_col4 = st.columns(4)
                    
                    with button_col1:
                        if st.button("▶️", key=f"start_{schedule.id}", help="Start schedule"):
                            if self.scheduler.start_schedule(schedule.id):
                                st.success("Schedule started!")
                                self.perf_optimizer.smart_rerun()
                            else:
                                st.error("Failed to start schedule")
                    
                    with button_col2:
                        if st.button("⏸️", key=f"stop_{schedule.id}", help="Stop schedule"):
                            self.scheduler.stop_schedule(schedule.id)
                            st.success("Schedule stopped!")
                            self.perf_optimizer.smart_rerun()
                    
                    with button_col3:
                        if st.button("🚀", key=f"run_now_{schedule.id}", help="Run now"):
                            if self.scheduler.run_schedule_now(schedule.id):
                                st.success("Manual run started!")
                            else:
                                st.error("Failed to start manual run")
                    
                    with button_col4:
                        if st.button("🗑️", key=f"delete_schedule_{schedule.id}", help="Delete schedule"):
                            self.scheduler.delete_schedule(schedule.id)
                            st.success("Schedule deleted!")
                            self.perf_optimizer.smart_rerun()
                
                # Show folder details
                with st.expander(f"📁 Folders in '{schedule.name}'", expanded=False):
                    folder_info = self.manager.get_selected_folder_info(schedule.selected_folders)
                    for folder in folder_info:
                        st.write(f"• {folder['display_name']}")
                
                st.divider()
    
    def render_reports(self):
        """Render reports interface"""
        st.subheader("📊 Indexing Reports")
        
        # Control buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🔄 Refresh Reports", use_container_width=True):
                # Force reload of reports from disk
                self.reports.load_reports()
                # Use session state to trigger refresh without full page reload
                if "ui_reports_refresh_counter" not in st.session_state:
                    st.session_state.ui_reports_refresh_counter = 0
                st.session_state.ui_reports_refresh_counter += 1
                st.success("Reports refreshed!", icon="✅")
        
        with col2:
            if st.button("🗑️ Delete All Reports", type="secondary", use_container_width=True):
                if st.session_state.get('confirm_delete_all', False):
                    # Execute the deletion
                    result = self.reports.delete_all_reports()
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                    else:
                        st.error(f"❌ {result['message']}")
                    st.session_state.confirm_delete_all = False
                    self.perf_optimizer.smart_rerun()
                else:
                    # Set confirmation flag
                    st.session_state.confirm_delete_all = True
                    self.perf_optimizer.smart_rerun()
        
        # Show confirmation dialog if needed
        if st.session_state.get('confirm_delete_all', False):
            with st.container():
                st.warning("⚠️ **Confirm Deletion**")
                st.write("Are you sure you want to delete ALL reports? This action cannot be undone.")
                
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Yes, Delete All", type="primary", use_container_width=True):
                        result = self.reports.delete_all_reports()
                        if result['success']:
                            st.success(f"✅ {result['message']}")
                        else:
                            st.error(f"❌ {result['message']}")
                        st.session_state.confirm_delete_all = False
                        self.perf_optimizer.smart_rerun()
                
                with col_no:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.confirm_delete_all = False
                        self.perf_optimizer.smart_rerun()
                
                st.divider()
        
        # Show statistics
        stats = self.reports.get_reports_stats()
        
        if stats['total_reports'] > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Reports", stats['total_reports'])
            
            with col2:
                success_rate = (stats['successful_reports'] / stats['total_reports'] * 100) if stats['total_reports'] > 0 else 0
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            with col3:
                st.metric("Files Processed", stats['total_files_processed'])
            
            with col4:
                st.metric("Chunks Created", stats['total_chunks_created'])
            
            st.divider()
        
        # Reports list
        self.reports.render_report_list(limit=20)
        
        # Cleanup option
        if stats['total_reports'] > 50:
            st.subheader("🧹 Cleanup")
            if st.button("🗑️ Keep only latest 50 reports"):
                self.reports.cleanup_old_reports(keep_count=50)
                st.success("Old reports cleaned up!")
                self.perf_optimizer.smart_rerun()
    
    def run_manual_indexing(self, folder_info: List[Dict[str, Any]], file_types: List[str]):
        """Run manual indexing operation"""
        start_time = time.time()
        
        with st.spinner("🔄 Indexing SharePoint folders..."):
            try:
                # Convert folder info back to folder keys
                folder_keys = []
                for folder in folder_info:
                    folder_key = f"{folder['site_domain']}|{folder['site_name']}|{folder['drive_name']}|{folder['folder_path']}"
                    folder_keys.append(folder_key)
                
                # Run indexing
                result = self.manager.index_selected_folders(
                    selected_folders=folder_keys,
                    index_name=st.session_state.selected_index,
                    file_types=file_types
                )
                
                duration = time.time() - start_time
                
                # Save report
                report_id = self.reports.save_report(
                    schedule_name="Manual Indexing",
                    folders=folder_keys,
                    result=result,
                    scheduled=False,
                    duration_seconds=duration
                )
                
                # Show results
                if result['success']:
                    st.success(f"✅ Indexing completed successfully in {duration:.1f} seconds!")
                    st.write(f"📊 **Summary:**")
                    st.write(f"• Folders processed: {result['folders_processed']}")
                    st.write(f"• Files processed: {result['total_processed']}")
                    st.write(f"• Chunks created: {result['total_chunks']}")
                    
                    if result['skipped_files']:
                        st.warning(f"⚠️ {len(result['skipped_files'])} files were skipped")
                else:
                    st.error("❌ Indexing failed!")
                    for error in result.get('errors', []):
                        st.error(error)
                
                # Link to detailed report
                st.info(f"📋 View detailed report in the 'Reports' tab")
                
            except Exception as e:
                st.error(f"❌ Indexing failed: {str(e)}")
                logging.error(f"Manual indexing failed: {e}")
