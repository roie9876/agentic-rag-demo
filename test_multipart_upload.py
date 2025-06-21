#!/usr/bin/env python3
"""
Test script to compare different upload methods to Azure Document Intelligence:
1. Raw binary upload (current method)
2. Multipart form-data upload (like portal UI might use)
3. Force PDF content-type (user's suggestion)
"""

import os
import requests
import logging
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_file_upload_methods():
    """Test both raw binary and multipart form-data upload methods"""
    
    # Configuration - read directly from environment or use hardcoded values for testing
    endpoint = (
        os.getenv("DOCUMENT_INTEL_ENDPOINT") or 
        os.getenv("AZURE_FORMREC_ENDPOINT") or
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT") or
        "https://swedencentral.api.cognitive.microsoft.com"
    )
    
    api_key = (
        os.getenv("DOCUMENT_INTEL_KEY") or 
        os.getenv("AZURE_FORMREC_KEY") or
        os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY") or
        "0870c9b64d5548aeaaa579716c41cebf"
    )
    
    api_version = "2024-11-30"
    
    if not endpoint or not api_key:
        print("❌ Missing Azure Document Intelligence endpoint or API key")
        return
    
    endpoint = endpoint.rstrip("/")
    
    # Test with a small "problematic" PDF (actually plain text)
    test_content = "This is just plain text content masquerading as a PDF file."
    test_filename = "test_small.pdf"
    
    print(f"Testing Document Intelligence uploads with {test_filename}")
    print(f"Content: {test_content}")
    print(f"File size: {len(test_content.encode())} bytes")
    print(f"Endpoint: {endpoint}")
    print()
    
    # Test 1: Raw binary upload with PDF content-type (user's suggestion!)
    print("🔄 Test 1: Raw binary upload with application/pdf content-type (FORCE PDF)")
    test_raw_binary_upload(endpoint, api_key, api_version, test_content.encode(), test_filename, "application/pdf")
    print()
    
    # Test 2: Multipart form-data upload with PDF content-type
    print("🔄 Test 2: Multipart form-data upload with application/pdf content-type (FORCE PDF)")
    test_multipart_upload(endpoint, api_key, api_version, test_content.encode(), test_filename, "application/pdf")
    print()
    
    # Test 3: Raw binary upload (current method) with detected content-type
    print("🔄 Test 3: Raw binary upload with text/plain content-type (detected)")
    test_raw_binary_upload(endpoint, api_key, api_version, test_content.encode(), test_filename, "text/plain")
    print()
    
    # Test 4: Try as HTML content type
    print("🔄 Test 4: Raw binary upload with text/html content-type")
    test_raw_binary_upload(endpoint, api_key, api_version, test_content.encode(), test_filename, "text/html")
    print()
    
    # Test 5: Multipart as HTML
    print("🔄 Test 5: Multipart form-data upload with text/html content-type")
    test_multipart_upload(endpoint, api_key, api_version, test_content.encode(), test_filename, "text/html")
    print()
    
    # Test 6: Auto-detect with octet-stream
    print("🔄 Test 6: Raw binary upload with application/octet-stream (auto-detect)")
    test_raw_binary_upload(endpoint, api_key, api_version, test_content.encode(), test_filename, "application/octet-stream")


def test_raw_binary_upload(endpoint, api_key, api_version, file_bytes, filename, content_type):
    """Test raw binary upload (current method)"""
    
    url = f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version={api_version}"
    
    headers = {
        "Content-Type": content_type,
        "Ocp-Apim-Subscription-Key": api_key,
        "x-ms-useragent": "gpt-rag/1.0.0"
    }
    
    try:
        response = requests.post(url, headers=headers, data=file_bytes)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 202:
            print("   ✅ Upload successful")
        else:
            print("   ❌ Upload failed")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")


def test_multipart_upload(endpoint, api_key, api_version, file_bytes, filename, content_type):
    """Test multipart form-data upload (like portal UI might use)"""
    
    url = f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version={api_version}"
    
    # Prepare multipart form data
    files = {
        'file': (filename, BytesIO(file_bytes), content_type)
    }
    
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "x-ms-useragent": "gpt-rag/1.0.0"
        # Don't set Content-Type header - let requests handle multipart boundary
    }
    
    try:
        response = requests.post(url, headers=headers, files=files)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 202:
            print("   ✅ Upload successful")
        else:
            print("   ❌ Upload failed")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    test_file_upload_methods()
