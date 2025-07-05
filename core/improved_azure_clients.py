"""
Improved Azure Search Client Management
-------------------------------------
This shows how the search client should be initialized efficiently.
"""

import streamlit as st
from typing import Tuple, Optional
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

def get_search_client_cached() -> Tuple[Optional[SearchClient], Optional[SearchIndexClient]]:
    """
    Get cached search clients or create them if needed.
    Only initializes when actually needed, not on every page load.
    """
    # Check if clients are already cached in session state
    if 'search_clients_initialized' in st.session_state:
        return (
            st.session_state.get('root_search_client'),
            st.session_state.get('root_index_client')
        )
    
    try:
        # Only initialize when actually needed
        from core.azure_clients import init_search_client_lightweight
        search_client, index_client = init_search_client_lightweight()
        
        # Cache in session state
        st.session_state.root_search_client = search_client
        st.session_state.root_index_client = index_client
        st.session_state.search_clients_initialized = True
        
        return search_client, index_client
        
    except Exception as e:
        # Don't fail the entire app if search is unavailable
        st.session_state.search_client_error = str(e)
        return None, None

def get_available_indexes() -> list:
    """
    Get available indexes, only when explicitly requested.
    Uses caching to avoid repeated API calls.
    """
    # Check cache first
    if 'available_indexes' in st.session_state and 'indexes_last_fetched' in st.session_state:
        # Cache for 5 minutes
        import time
        if time.time() - st.session_state.indexes_last_fetched < 300:
            return st.session_state.available_indexes
    
    # Get client
    _, index_client = get_search_client_cached()
    if not index_client:
        return []
    
    try:
        # Only make API call when needed
        indexes = list(index_client.list_indexes())
        index_names = [idx.name for idx in indexes]
        
        # Cache results
        st.session_state.available_indexes = index_names
        st.session_state.indexes_last_fetched = time.time()
        
        return index_names
        
    except Exception as e:
        st.error(f"Failed to load indexes: {e}")
        return st.session_state.get('available_indexes', [])

def init_search_client_lightweight(index_name: str | None = None) -> Tuple[SearchClient, SearchIndexClient]:
    """
    Initialize search clients WITHOUT making any API calls.
    This is fast and doesn't depend on network connectivity.
    """
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not endpoint:
        raise ValueError("Missing required environment variable: AZURE_SEARCH_ENDPOINT")
        
    credential = get_search_credential()
    
    # Create clients but DON'T make any API calls yet
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    
    if index_name:
        search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    else:
        search_client = SearchClient(endpoint=endpoint, index_name="dummy", credential=credential)
    
    # NO API CALLS HERE - just return the configured clients
    return search_client, index_client
