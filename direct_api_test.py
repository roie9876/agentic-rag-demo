#!/usr/bin/env python3
import os
import requests
from pathlib import Path

print("🔍 Direct Document Intelligence API test...")

# Load environment manually
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                # Handle variable expansion like ${OTHER_VAR}
                while '${' in value and '}' in value:
                    start = value.find('${')
                    end = value.find('}', start)
                    if start != -1 and end != -1:
                        var_name = value[start+2:end]
                        var_value = os.environ.get(var_name, '')
                        value = value[:start] + var_value + value[end+1:]
                    else:
                        break
                os.environ[key] = value

endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT")
key = os.getenv("DOCUMENT_INTEL_KEY")
api_version = "2024-11-30"

print(f"🌐 Endpoint: {endpoint}")
print(f"🔑 Key configured: {'Yes' if key else 'No'}")
print(f"📋 API Version: {api_version}")

# Test PDF
pdf_path = "/Users/robenhai/Downloads/תעשייה אווירית – ויקיפדיה.pdf"
if not os.path.exists(pdf_path):
    print("❌ PDF not found!")
    exit(1)

with open(pdf_path, 'rb') as f:
    file_bytes = f.read()

print(f"📊 File size: {len(file_bytes):,} bytes")

# Make direct API call
try:
    url = f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version={api_version}&features=ocr.highResolution"
    
    headers = {
        "Content-Type": "application/pdf",
        "Ocp-Apim-Subscription-Key": key,
        "x-ms-useragent": "gpt-rag/1.0.0"
    }
    
    print(f"🚀 Making API request to: {url}")
    print(f"📤 Request headers: {list(headers.keys())}")
    
    response = requests.post(url, headers=headers, data=file_bytes, timeout=30)
    
    print(f"📥 Response status: {response.status_code}")
    print(f"📋 Response headers: {dict(response.headers)}")
    
    if response.status_code == 202:
        operation_location = response.headers.get("Operation-Location")
        print(f"✅ Analysis started successfully!")
        print(f"🔗 Operation location: {operation_location}")
        
        if operation_location:
            # Poll for results
            result_headers = {
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "application/json-patch+json"
            }
            
            print(f"⏳ Polling for results...")
            import time
            for i in range(30):  # Poll for up to 60 seconds
                time.sleep(2)
                result_response = requests.get(operation_location, headers=result_headers)
                print(f"📊 Poll {i+1}: Status {result_response.status_code}")
                
                if result_response.status_code == 200:
                    result_json = result_response.json()
                    status = result_json.get("status")
                    print(f"🔄 Analysis status: {status}")
                    
                    if status == "succeeded":
                        print(f"✅ SUCCESS! Analysis completed")
                        analyze_result = result_json.get('analyzeResult', {})
                        content = analyze_result.get('content', '')
                        pages = analyze_result.get('pages', [])
                        print(f"📄 Content length: {len(content)} chars")
                        print(f"📃 Number of pages: {len(pages)}")
                        print(f"📝 Content preview: {repr(content[:200])}...")
                        break
                    elif status == "failed":
                        print(f"❌ Analysis failed!")
                        if 'error' in result_json:
                            error = result_json['error']
                            print(f"💥 Error: {error}")
                        break
                else:
                    print(f"❌ Polling failed: {result_response.status_code}")
                    print(f"📄 Response: {result_response.text}")
                    break
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
except Exception as e:
    print(f"💥 Exception: {e}")
    import traceback
    traceback.print_exc()
