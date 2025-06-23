"""
Ultra-Fast SharePoint UI
Minimal, high-performance SharePoint folder selection interface
"""

import streamlit as st
from typing import List, Dict, Any
import logging


class UltraFastSharePointUI:
    """Ultra-fast SharePoint UI with minimal overhead"""
    
    @staticmethod
    def render_ultra_fast_folder_tree(manager, site_domain: str, site_name: str, 
                                     drive_name: str, selected_folders: List[str]) -> List[str]:
        """Ultra-fast folder tree rendering with minimal refreshes"""
        
        # Use simple session state management
        if 'fast_expanded' not in st.session_state:
            st.session_state.fast_expanded = set()
        
        if 'fast_selected' not in st.session_state:
            st.session_state.fast_selected = set(selected_folders)
        
        # Performance warning
        st.info("🚀 **Ultra-Fast Mode**: File counts disabled for maximum speed. Only folder names shown.")
        
        try:
            # Get root folders only
            root_folders = manager.get_folder_tree(site_domain, site_name, drive_name, "/")
            
            if not root_folders:
                st.warning("No folders found or unable to access SharePoint")
                return list(st.session_state.fast_selected)
            
            # Render folder tree with minimal UI
            UltraFastSharePointUI._render_folder_level(
                root_folders, site_domain, site_name, drive_name, manager, 0
            )
            
            return list(st.session_state.fast_selected)
            
        except Exception as e:
            st.error(f"Error loading folders: {str(e)}")
            logging.error(f"Ultra-fast folder tree error: {e}")
            return list(st.session_state.fast_selected)
    
    @staticmethod
    def _render_folder_level(folders: List[Dict], site_domain: str, site_name: str, 
                           drive_name: str, manager, level: int, max_level: int = 3):
        """Render a single folder level with minimal overhead"""
        
        if level > max_level:  # Prevent infinite expansion
            return
        
        for folder in folders:
            folder_key = f"{site_domain}|{site_name}|{drive_name}|{folder['path']}"
            is_selected = folder_key in st.session_state.fast_selected
            expand_key = f"{site_domain}_{site_name}_{drive_name}_{folder['path']}"
            is_expanded = expand_key in st.session_state.fast_expanded
            
            # Create simple layout
            col1, col2, col3 = st.columns([0.1, 0.1, 0.8])
            
            # Selection checkbox
            with col1:
                checkbox_key = f"ultrafast_{folder['id']}_{level}"
                if st.checkbox("", value=is_selected, key=checkbox_key, label_visibility="collapsed"):
                    st.session_state.fast_selected.add(folder_key)
                else:
                    st.session_state.fast_selected.discard(folder_key)
            
            # Expand button (minimal logic)
            with col2:
                if folder.get('hasChildren', True):  # Assume all folders have children
                    expand_symbol = "➖" if is_expanded else "➕"
                    expand_button_key = f"ultrafast_exp_{folder['id']}_{level}"
                    
                    if st.button(expand_symbol, key=expand_button_key, help="Expand"):
                        if is_expanded:
                            st.session_state.fast_expanded.discard(expand_key)
                        else:
                            st.session_state.fast_expanded.add(expand_key)
                        st.rerun()
                else:
                    st.write("📄")
            
            # Folder name (super simple)
            with col3:
                indent = "　" * level
                folder_display = f"{indent}📁 {folder['name']}"
                
                # Only show file count if specifically selected and requested
                if is_selected:
                    folder_display += " ✅"  # Just show selected indicator
                
                st.write(folder_display)
            
            # Load subfolders if expanded (lazy loading)
            if is_expanded and folder.get('hasChildren', True) and level < max_level:
                try:
                    subfolders = manager.get_folder_tree(
                        site_domain, site_name, drive_name, folder['path']
                    )
                    if subfolders:
                        UltraFastSharePointUI._render_folder_level(
                            subfolders, site_domain, site_name, drive_name, 
                            manager, level + 1, max_level
                        )
                except Exception as e:
                    st.error(f"Error loading subfolders: {str(e)}")
    
    @staticmethod
    def get_file_count_for_selected(manager, selected_folders: List[str]) -> Dict[str, int]:
        """Get file counts only for selected folders (on demand)"""
        file_counts = {}
        
        if not selected_folders:
            return file_counts
        
        st.info("📊 Getting file counts for selected folders...")
        progress_bar = st.progress(0)
        
        for i, folder_key in enumerate(selected_folders):
            try:
                # Parse folder key
                parts = folder_key.split('|', 3)
                if len(parts) == 4:
                    site_domain, site_name, drive_name, folder_path = parts
                    
                    # Get files count (this is the expensive operation)
                    files = manager.get_files_from_folder(
                        site_domain, site_name, drive_name, folder_path
                    )
                    file_counts[folder_key] = len(files) if files else 0
                
                # Update progress
                progress_bar.progress((i + 1) / len(selected_folders))
                
            except Exception as e:
                logging.error(f"Error getting file count for {folder_key}: {e}")
                file_counts[folder_key] = 0
        
        progress_bar.empty()
        return file_counts
