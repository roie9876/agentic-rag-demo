#!/usr/bin/env python3
"""
Minimal test to debug tab issues
"""
import streamlit as st

def main():
    st.set_page_config(page_title="Tab Test", page_icon="🧪", layout="wide")
    st.title("🧪 Tab Loading Test")
    
    # Simple message
    st.write("This is before the tabs")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])
    
    with tab1:
        st.header("Tab 1 Content")
        st.write("This is tab 1")
    
    with tab2:
        st.header("Tab 2 Content")
        st.write("This is tab 2")
        
    with tab3:
        st.header("Tab 3 Content")
        st.write("This is tab 3")
    
    st.write("This is after the tabs")

if __name__ == "__main__":
    main()
