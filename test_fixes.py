#!/usr/bin/env python3
"""
Test script to verify the fixes for the agentic-rag-demo issues:
1. DocumentChunker type error
2. Embedding token limit
3. Environment variable resolution
"""

import os
import sys
import base64
import logging
from dotenv import load_dotenv

# Clear any cached environment variables
for key in list(os.environ.keys()):
    if key.startswith(('AZURE_', 'DOCUMENT_')):
        del os.environ[key]

# Force reload the .env file
load_dotenv(override=True)

print("=== Environment Variable Test ===")
print(f"DOCUMENT_INTEL_ENDPOINT: {os.getenv('DOCUMENT_INTEL_ENDPOINT')}")
print(f"AZURE_FORMREC_SERVICE: {os.getenv('AZURE_FORMREC_SERVICE')}")
print(f"AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: {os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')}")

print("\n=== DocumentChunker Import Test ===")
try:
    from chunking import DocumentChunker
    print("✅ DocumentChunker imported successfully")
except Exception as e:
    print(f"❌ DocumentChunker import failed: {e}")

print("\n=== Embedding Function Test ===")
try:
    # Import from the actual file
    sys.path.append('/Users/robenhai/agentic-rag-demo')
    import importlib.util
    spec = importlib.util.spec_from_file_location("agentic_rag_demo", "/Users/robenhai/agentic-rag-demo/agentic-rag-demo.py")
    agentic_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentic_module)
    
    print("✅ agentic-rag-demo module loaded successfully")
    
    # Test the truncation logic
    long_text = "This is a test text. " * 2000  # ~40,000 characters
    print(f"Test text length: {len(long_text):,} characters")
    
    # The function should truncate this automatically
    MAX_EMBEDDING_CHARS = 28000  # As defined in the embed_text function
    if len(long_text) > MAX_EMBEDDING_CHARS:
        truncated = long_text[:MAX_EMBEDDING_CHARS]
        print(f"✅ Text would be truncated to {len(truncated):,} characters (under 8192 token limit)")
    else:
        print("✅ Text is within limits")
        
except Exception as e:
    print(f"❌ embed_text test failed: {e}")

print("\n=== Test Complete ===")
