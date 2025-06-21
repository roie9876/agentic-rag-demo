#!/usr/bin/env python3
"""
Test script to validate Azure Document Intelligence credentials and endpoint.
"""

import os
import sys
import json
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_document_intelligence():
    """Test Azure Document Intelligence credentials and endpoint."""
    
    print("=== Testing Azure Document Intelligence Authentication ===\n")
    
    # Get configuration from environment
    endpoint = os.getenv("AZURE_FORMREC_ENDPOINT", os.getenv("DOCUMENT_INTEL_ENDPOINT", ""))
    api_key = os.getenv("AZURE_FORMREC_KEY", os.getenv("DOCUMENT_INTEL_KEY", ""))
    api_version = os.getenv('FORM_REC_API_VERSION', os.getenv('DOCINT_API_VERSION', '2024-11-30'))
    
    print(f"Endpoint: {endpoint}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'NOT SET'}")
    print(f"API Version: {api_version}")
    print()
    
    if not endpoint:
        print("❌ ERROR: No endpoint configured")
        return False
        
    if not api_key:
        print("❌ ERROR: No API key configured")
        return False
    
    # Clean up the endpoint
    endpoint = endpoint.rstrip("/")
    
    # Test different endpoint formats for Document Intelligence
    test_endpoints = [
        endpoint,  # Original format
        endpoint.replace(".api.cognitive.microsoft.com", ".cognitiveservices.azure.com"),  # Alternative format
    ]
    
    for test_endpoint in test_endpoints:
        print(f"Testing endpoint: {test_endpoint}")
        
        # Test with prebuilt-layout model (common test)
        analyze_url = f"{test_endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version={api_version}"
        
        headers = {
            'Ocp-Apim-Subscription-Key': api_key,
            'Content-Type': 'application/json'
        }
        
        # Simple test payload
        test_payload = {
            "urlSource": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf"
        }
        
        try:
            print(f"POST {analyze_url}")
            print(f"Headers: {dict(headers)}")
            print(f"Payload: {json.dumps(test_payload, indent=2)}")
            
            response = requests.post(analyze_url, headers=headers, json=test_payload, timeout=30)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Text: {response.text[:500]}...")
            print()
            
            if response.status_code == 202:  # Accepted - operation started
                print("✅ SUCCESS: Authentication successful, analysis started")
                return True
            elif response.status_code == 401:
                print("❌ AUTHENTICATION ERROR: Invalid subscription key or wrong API endpoint")
                print("   - Check that your API key is correct")
                print("   - Verify the endpoint region matches your Document Intelligence resource")
                print("   - Ensure your subscription is active")
            elif response.status_code == 404:
                print("❌ ENDPOINT ERROR: Endpoint not found")
                print("   - Check that the endpoint URL is correct")
                print("   - Verify the API version is supported")
            else:
                print(f"❌ ERROR: Unexpected status code {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ NETWORK ERROR: {e}")
        
        print("-" * 50)
    
    return False

def check_endpoint_format():
    """Check if the endpoint format is correct for Document Intelligence."""
    
    print("\n=== Checking Endpoint Format ===\n")
    
    endpoint = os.getenv("AZURE_FORMREC_ENDPOINT", os.getenv("DOCUMENT_INTEL_ENDPOINT", ""))
    
    if not endpoint:
        print("❌ No endpoint configured")
        return
    
    print(f"Current endpoint: {endpoint}")
    
    # Document Intelligence endpoints should typically be in this format:
    # https://<region>.api.cognitive.microsoft.com
    # OR
    # https://<resource-name>.cognitiveservices.azure.com
    
    if ".api.cognitive.microsoft.com" in endpoint:
        print("✅ Endpoint format looks correct (regional endpoint)")
    elif ".cognitiveservices.azure.com" in endpoint:
        print("✅ Endpoint format looks correct (resource-specific endpoint)")
    else:
        print("⚠️  Endpoint format may be incorrect")
        print("   Expected formats:")
        print("   - https://<region>.api.cognitive.microsoft.com")
        print("   - https://<resource-name>.cognitiveservices.azure.com")

def suggest_fixes():
    """Suggest potential fixes for common Document Intelligence authentication issues."""
    
    print("\n=== Suggested Fixes ===\n")
    
    print("1. **Check your Azure portal:**")
    print("   - Go to your Document Intelligence resource")
    print("   - Copy the exact endpoint and key from 'Keys and Endpoint' section")
    print("   - Ensure the resource is in the correct region")
    print()
    
    print("2. **Verify endpoint format:**")
    print("   - Should be: https://<region>.api.cognitive.microsoft.com")
    print("   - Or: https://<resource-name>.cognitiveservices.azure.com")
    print()
    
    print("3. **Check API version:**")
    print("   - Latest: 2024-11-30")
    print("   - For Document Intelligence 4.0: 2023-10-31-preview or later")
    print()
    
    print("4. **Test with curl:**")
    endpoint = os.getenv("AZURE_FORMREC_ENDPOINT", "YOUR_ENDPOINT")
    api_key = os.getenv("AZURE_FORMREC_KEY", "YOUR_KEY")
    
    curl_command = f'''curl -X POST "{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version=2024-11-30" \\
     -H "Ocp-Apim-Subscription-Key: {api_key}" \\
     -H "Content-Type: application/json" \\
     -d '{{"urlSource": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf"}}'
'''
    
    print(f"   {curl_command}")

if __name__ == "__main__":
    print("Azure Document Intelligence Authentication Test")
    print("=" * 50)
    
    # Check environment setup
    check_endpoint_format()
    
    # Test authentication
    success = test_document_intelligence()
    
    if not success:
        suggest_fixes()
    
    print("\n" + "=" * 50)
    print("Test completed.")
