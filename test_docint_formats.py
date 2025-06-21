#!/usr/bin/env python3
"""
Test different request formats to Document Intelligence API
to identify what works vs what doesn't work.
"""

import os
import sys
import requests
import json
from pathlib import Path

def test_different_content_types(file_path, endpoint, api_key):
    """Test the same file with different Content-Type headers."""
    print("🧪 Testing different Content-Type headers")
    print("=" * 50)
    
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    
    filename = Path(file_path).name
    print(f"📁 File: {filename}")
    print(f"📊 Size: {len(file_bytes):,} bytes")
    
    # Different content types to try
    content_types = [
        'application/pdf',
        'application/octet-stream', 
        'binary/octet-stream',
        'multipart/form-data',
        None  # No Content-Type header
    ]
    
    api_versions = [
        '2024-11-30',  # Latest
        '2023-10-31-preview',  # v4.0
        '2023-07-31',  # Stable
        '2022-08-31'   # Older
    ]
    
    base_url = endpoint.rstrip('/')
    model = 'prebuilt-layout'
    
    # Test each combination
    for api_version in api_versions:
        print(f"\n🔧 Testing API version: {api_version}")
        
        for content_type in content_types:
            print(f"  📋 Content-Type: {content_type or 'None'}")
            
            # Build URL
            if api_version >= '2023-10-31':
                service_type = 'documentintelligence'
            else:
                service_type = 'formrecognizer'
                
            url = f"{base_url}/{service_type}/documentModels/{model}:analyze?api-version={api_version}"
            
            # Add features for newer versions
            if api_version >= '2023-10-31':
                url += "&outputContentFormat=markdown&output=figures"
            
            headers = {
                "Ocp-Apim-Subscription-Key": api_key,
                "x-ms-useragent": "azure-portal/1.0.0"  # Mimic portal user agent
            }
            
            if content_type:
                headers["Content-Type"] = content_type
            
            try:
                response = requests.post(url, headers=headers, data=file_bytes, timeout=30)
                
                if response.status_code == 202:
                    print(f"    ✅ SUCCESS (202)")
                    # Don't wait for completion, just test if request is accepted
                elif response.status_code == 400:
                    print(f"    ❌ Bad Request (400): {response.text[:100]}...")
                elif response.status_code == 415:
                    print(f"    ❌ Unsupported Media Type (415)")
                else:
                    print(f"    ❌ Error {response.status_code}: {response.text[:50]}...")
                    
            except Exception as e:
                print(f"    ❌ Exception: {str(e)[:50]}...")

def test_portal_style_request(file_path, endpoint, api_key):
    """Test with headers and format similar to Azure portal."""
    print("\n🌐 Testing Azure Portal-style request")
    print("=" * 50)
    
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    
    filename = Path(file_path).name
    
    # Try to mimic what the Azure portal does
    url = f"{endpoint.rstrip('/')}/documentintelligence/documentModels/prebuilt-layout:analyze"
    
    # Parameters that portal might use
    params = {
        'api-version': '2024-11-30',
        'stringIndexType': 'textElements',
        'outputContentFormat': 'markdown',
        'output': 'figures'
    }
    
    # Headers that portal might use
    headers = {
        'Content-Type': 'application/pdf',
        'Ocp-Apim-Subscription-Key': api_key,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Origin': 'https://portal.azure.com',
        'Referer': 'https://portal.azure.com/',
        'x-ms-client-request-id': 'portal-request-12345',
        'x-ms-useragent': 'azure-portal/unknown'
    }
    
    print(f"📁 File: {filename}")
    print(f"🌐 URL: {url}")
    print(f"📋 Params: {params}")
    print(f"📋 Key headers: Content-Type={headers['Content-Type']}, User-Agent={headers['User-Agent'][:50]}...")
    
    try:
        response = requests.post(url, params=params, headers=headers, data=file_bytes, timeout=30)
        
        print(f"📊 Response: {response.status_code}")
        if response.status_code == 202:
            print("✅ Portal-style request SUCCESS!")
            operation_location = response.headers.get('Operation-Location')
            if operation_location:
                print(f"🔗 Operation: {operation_location}")
        else:
            print(f"❌ Portal-style request failed")
            print(f"📄 Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python test_docint_formats.py <path_to_pdf_file>")
        return
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    # Get credentials from environment
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
        print("Set DOCUMENT_INTEL_ENDPOINT and DOCUMENT_INTEL_KEY environment variables.")
        return
    
    # Ensure endpoint is full URL
    if not endpoint.startswith('http'):
        if '.' in endpoint:
            endpoint = f"https://{endpoint}"
        else:
            endpoint = f"https://{endpoint}.cognitiveservices.azure.com"
    
    print(f"🔗 Using endpoint: {endpoint}")
    print(f"🔑 Using API key: ***{api_key[-4:]}")
    
    test_different_content_types(file_path, endpoint, api_key)
    test_portal_style_request(file_path, endpoint, api_key)

if __name__ == "__main__":
    main()
