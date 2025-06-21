#!/usr/bin/env python3
"""
Debug script to compare Document Intelligence API requests.
This will help us understand the difference between what our code sends
vs what the Azure portal sends, so we can identify why some PDFs work
in the portal but not in our code.
"""

import os
import sys
import requests
import json
import mimetypes
from pathlib import Path
from tools.doc_intelligence import DocumentIntelligenceClient

def debug_request_details(file_path):
    """Debug the exact request being sent to Document Intelligence API."""
    print("🔍 Document Intelligence Request Debug Tool")
    print("=" * 60)
    
    # Read the file
    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    filename = Path(file_path).name
    print(f"📁 File: {filename}")
    print(f"📊 Size: {len(file_bytes):,} bytes")
    
    # Analyze the file header
    header = file_bytes[:100]
    print(f"🔤 First 100 bytes: {repr(header)}")
    
    # Check if it starts with PDF header
    if file_bytes.startswith(b'%PDF-'):
        print("✅ File starts with %PDF- header")
    else:
        print("⚠️  File does NOT start with %PDF- header")
        # Show what it actually starts with
        try:
            text_start = header.decode('utf-8', errors='ignore')
            print(f"📝 Starts with: {repr(text_start[:50])}")
        except:
            print("📝 Cannot decode start as UTF-8")
    
    # Initialize Document Intelligence client
    try:
        client = DocumentIntelligenceClient()
        print(f"🔗 Endpoint: {client.endpoint}")
        print(f"🔧 API Version: {client.api_version}")
        print(f"🛡️ Using API Key: {'Yes' if client.api_key else 'No (using token auth)'}")
    except Exception as e:
        print(f"❌ Failed to initialize Document Intelligence client: {e}")
        return
    
    # Build the exact request that will be sent
    model = 'prebuilt-layout'
    file_ext = Path(filename).suffix[1:].lower() if Path(filename).suffix else ""
    
    # Get content type
    content_type_map = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'html': 'text/html'
    }
    
    content_type = content_type_map.get(file_ext, 'application/octet-stream')
    
    # Guess content type using mimetypes as well
    guessed_type, _ = mimetypes.guess_type(filename)
    print(f"📄 File extension: .{file_ext}")
    print(f"🏷️  Our content-type: {content_type}")
    print(f"🔍 Python guessed type: {guessed_type}")
    
    # Build request URL
    ai_service_type = "documentintelligence" if client.docint_40_api else "formrecognizer"
    request_endpoint = f"{client.endpoint}/{ai_service_type}/documentModels/{model}:analyze?api-version={client.api_version}"
    
    # Add features for PDF
    if file_ext == "pdf":
        request_endpoint += "&features=ocr.highResolution"
    
    # Add output format if using newer API
    if client.docint_40_api:
        request_endpoint += "&outputContentFormat=markdown&output=figures"
    
    print(f"🌐 Request URL: {request_endpoint}")
    
    # Build headers
    headers = {
        "Content-Type": content_type,
        "x-ms-useragent": "gpt-rag/1.0.0"
    }
    
    if client.api_key:
        headers["Ocp-Apim-Subscription-Key"] = client.api_key
    else:
        try:
            token = client.credential.get_token("https://cognitiveservices.azure.com/.default")
            headers["Authorization"] = f"Bearer {token.token}"
        except Exception as e:
            print(f"❌ Failed to get authentication token: {e}")
            return
    
    print(f"📋 Request headers:")
    for key, value in headers.items():
        if key == "Ocp-Apim-Subscription-Key":
            print(f"   {key}: ***{value[-4:] if value else 'None'}")
        elif key == "Authorization":
            print(f"   {key}: Bearer ***{value.split('.')[-1][-10:] if '.' in value else value[-10:]}")
        else:
            print(f"   {key}: {value}")
    
    print("\n🚀 Sending request...")
    
    # Send the actual request
    try:
        response = requests.post(request_endpoint, headers=headers, data=file_bytes)
        print(f"📊 Response status: {response.status_code}")
        print(f"📋 Response headers:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")
        
        if response.status_code == 202:
            print("✅ Request accepted successfully!")
            operation_location = response.headers.get("Operation-Location")
            if operation_location:
                print(f"🔗 Operation Location: {operation_location}")
            else:
                print("⚠️  No Operation-Location header found")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"📄 Response body: {response.text}")
            
            # Provide specific guidance based on the error
            if response.status_code == 400:
                print("\n💡 Common 400 error causes:")
                print("   • File is corrupted or not a valid PDF")
                print("   • File is too large (>500MB for paid, >4MB for free tier)")
                print("   • File is password protected")
                print("   • Content-Type header doesn't match file content")
                
            elif response.status_code == 415:
                print("\n💡 415 Unsupported Media Type:")
                print("   • Content-Type header may be incorrect")
                print("   • File format not supported by the model")
                print(f"   • Try changing Content-Type from '{content_type}' to 'application/pdf'")
                
    except Exception as e:
        print(f"❌ Exception during request: {e}")
    
    print("\n" + "=" * 60)
    print("🔧 Debugging suggestions:")
    print("1. Try the same file in the Azure portal Document Intelligence studio")
    print("2. Check if the file opens correctly in a PDF viewer")
    print("3. Try saving/re-exporting the PDF from another application")
    print("4. Check if the file has any special encoding or metadata")
    print("5. Try analyzing with a different model (e.g., prebuilt-read)")

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python debug_docint_request.py <path_to_pdf_file>")
        print("\nExample:")
        print("python debug_docint_request.py /path/to/problematic.pdf")
        return
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    debug_request_details(file_path)

if __name__ == "__main__":
    main()
