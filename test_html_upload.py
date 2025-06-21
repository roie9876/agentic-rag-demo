#!/usr/bin/env python3
"""
Test with more realistic HTML content that might be accepted by Document Intelligence
"""

import os
import requests
import logging
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_html_content():
    """Test with actual HTML content"""
    
    endpoint = "https://swedencentral.api.cognitive.microsoft.com"
    api_key = "0870c9b64d5548aeaaa579716c41cebf"
    api_version = "2024-11-30"
    
    # Test with actual HTML content
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Document</title>
</head>
<body>
    <h1>Sample Document</h1>
    <p>This is a test document with some meaningful content.</p>
    <p>It contains multiple paragraphs to see if Document Intelligence can process it.</p>
    <div>
        <h2>Section 2</h2>
        <p>More content here with some <strong>bold text</strong> and <em>italic text</em>.</p>
    </div>
</body>
</html>"""
    
    test_filename = "test_document.html"
    
    print(f"Testing Document Intelligence with HTML content")
    print(f"File size: {len(html_content.encode())} bytes")
    print()
    
    # Test with text/html content-type
    print("🔄 Test 1: HTML content with text/html content-type")
    test_upload(endpoint, api_key, api_version, html_content.encode(), test_filename, "text/html")
    print()
    
    # Test the same content but with .pdf extension (like what user described)
    print("🔄 Test 2: HTML content with .pdf extension and application/pdf content-type")
    test_upload(endpoint, api_key, api_version, html_content.encode(), "test_document.pdf", "application/pdf")
    print()
    
    # Test with multipart
    print("🔄 Test 3: HTML content with .pdf extension using multipart upload")
    test_multipart_upload(endpoint, api_key, api_version, html_content.encode(), "test_document.pdf", "text/html")

def test_upload(endpoint, api_key, api_version, file_bytes, filename, content_type):
    """Test raw binary upload"""
    
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
            operation_location = response.headers.get("Operation-Location")
            if operation_location:
                print(f"   Operation Location: {operation_location}")
        else:
            print("   ❌ Upload failed")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

def test_multipart_upload(endpoint, api_key, api_version, file_bytes, filename, content_type):
    """Test multipart form-data upload"""
    
    url = f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version={api_version}"
    
    # Prepare multipart form data
    files = {
        'file': (filename, BytesIO(file_bytes), content_type)
    }
    
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "x-ms-useragent": "gpt-rag/1.0.0"
    }
    
    try:
        response = requests.post(url, headers=headers, files=files)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 202:
            print("   ✅ Upload successful")
            operation_location = response.headers.get("Operation-Location")
            if operation_location:
                print(f"   Operation Location: {operation_location}")
        else:
            print("   ❌ Upload failed")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_html_content()
