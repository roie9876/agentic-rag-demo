#!/usr/bin/env python3
"""
Simple UI test to isolate performance issues
"""
import streamlit as st
import os
from pathlib import Path

# Load basic environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

def main():
    st.set_page_config(page_title="Simple Test", page_icon="🧪", layout="wide")
    st.title("🧪 Simple UI Test")
    
    # Test basic functionality
    tab1, tab2, tab3 = st.tabs(["Basic", "Environment", "Files"])
    
    with tab1:
        st.header("Basic Test")
        st.write("If you can see this, basic Streamlit is working!")
        
        name = st.text_input("Enter your name")
        if name:
            st.success(f"Hello, {name}!")
    
    with tab2:
        st.header("Environment Variables")
        env_vars = ["AZURE_SEARCH_ENDPOINT", "AZURE_OPENAI_ENDPOINT_41", "INDEX_NAME"]
        for var in env_vars:
            value = os.getenv(var, "Not set")
            st.write(f"**{var}:** {value[:50]}{'...' if len(value) > 50 else ''}")
    
    with tab3:
        st.header("File System")
        current_dir = Path.cwd()
        st.write(f"**Current directory:** {current_dir}")
        
        # List some key files
        key_files = ["agentic-rag-demo.py", ".env", "requirements.txt"]
        for file in key_files:
            file_path = current_dir / file
            exists = "✅" if file_path.exists() else "❌"
            st.write(f"{exists} {file}")

if __name__ == "__main__":
    main()
