#!/usr/bin/env python3
"""
Test Document Intelligence with different request body formats.
Some services prefer multipart/form-data over raw binary data.
"""

import os
import sys
import requests
from pathlib import Path

def test_multipart_format(file_path, endpoint, api_key):
    """Test using multipart/form-data format like a web form upload."""
    print("📤 Testing multipart/form-data format")
    print("=" * 40)
    
    filename = Path(file_path).name
    print(f"📁 File: {filename}")
    
    url = f"{endpoint.rstrip('/')}/documentintelligence/documentModels/prebuilt-layout:analyze"
    params = {
        'api-version': '2024-11-30',
        'outputContentFormat': 'markdown',
        'output': 'figures'
    }
    
    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'Accept': 'application/json'
        # Don't set Content-Type - let requests handle it for multipart
    }
    
    # Open file for multipart upload
    with open(file_path, 'rb') as f:
        files = {
            'file': (filename, f, 'application/pdf')
        }
        
        try:
            response = requests.post(url, params=params, headers=headers, files=files, timeout=30)
            
            print(f"📊 Status: {response.status_code}")
            if response.status_code == 202:
                print("✅ Multipart format SUCCESS!")
            else:
                print(f"❌ Failed: {response.text[:150]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

def test_form_data_format(file_path, endpoint, api_key):
    """Test using application/x-www-form-urlencoded with base64."""
    print("\n📋 Testing form-encoded format")
    print("=" * 40)
    
    import base64
    
    filename = Path(file_path).name
    print(f"📁 File: {filename}")
    
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    
    # Base64 encode the file
    file_b64 = base64.b64encode(file_bytes).decode('utf-8')
    
    url = f"{endpoint.rstrip('/')}/documentintelligence/documentModels/prebuilt-layout:analyze"
    params = {
        'api-version': '2024-11-30'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Ocp-Apim-Subscription-Key': api_key,
        'Accept': 'application/json'
    }
    
    # Form data with base64 encoded file
    data = f"file={file_b64}&filename={filename}"
    
    try:
        response = requests.post(url, params=params, headers=headers, data=data, timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        if response.status_code == 202:
            print("✅ Form-encoded format SUCCESS!")
        else:
            print(f"❌ Failed: {response.text[:150]}...")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_json_format(file_path, endpoint, api_key):
    """Test using JSON format with base64 encoded content."""
    print("\n📄 Testing JSON format")
    print("=" * 40)
    
    import base64
    import json
    
    filename = Path(file_path).name
    print(f"📁 File: {filename}")
    
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    
    # Base64 encode the file
    file_b64 = base64.b64encode(file_bytes).decode('utf-8')
    
    url = f"{endpoint.rstrip('/')}/documentintelligence/documentModels/prebuilt-layout:analyze"
    params = {
        'api-version': '2024-11-30'
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': api_key,
        'Accept': 'application/json'
    }
    
    # JSON payload
    payload = {
        'base64Source': file_b64
    }
    
    try:
        response = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        if response.status_code == 202:
            print("✅ JSON format SUCCESS!")
        else:
            print(f"❌ Failed: {response.text[:150]}...")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_url_format(file_path, endpoint, api_key, blob_url=None):
    """Test using URL format (if file is accessible via URL)."""
    print("\n🌐 Testing URL format")
    print("=" * 40)
    
    if not blob_url:
        print("⏭️  Skipping URL format test (no URL provided)")
        return
    
    url = f"{endpoint.rstrip('/')}/documentintelligence/documentModels/prebuilt-layout:analyze"
    params = {
        'api-version': '2024-11-30'
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': api_key,
        'Accept': 'application/json'
    }
    
    # JSON payload with URL
    payload = {
        'urlSource': blob_url
    }
    
    try:
        response = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        if response.status_code == 202:
            print("✅ URL format SUCCESS!")
        else:
            print(f"❌ Failed: {response.text[:150]}...")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python test_docint_body_formats.py <path_to_pdf_file> [blob_url]")
        print("\nExample:")
        print("python test_docint_body_formats.py /path/to/file.pdf")
        print("python test_docint_body_formats.py /path/to/file.pdf https://storage.blob.core.windows.net/container/file.pdf")
        return
    
    file_path = sys.argv[1]
    blob_url = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    # Get credentials
    endpoint = (
        os.getenv("DOCUMENT_INTEL_ENDPOINT") or
        os.getenv("AZURE_FORMREC_SERVICE") or
        os.getenv("AZURE_FORMRECOGNIZER_ENDPOINT")
    )
    
    api_key = (
        os.getenv("DOCUMENT_INTEL_KEY") or
        os.getenv("AZURE_FORMREC_KEY") or
        os.getenv("AZURE_FORMRECOGNIZER_KEY")
    )
    
    if not endpoint or not api_key:
        print("❌ Missing Document Intelligence credentials.")
        return
    
    # Ensure endpoint is full URL
    if not endpoint.startswith('http'):
        if '.' in endpoint:
            endpoint = f"https://{endpoint}"
        else:
            endpoint = f"https://{endpoint}.cognitiveservices.azure.com"
    
    print(f"🔗 Endpoint: {endpoint}")
    print(f"🔑 API Key: ***{api_key[-4:]}")
    
    # Test all formats
    test_multipart_format(file_path, endpoint, api_key)
    test_form_data_format(file_path, endpoint, api_key)
    test_json_format(file_path, endpoint, api_key)
    test_url_format(file_path, endpoint, api_key, blob_url)

if __name__ == "__main__":
    main()
