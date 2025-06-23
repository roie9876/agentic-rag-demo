"""
UI Performance Optimizer for SharePoint Indexing
Optimizes Streamlit UI performance by reducing unnecessary refreshes and improving state management
"""

import streamlit as st
import time
import logging
from typing import Dict, Any, List, Optional
from functools import wraps
import hashlib


class UIPerformanceOptimizer:
    """Optimizes Streamlit UI performance for SharePoint operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._init_performance_state()
    
    def _init_performance_state(self):
        """Initialize performance tracking state"""
        if 'ui_perf_cache' not in st.session_state:
            st.session_state.ui_perf_cache = {}
        if 'ui_perf_stats' not in st.session_state:
            st.session_state.ui_perf_stats = {
                'page_loads': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'load_times': []
            }
    
    def cache_expensive_operation(self, cache_key: str, operation_func, *args, **kwargs):
        """Cache expensive operations to avoid repeated calculations"""
        # Create a hash of the arguments for cache invalidation
        arg_hash = hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()
        full_cache_key = f"{cache_key}_{arg_hash}"
        
        if full_cache_key in st.session_state.ui_perf_cache:
            st.session_state.ui_perf_stats['cache_hits'] += 1
            self.logger.debug(f"Cache hit for {cache_key}")
            return st.session_state.ui_perf_cache[full_cache_key]
        
        # Cache miss - execute operation
        st.session_state.ui_perf_stats['cache_misses'] += 1
        self.logger.debug(f"Cache miss for {cache_key}")
        
        start_time = time.time()
        result = operation_func(*args, **kwargs)
        end_time = time.time()
        
        # Store in cache
        st.session_state.ui_perf_cache[full_cache_key] = result
        st.session_state.ui_perf_stats['load_times'].append(end_time - start_time)
        
        return result
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache entries, optionally matching a pattern"""
        if pattern:
            keys_to_remove = [k for k in st.session_state.ui_perf_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del st.session_state.ui_perf_cache[key]
            self.logger.info(f"Cleared {len(keys_to_remove)} cache entries matching '{pattern}'")
        else:
            st.session_state.ui_perf_cache.clear()
            self.logger.info("Cleared all cache entries")
    
    def smart_rerun(self, condition: bool = True, delay: float = 0.1):
        """Smart rerun that only triggers when necessary and with debouncing"""
        if not condition:
            return
        
        # Debouncing: prevent rapid successive reruns
        current_time = time.time()
        last_rerun_key = 'last_smart_rerun'
        
        if last_rerun_key in st.session_state:
            time_since_last = current_time - st.session_state[last_rerun_key]
            if time_since_last < delay:
                self.logger.debug(f"Debounced rerun (last: {time_since_last:.2f}s ago)")
                return
        
        st.session_state[last_rerun_key] = current_time
        st.rerun()
    
    def with_performance_monitoring(self, operation_name: str):
        """Decorator to monitor performance of UI operations"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    if duration > 1.0:  # Log slow operations
                        self.logger.warning(f"Slow UI operation '{operation_name}': {duration:.2f}s")
                    
                    return result
                except Exception as e:
                    self.logger.error(f"Error in UI operation '{operation_name}': {e}")
                    raise
            return wrapper
        return decorator
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        stats = st.session_state.ui_perf_stats.copy()
        if stats['load_times']:
            stats['avg_load_time'] = sum(stats['load_times']) / len(stats['load_times'])
            stats['max_load_time'] = max(stats['load_times'])
        else:
            stats['avg_load_time'] = 0
            stats['max_load_time'] = 0
        
        stats['cache_size'] = len(st.session_state.ui_perf_cache)
        stats['cache_hit_rate'] = (
            stats['cache_hits'] / max(1, stats['cache_hits'] + stats['cache_misses'])
        )
        
        return stats
    
    def render_performance_debug(self):
        """Render performance debugging information"""
        if st.checkbox("🔧 Show Performance Debug", value=False):
            stats = self.get_performance_stats()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Cache Hit Rate", f"{stats['cache_hit_rate']:.1%}")
            with col2:
                st.metric("Avg Load Time", f"{stats['avg_load_time']:.2f}s")
            with col3:
                st.metric("Cache Size", stats['cache_size'])
            
            if st.button("Clear Performance Cache"):
                self.clear_cache()
                st.success("Performance cache cleared")
                self.smart_rerun()


class OptimizedFolderTreeRenderer:
    """Optimized folder tree rendering with minimal refreshes"""
    
    def __init__(self, performance_optimizer: UIPerformanceOptimizer):
        self.perf = performance_optimizer
        self.logger = logging.getLogger(__name__)
    
    def render_folder_tree_ultra_optimized(self, site_domain: str, site_name: str, 
                                          drive_name: str, selected_folders: List[str],
                                          folder_manager) -> List[str]:
        """Ultra-optimized folder tree with minimal refreshes and smart caching"""
        
        # Create unique cache key for this tree
        tree_cache_key = f"folder_tree_{site_domain}_{site_name}_{drive_name}"
        
        # Initialize expansion state more efficiently
        expansion_key = f"sp_expanded_{site_domain}_{site_name}_{drive_name}"
        if expansion_key not in st.session_state:
            st.session_state[expansion_key] = set()
        
        # Track selection changes to minimize reruns
        selection_key = f"sp_selection_{site_domain}_{site_name}_{drive_name}"
        if selection_key not in st.session_state:
            st.session_state[selection_key] = set(selected_folders)
        
        updated_selected = list(st.session_state[selection_key])
        
        # Use performance-optimized container
        with st.container():
            st.info("🚀 Optimized folder tree - selections update without page refresh")
            
            # Cache folder structure
            @self.perf.with_performance_monitoring("folder_tree_load")
            def load_folder_structure():
                return folder_manager.get_folder_tree(site_domain, site_name, drive_name, "/")
            
            folders = self.perf.cache_expensive_operation(
                tree_cache_key, 
                load_folder_structure
            )
            
            if not folders:
                st.info("No folders found or unable to access SharePoint")
                return updated_selected
            
            # Render with minimal refresh strategy
            self._render_optimized_level(
                folders, site_domain, site_name, drive_name, 
                updated_selected, 0, folder_manager
            )
        
        return updated_selected
    
    def _render_optimized_level(self, folders: List[Dict], site_domain: str, 
                               site_name: str, drive_name: str, 
                               selected_folders: List[str], level: int, 
                               folder_manager, max_depth: int = 2):
        """Render folder level with optimization"""
        
        expansion_key = f"sp_expanded_{site_domain}_{site_name}_{drive_name}"
        selection_key = f"sp_selection_{site_domain}_{site_name}_{drive_name}"
        
        # Use form to batch updates and reduce refreshes
        with st.form(f"folder_form_level_{level}_{hash(str(folders))}", clear_on_submit=False):
            folder_updates = {}
            expansion_updates = {}
            
            for i, folder in enumerate(folders):
                folder_key = f"{site_domain}|{site_name}|{drive_name}|{folder['path']}"
                is_selected = folder_key in selected_folders
                expand_key = f"{folder['path']}"
                is_expanded = expand_key in st.session_state[expansion_key]
                
                # Layout columns
                col1, col2, col3 = st.columns([0.08, 0.08, 0.84])
                
                # Selection checkbox
                with col1:
                    checkbox_key = f"opt_folder_{folder['id']}_{level}_{i}"
                    new_selection = st.checkbox(
                        "Select", 
                        value=is_selected, 
                        key=checkbox_key,
                        label_visibility="collapsed"
                    )
                    folder_updates[folder_key] = new_selection
                
                # Expand button
                with col2:
                    if folder['hasChildren'] and level < max_depth:
                        expand_symbol = "➖" if is_expanded else "➕"
                        expand_button_key = f"opt_expand_{folder['id']}_{level}_{i}"
                        if st.form_submit_button(
                            expand_symbol, 
                            help="Expand/collapse"
                        ):
                            expansion_updates[expand_key] = not is_expanded
                
                # Folder display
                with col3:
                    indent = "　" * level
                    display_name = f"{indent}📁 {folder['name']}"
                    
                    # Only show counts for selected folders
                    if is_selected and 'childCount' in folder and folder['childCount'] > 0:
                        display_name += f" ({folder['childCount']} items)"
                    
                    st.write(display_name)
            
            # Submit button for batched updates
            if st.form_submit_button("🔄 Update Selections", type="primary"):
                # Update selections
                new_selection_set = set()
                for folder_key, is_selected in folder_updates.items():
                    if is_selected:
                        new_selection_set.add(folder_key)
                
                st.session_state[selection_key] = new_selection_set
                
                # Update expansions
                for expand_key, should_expand in expansion_updates.items():
                    if should_expand:
                        st.session_state[expansion_key].add(expand_key)
                    else:
                        st.session_state[expansion_key].discard(expand_key)
                
                # Smart rerun with debouncing
                self.perf.smart_rerun(condition=bool(folder_updates or expansion_updates))
        
        # Render expanded subfolders (with caching)
        for folder in folders:
            expand_key = f"{folder['path']}"
            if (expand_key in st.session_state[expansion_key] and 
                folder['hasChildren'] and level < max_depth):
                
                subfolder_cache_key = f"subfolder_{site_domain}_{site_name}_{drive_name}_{folder['path']}"
                
                @self.perf.with_performance_monitoring("subfolder_load")
                def load_subfolders():
                    return folder_manager.get_folder_tree(
                        site_domain, site_name, drive_name, folder['path']
                    )
                
                subfolders = self.perf.cache_expensive_operation(
                    subfolder_cache_key,
                    load_subfolders
                )
                
                if subfolders:
                    self._render_optimized_level(
                        subfolders, site_domain, site_name, drive_name,
                        selected_folders, level + 1, folder_manager, max_depth
                    )


# Global performance optimizer instance
ui_perf_optimizer = UIPerformanceOptimizer()
optimized_folder_renderer = OptimizedFolderTreeRenderer(ui_perf_optimizer)
