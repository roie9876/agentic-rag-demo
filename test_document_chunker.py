#!/usr/bin/env python3
"""
Test the DocumentChunker fix with a real PDF to ensure the type error is resolved.
"""

import os
import sys
import base64
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv(override=True)

# Add current directory to path
sys.path.append('/Users/robenhai/agentic-rag-demo')

try:
    from chunking import DocumentChunker
    print("✅ DocumentChunker imported successfully")
    
    # Test with a simple document structure that mimics the issue
    # The issue was that content["text"] contained dicts instead of strings
    test_data = {
        "fileName": "test_doc.pdf",
        "documentBytes": "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPD4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooSGVsbG8gV29ybGQhKSBUagpFVAplbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAwOSAwMDAwMCBuIAowMDAwMDAwMDU4IDAwMDAwIG4gCjAwMDAwMDAxMTUgMDAwMDAgbiAKMDAwMDAwMDIwNyAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjMwMQolJUVPRg==",
        "documentUrl": ""
    }
    
    print(f"Testing DocumentChunker with test data...")
    
    # Create chunker instance
    dc = DocumentChunker(multimodal=False, openai_client=None)
    
    # Test the chunking process
    chunks, errors, warnings = dc.chunk_documents(test_data)
    
    print(f"✅ DocumentChunker executed successfully!")
    print(f"   Chunks: {len(chunks)}")
    print(f"   Errors: {len(errors)}")
    print(f"   Warnings: {len(warnings)}")
    
    if errors:
        print("Error details:")
        for error in errors:
            print(f"   - {error}")
    
    if chunks:
        print("Sample chunk structure:")
        chunk = chunks[0]
        print(f"   Keys: {list(chunk.keys())}")
        if 'content' in chunk:
            content_type = type(chunk['content'])
            content_preview = str(chunk['content'])[:100] + "..." if len(str(chunk['content'])) > 100 else str(chunk['content'])
            print(f"   Content type: {content_type}")
            print(f"   Content preview: {content_preview}")
    
    print("\n=== DocumentChunker Fix Test Complete ===")
    
except Exception as e:
    print(f"❌ DocumentChunker test failed: {e}")
    import traceback
    traceback.print_exc()
