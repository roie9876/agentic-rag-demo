#!/usr/bin/env python3
"""
Diagnostic version of the Streamlit app to identify initialization issues
"""

import streamlit as st
import os
import traceback

def safe_init_test():
    """Test each initialization step safely"""
    results = {}
    
    # Test 1: Basic imports
    try:
        from health_check import HealthCheckUI
        results['health_check_import'] = "✅ SUCCESS"
    except Exception as e:
        results['health_check_import'] = f"❌ FAILED: {e}"
    
    # Test 2: init_openai function
    try:
        import sys
        sys.path.append('/home/azureuser/agentic-rag-demo')
        from agentic_rag_demo import init_openai
        oai_client, chat_params = init_openai("41")
        results['init_openai'] = "✅ SUCCESS"
    except Exception as e:
        results['init_openai'] = f"❌ FAILED: {e}"
    
    # Test 3: rbac_enabled function
    try:
        from agentic_rag_demo import rbac_enabled, env
        rbac_flag = rbac_enabled(env("AZURE_SEARCH_ENDPOINT"))
        results['rbac_check'] = f"✅ SUCCESS: RBAC = {rbac_flag}"
    except Exception as e:
        results['rbac_check'] = f"❌ FAILED: {e}"
    
    # Test 4: init_search_client function
    try:
        from agentic_rag_demo import init_search_client
        _, root_index_client = init_search_client()
        results['search_client'] = "✅ SUCCESS"
    except Exception as e:
        results['search_client'] = f"❌ FAILED: {e}"
    
    return results

def main():
    st.set_page_config(page_title="Diagnostic Test", page_icon="🔧", layout="wide")
    
    st.title("🔧 Streamlit App Diagnostic Test")
    
    st.header("Initialization Tests")
    
    if st.button("🔍 Run Diagnostic Tests"):
        with st.spinner("Running tests..."):
            results = safe_init_test()
        
        for test_name, result in results.items():
            if "SUCCESS" in result:
                st.success(f"**{test_name}**: {result}")
            else:
                st.error(f"**{test_name}**: {result}")
    
    st.header("Test Tabs")
    
    # Test if tabs work when initialization functions are skipped
    tab1, tab2, tab3 = st.tabs(["🩺 Health Check", "✅ Test Tab", "🔧 Debug"])
    
    with tab1:
        st.write("Health Check tab content")
        try:
            from health_check import HealthCheckUI
            health_ui = HealthCheckUI()
            health_ui.render_health_check_tab()
        except Exception as e:
            st.error(f"Health Check UI failed: {e}")
            st.code(traceback.format_exc())
    
    with tab2:
        st.write("This is a test tab to verify tabs are working")
        st.success("✅ Tabs are loading correctly!")
    
    with tab3:
        st.write("Debug information:")
        st.write("Environment variables:")
        st.write({
            "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT", "Not set"),
            "AZURE_SEARCH_ENDPOINT": os.getenv("AZURE_SEARCH_ENDPOINT", "Not set"),
            "DOCUMENT_INTEL_ENDPOINT": os.getenv("DOCUMENT_INTEL_ENDPOINT", "Not set")
        })

if __name__ == "__main__":
    main()
