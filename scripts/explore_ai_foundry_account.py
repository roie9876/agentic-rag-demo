#!/usr/bin/env python3
"""
Explore AI Foundry Account Structure
This script explores the AI Foundry account to discover the correct API endpoints,
available projects, and supported operations.
"""

import os
import requests
import json
from typing import Dict, Any, Optional, List
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()
    return {
        'project_endpoint': os.getenv('PROJECT_ENDPOINT'),
        'api_version': os.getenv('API_VERSION', '2025-05-01-preview'),
    }

def get_azure_token() -> str:
    """Get Azure access token for AI Foundry Account."""
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
    except Exception as e:
        print(f"❌ Failed to get Azure token: {e}")
        return None

def parse_foundry_endpoint(endpoint: str) -> Dict[str, str]:
    """Parse AI Foundry endpoint to extract account details."""
    try:
        # https://aiagenticservicesfgtt.services.ai.azure.com/api/projects/agentic-rag
        parts = endpoint.split('/')
        hostname = parts[2]  # aiagenticservicesfgtt.services.ai.azure.com
        account_name = hostname.split('.')[0]  # aiagenticservicesfgtt
        
        return {
            'hostname': hostname,
            'account_name': account_name,
            'base_url': f"https://{hostname}",
            'api_base': f"https://{hostname}/api"
        }
    except Exception as e:
        print(f"❌ Error parsing endpoint: {e}")
        return {}

def test_api_endpoints(base_info: Dict[str, str], token: str, api_version: str) -> Dict[str, Any]:
    """Test various API endpoints to discover available operations."""
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    base_url = base_info['base_url']
    api_base = base_info['api_base']
    
    # List of endpoints to test
    endpoints_to_test = [
        # Root endpoints
        f"{base_url}/",
        f"{api_base}/",
        
        # Project-related endpoints
        f"{api_base}/projects",
        f"{api_base}/workspaces",
        
        # Different API versions
        f"{api_base}/projects?api-version=2024-10-01-preview",
        f"{api_base}/projects?api-version=2024-07-01-preview", 
        f"{api_base}/projects?api-version=2023-12-01-preview",
        
        # Agent endpoints
        f"{api_base}/agents",
        f"{api_base}/models",
        f"{api_base}/deployments",
        
        # Health/status endpoints
        f"{base_url}/health",
        f"{base_url}/status",
        f"{api_base}/health",
        f"{api_base}/status",
    ]
    
    results = {}
    
    print("🔍 Testing API endpoints...")
    print("=" * 60)
    
    for endpoint in endpoints_to_test:
        try:
            print(f"🔸 Testing: {endpoint}")
            
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=10
            )
            
            status = response.status_code
            
            if status == 200:
                try:
                    data = response.json()
                    print(f"✅ SUCCESS ({status}): {json.dumps(data, indent=2)[:200]}...")
                    results[endpoint] = {
                        'status': status,
                        'data': data,
                        'success': True
                    }
                except:
                    print(f"✅ SUCCESS ({status}): {response.text[:200]}...")
                    results[endpoint] = {
                        'status': status,
                        'text': response.text,
                        'success': True
                    }
            elif status == 401:
                print(f"🔒 UNAUTHORIZED ({status}): Authentication issue")
                results[endpoint] = {'status': status, 'error': 'Unauthorized'}
            elif status == 403:
                print(f"🚫 FORBIDDEN ({status}): Permission issue")
                results[endpoint] = {'status': status, 'error': 'Forbidden'}
            elif status == 404:
                print(f"❌ NOT FOUND ({status}): Endpoint doesn't exist")
                results[endpoint] = {'status': status, 'error': 'Not Found'}
            elif status == 405:
                print(f"🔄 METHOD NOT ALLOWED ({status}): Try different HTTP method")
                results[endpoint] = {'status': status, 'error': 'Method Not Allowed'}
            else:
                print(f"⚠️  OTHER ({status}): {response.text[:100]}...")
                results[endpoint] = {'status': status, 'text': response.text}
                
        except requests.exceptions.Timeout:
            print(f"⏰ TIMEOUT: Request timed out")
            results[endpoint] = {'error': 'Timeout'}
        except requests.exceptions.ConnectionError:
            print(f"🔌 CONNECTION ERROR: Can't connect")
            results[endpoint] = {'error': 'Connection Error'}
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results[endpoint] = {'error': str(e)}
        
        print()
    
    return results

def analyze_results(results: Dict[str, Any], base_info: Dict[str, str]):
    """Analyze the test results and provide recommendations."""
    
    print("🎯 ANALYSIS & RECOMMENDATIONS")
    print("=" * 60)
    
    successful_endpoints = []
    for endpoint, result in results.items():
        if result.get('success'):
            successful_endpoints.append(endpoint)
    
    if successful_endpoints:
        print("✅ Working endpoints found:")
        for endpoint in successful_endpoints:
            print(f"   📍 {endpoint}")
            result = results[endpoint]
            if 'data' in result:
                data = result['data']
                if isinstance(data, dict):
                    if 'value' in data:
                        print(f"      📋 Contains {len(data['value'])} items")
                    elif 'projects' in data:
                        print(f"      📋 Contains projects data")
                    elif 'name' in data:
                        print(f"      📋 Name: {data['name']}")
        print()
    else:
        print("❌ No successful endpoints found")
        print()
    
    # Check for common patterns
    api_versions_tried = []
    for endpoint in results.keys():
        if 'api-version=' in endpoint:
            version = endpoint.split('api-version=')[1].split('&')[0]
            api_versions_tried.append(version)
    
    if api_versions_tried:
        print(f"🔍 API Versions tested: {', '.join(set(api_versions_tried))}")
        working_versions = []
        for endpoint, result in results.items():
            if 'api-version=' in endpoint and result.get('success'):
                version = endpoint.split('api-version=')[1].split('&')[0]
                working_versions.append(version)
        
        if working_versions:
            print(f"✅ Working API versions: {', '.join(set(working_versions))}")
        else:
            print("❌ No API versions worked")
        print()
    
    # Provide specific recommendations
    print("💡 RECOMMENDATIONS:")
    
    # Check if we found any project endpoints
    project_endpoints = [ep for ep in successful_endpoints if 'project' in ep.lower()]
    if project_endpoints:
        print("✅ Found working project endpoints!")
        for ep in project_endpoints:
            print(f"   🎯 Use: {ep}")
    else:
        print("❌ No project endpoints found")
        print("   💡 The project might not exist yet")
        print("   💡 Or the API structure is different than expected")
    
    # Check authentication
    auth_issues = [ep for ep, result in results.items() if result.get('status') in [401, 403]]
    if auth_issues:
        print(f"🔒 Authentication issues on {len(auth_issues)} endpoints")
        print("   💡 Your permissions might be limited to specific operations")
    
    # Check for alternative endpoints
    if not successful_endpoints:
        print("🔧 TROUBLESHOOTING:")
        print("   1. Try creating the project first in Azure Portal or AI Foundry Studio")
        print("   2. Check if you need to use a different API version")
        print("   3. Verify the AI Foundry account supports the expected API structure")
        print(f"   4. Try accessing the AI Foundry Portal: https://ai.azure.com")

def suggest_next_steps(base_info: Dict[str, str]):
    """Suggest next steps based on findings."""
    
    print("\n🚀 SUGGESTED NEXT STEPS:")
    print("=" * 60)
    
    account_name = base_info['account_name']
    
    print("1. 🌐 Check AI Foundry Portal:")
    print(f"   Visit: https://ai.azure.com")
    print(f"   Look for your account: {account_name}")
    print(f"   Check if project 'agentic-rag' exists")
    print()
    
    print("2. 🏗️  Create Project (if it doesn't exist):")
    print("   Use Azure Portal or AI Foundry Studio to create the project")
    print("   Then update your PROJECT_ENDPOINT with the correct project name")
    print()
    
    print("3. 🔍 Alternative API exploration:")
    print("   Try using Azure ML SDK or AI Services SDK")
    print("   Check Azure Resource Manager API for the account")
    print()
    
    print("4. 📞 Check Azure documentation:")
    print("   Look for AI Foundry Account API documentation")
    print("   Verify supported API versions and endpoints")

def main():
    """Main function to explore AI Foundry account structure."""
    print("🔍 AI Foundry Account Explorer")
    print("=" * 60)
    
    # Load configuration
    config = load_environment()
    
    if not config['project_endpoint']:
        print("❌ PROJECT_ENDPOINT not found in .env file")
        return
    
    print(f"📋 Exploring: {config['project_endpoint']}")
    print(f"🔧 API Version: {config['api_version']}")
    print()
    
    # Parse the endpoint
    base_info = parse_foundry_endpoint(config['project_endpoint'])
    if not base_info:
        return
    
    print(f"🎯 AI Foundry Account: {base_info['account_name']}")
    print(f"🌐 Base URL: {base_info['base_url']}")
    print(f"🔌 API Base: {base_info['api_base']}")
    print()
    
    # Get access token
    token = get_azure_token()
    if not token:
        return
    
    print("✅ Successfully obtained access token")
    print()
    
    # Test API endpoints
    results = test_api_endpoints(base_info, token, config['api_version'])
    
    # Analyze results
    analyze_results(results, base_info)
    
    # Suggest next steps
    suggest_next_steps(base_info)

if __name__ == "__main__":
    main()
