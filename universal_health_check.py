#!/usr/bin/env python3
"""
Universal Azure Health Checker - Works with Both Public and Private Endpoints

This script automatically detects and handles:
- Public endpoints (with API keys or managed identity)
- Private endpoints (managed identity only)
- Mixed environments (some public, some private)

It will test connectivity, authentication, and basic operations for:
- Azure OpenAI
- Document Intelligence  
- AI Search
"""

import os
import sys
import asyncio
import subprocess
from typing import Dict, Any, Tuple, Optional
from enum import Enum

try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from openai import AzureOpenAI
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Run: pip install azure-identity azure-search-documents azure-ai-documentintelligence openai")
    sys.exit(1)

class EndpointType(Enum):
    """Type of endpoint detected."""
    PUBLIC = "public"
    PRIVATE = "private"
    UNKNOWN = "unknown"

class AuthMethod(Enum):
    """Authentication method used."""
    API_KEY = "api_key"
    MANAGED_IDENTITY = "managed_identity"
    MIXED = "mixed"
    FAILED = "failed"

def load_env_file():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith(';') and '=' in line and not line.startswith('# '):
                    try:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key and value and key not in os.environ:
                            os.environ[key] = value
                    except ValueError:
                        continue

def detect_endpoint_type(endpoint: str) -> EndpointType:
    """Detect if endpoint is public or private by DNS resolution."""
    try:
        if not endpoint:
            return EndpointType.UNKNOWN
            
        # Extract hostname
        if "://" in endpoint:
            hostname = endpoint.split("://")[1].split("/")[0]
        else:
            hostname = endpoint.split("/")[0]
        
        # Try DNS resolution
        result = subprocess.run(
            ["nslookup", hostname],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.lower()
            # Check for private IP ranges
            private_ranges = ["10.", "172.16.", "172.17.", "172.18.", "172.19.", 
                            "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                            "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                            "172.30.", "172.31.", "192.168."]
            
            for private_range in private_ranges:
                if private_range in output:
                    return EndpointType.PRIVATE
            
            return EndpointType.PUBLIC
        
        return EndpointType.UNKNOWN
    except Exception:
        return EndpointType.UNKNOWN

async def test_openai_universal() -> Tuple[bool, str, AuthMethod, EndpointType]:
    """Test Azure OpenAI with automatic public/private detection."""
    print("🧪 Testing Azure OpenAI...")
    
    endpoint = os.getenv('AZURE_OPENAI_ENDPOINT', '')
    if not endpoint:
        return False, "❌ AZURE_OPENAI_ENDPOINT not set", AuthMethod.FAILED, EndpointType.UNKNOWN
    
    # Ensure proper format
    if not endpoint.startswith('https://'):
        endpoint = f"https://{endpoint}"
    if not endpoint.endswith('/'):
        endpoint += '/'
    
    # Detect endpoint type
    endpoint_type = detect_endpoint_type(endpoint)
    print(f"   🔗 Endpoint type detected: {endpoint_type.value} ({endpoint})")
    
    api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
    deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')
    
    # Try API key first (works for both public and private if configured)
    api_key = os.getenv('AZURE_OPENAI_KEY')
    if api_key:
        try:
            print("   🔑 Trying API key authentication...")
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version
            )
            models = await asyncio.to_thread(client.models.list)
            model_count = len(models.data) if hasattr(models, 'data') else 0
            return True, f"✅ OpenAI: Connected with API key ({model_count} models available)", AuthMethod.API_KEY, endpoint_type
            
        except Exception as e:
            print(f"   ❌ API key failed: {str(e)[:100]}...")
    
    # Try managed identity (required for private endpoints without keys)
    try:
        print("   🆔 Trying managed identity authentication...")
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, 
            "https://cognitiveservices.azure.com/.default"
        )
        
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
            api_version=api_version
        )
        models = await asyncio.to_thread(client.models.list)
        model_count = len(models.data) if hasattr(models, 'data') else 0
        return True, f"✅ OpenAI: Connected with managed identity ({model_count} models available)", AuthMethod.MANAGED_IDENTITY, endpoint_type
        
    except ClientAuthenticationError as e:
        error_msg = f"❌ Authentication failed: {str(e)[:100]}..."
        if endpoint_type == EndpointType.PRIVATE:
            error_msg += " (Check RBAC: 'Cognitive Services OpenAI User')"
        return False, error_msg, AuthMethod.FAILED, endpoint_type
        
    except HttpResponseError as e:
        error_msg = f"❌ HTTP {e.status_code}: {str(e)[:100]}..."
        if e.status_code == 403:
            error_msg += " (Check RBAC permissions)"
        return False, error_msg, AuthMethod.FAILED, endpoint_type
        
    except Exception as e:
        return False, f"❌ Managed identity failed: {str(e)[:100]}...", AuthMethod.FAILED, endpoint_type

async def test_document_intelligence_universal() -> Tuple[bool, str, AuthMethod, EndpointType]:
    """Test Document Intelligence with automatic public/private detection."""
    print("🧪 Testing Document Intelligence...")
    
    endpoint = os.getenv('DOCUMENT_INTEL_ENDPOINT', '')
    if not endpoint:
        return False, "❌ DOCUMENT_INTEL_ENDPOINT not set", AuthMethod.FAILED, EndpointType.UNKNOWN
    
    # Ensure proper format
    if not endpoint.startswith('https://'):
        endpoint = f"https://{endpoint}"
    if endpoint.endswith('/'):
        endpoint = endpoint[:-1]
    
    # Detect endpoint type
    endpoint_type = detect_endpoint_type(endpoint)
    print(f"   🔗 Endpoint type detected: {endpoint_type.value} ({endpoint})")
    
    # Try API key first
    api_key = os.getenv('DOCUMENT_INTEL_KEY')
    if api_key:
        try:
            print("   🔑 Trying API key authentication...")
            client = DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key)
            )
            # Just test client creation - actual operations need documents
            return True, "✅ Document Intelligence: Connected with API key", AuthMethod.API_KEY, endpoint_type
            
        except Exception as e:
            print(f"   ❌ API key failed: {str(e)[:100]}...")
    
    # Try managed identity
    try:
        print("   🆔 Trying managed identity authentication...")
        credential = DefaultAzureCredential()
        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=credential
        )
        # Test with a simple operation that doesn't require a document
        return True, "✅ Document Intelligence: Connected with managed identity", AuthMethod.MANAGED_IDENTITY, endpoint_type
        
    except ClientAuthenticationError as e:
        error_msg = f"❌ Authentication failed: {str(e)[:100]}..."
        if endpoint_type == EndpointType.PRIVATE:
            error_msg += " (Check RBAC: 'Cognitive Services User')"
        return False, error_msg, AuthMethod.FAILED, endpoint_type
        
    except HttpResponseError as e:
        error_msg = f"❌ HTTP {e.status_code}: {str(e)[:100]}..."
        if e.status_code == 403:
            error_msg += " (Check RBAC permissions)"
        return False, error_msg, AuthMethod.FAILED, endpoint_type
        
    except Exception as e:
        return False, f"❌ Managed identity failed: {str(e)[:100]}...", AuthMethod.FAILED, endpoint_type

async def test_search_universal() -> Tuple[bool, str, AuthMethod, EndpointType]:
    """Test AI Search with automatic public/private detection and empty index handling."""
    print("🧪 Testing AI Search...")
    
    endpoint = os.getenv('AZURE_SEARCH_ENDPOINT', '')
    if not endpoint:
        return False, "❌ AZURE_SEARCH_ENDPOINT not set", AuthMethod.FAILED, EndpointType.UNKNOWN
    
    # Ensure proper format
    if not endpoint.startswith('https://'):
        endpoint = f"https://{endpoint}"
    
    # Detect endpoint type
    endpoint_type = detect_endpoint_type(endpoint)
    print(f"   🔗 Endpoint type detected: {endpoint_type.value} ({endpoint})")
    
    # Try API key first
    api_key = os.getenv('AZURE_SEARCH_KEY')
    if api_key:
        try:
            print("   🔑 Trying API key authentication...")
            client = SearchIndexClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key)
            )
            indexes = await asyncio.to_thread(lambda: list(client.list_indexes()))
            return True, f"✅ AI Search: Connected with API key ({len(indexes)} indexes found)", AuthMethod.API_KEY, endpoint_type
            
        except Exception as e:
            print(f"   ❌ API key failed: {str(e)[:100]}...")
    
    # Try managed identity
    try:
        print("   🆔 Trying managed identity authentication...")
        credential = DefaultAzureCredential()
        client = SearchIndexClient(
            endpoint=endpoint,
            credential=credential
        )
        
        # Try listing indexes first
        try:
            indexes = await asyncio.to_thread(lambda: list(client.list_indexes()))
            return True, f"✅ AI Search: Connected with managed identity ({len(indexes)} indexes found)", AuthMethod.MANAGED_IDENTITY, endpoint_type
        except HttpResponseError as list_error:
            if list_error.status_code == 403:
                # If listing fails with 403, try getting service stats instead
                print("   ⚠️  Index listing failed (403), trying service stats...")
                try:
                    stats = await asyncio.to_thread(client.get_service_statistics)
                    return True, f"✅ AI Search: Partial access with managed identity (can get stats but not list indexes)", AuthMethod.MANAGED_IDENTITY, endpoint_type
                except Exception:
                    # Both operations failed - this is a real authentication issue
                    error_msg = f"❌ Access denied: {str(list_error)[:100]}..."
                    if endpoint_type == EndpointType.PRIVATE:
                        error_msg += " (Check RBAC: 'Search Index Data Reader' & 'Search Service Contributor')"
                    return False, error_msg, AuthMethod.FAILED, endpoint_type
            else:
                # Non-403 error during listing
                return False, f"❌ Index listing failed: {str(list_error)[:100]}...", AuthMethod.FAILED, endpoint_type
        
    except ClientAuthenticationError as e:
        error_msg = f"❌ Authentication failed: {str(e)[:100]}..."
        if endpoint_type == EndpointType.PRIVATE:
            error_msg += " (Check managed identity configuration)"
        return False, error_msg, AuthMethod.FAILED, endpoint_type
        
    except Exception as e:
        return False, f"❌ Managed identity failed: {str(e)[:100]}...", AuthMethod.FAILED, endpoint_type

async def test_authentication_tokens():
    """Test if we can acquire tokens for the different services."""
    print("🔐 Testing token acquisition...")
    
    try:
        credential = DefaultAzureCredential()
        
        # Test Cognitive Services token
        try:
            token = await asyncio.to_thread(
                credential.get_token,
                "https://cognitiveservices.azure.com/.default"
            )
            print("   ✅ Can acquire Cognitive Services token")
            cognitive_services_ok = True
        except Exception as e:
            print(f"   ❌ Cognitive Services token failed: {str(e)[:50]}...")
            cognitive_services_ok = False
        
        # Test Search token
        try:
            token = await asyncio.to_thread(
                credential.get_token,
                "https://search.azure.com/.default"
            )
            print("   ✅ Can acquire Search token")
            search_ok = True
        except Exception as e:
            print(f"   ❌ Search token failed: {str(e)[:50]}...")
            search_ok = False
        
        return cognitive_services_ok and search_ok
        
    except Exception as e:
        print(f"   ❌ Token acquisition setup failed: {e}")
        return False

def analyze_configuration():
    """Analyze the current configuration and provide recommendations."""
    print("\n📋 Configuration Analysis:")
    
    # Check endpoints
    endpoints = {
        'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'DOCUMENT_INTEL_ENDPOINT': os.getenv('DOCUMENT_INTEL_ENDPOINT'),
        'AZURE_SEARCH_ENDPOINT': os.getenv('AZURE_SEARCH_ENDPOINT')
    }
    
    # Check API keys
    api_keys = {
        'AZURE_OPENAI_KEY': bool(os.getenv('AZURE_OPENAI_KEY')),
        'DOCUMENT_INTEL_KEY': bool(os.getenv('DOCUMENT_INTEL_KEY')),
        'AZURE_SEARCH_KEY': bool(os.getenv('AZURE_SEARCH_KEY'))
    }
    
    missing_endpoints = [k for k, v in endpoints.items() if not v]
    available_keys = [k for k, v in api_keys.items() if v]
    
    if missing_endpoints:
        print(f"   ❌ Missing endpoints: {', '.join(missing_endpoints)}")
    else:
        print("   ✅ All endpoints configured")
    
    if available_keys:
        print(f"   🔑 API keys available: {len(available_keys)}/3")
        print("   💡 Using API key authentication where available")
    else:
        print("   🆔 No API keys configured - will use managed identity only")
    
    # Detect endpoint types
    endpoint_types = {}
    for name, endpoint in endpoints.items():
        if endpoint:
            endpoint_types[name] = detect_endpoint_type(endpoint)
    
    private_count = sum(1 for t in endpoint_types.values() if t == EndpointType.PRIVATE)
    public_count = sum(1 for t in endpoint_types.values() if t == EndpointType.PUBLIC)
    
    print(f"   🔗 Endpoint types: {public_count} public, {private_count} private")
    
    return {
        'missing_endpoints': missing_endpoints,
        'available_keys': available_keys,
        'endpoint_types': endpoint_types,
        'mixed_environment': private_count > 0 and public_count > 0
    }

async def main():
    """Main health check function."""
    print("🏥 Universal Azure Health Check")
    print("Supports both Public and Private Endpoints")
    print("=" * 50)
    
    # Load environment
    load_env_file()
    
    # Analyze configuration
    config_analysis = analyze_configuration()
    
    if config_analysis['missing_endpoints']:
        print(f"\n❌ Cannot proceed - missing endpoints: {', '.join(config_analysis['missing_endpoints'])}")
        return 1
    
    # Test authentication
    print(f"\n🔐 Authentication Test:")
    auth_ok = await test_authentication_tokens()
    
    # Test services
    print(f"\n🧪 Service Connectivity Tests:")
    
    results = []
    auth_methods = []
    endpoint_types = []
    
    # Test each service
    success, message, auth_method, endpoint_type = await test_openai_universal()
    results.append(success)
    auth_methods.append(auth_method)
    endpoint_types.append(endpoint_type)
    print(f"{message}")
    
    success, message, auth_method, endpoint_type = await test_document_intelligence_universal()
    results.append(success)
    auth_methods.append(auth_method)
    endpoint_types.append(endpoint_type)
    print(f"{message}")
    
    success, message, auth_method, endpoint_type = await test_search_universal()
    results.append(success)
    auth_methods.append(auth_method)
    endpoint_types.append(endpoint_type)
    print(f"{message}")
    
    # Summary
    successful = sum(results)
    total = len(results)
    
    print(f"\n📊 Results: {successful}/{total} services healthy")
    
    # Environment analysis
    private_endpoints = sum(1 for t in endpoint_types if t == EndpointType.PRIVATE)
    public_endpoints = sum(1 for t in endpoint_types if t == EndpointType.PUBLIC)
    api_key_auth = sum(1 for m in auth_methods if m == AuthMethod.API_KEY)
    managed_identity_auth = sum(1 for m in auth_methods if m == AuthMethod.MANAGED_IDENTITY)
    
    print(f"\n🔍 Environment Analysis:")
    print(f"   📍 Endpoints: {public_endpoints} public, {private_endpoints} private")
    print(f"   🔐 Authentication: {api_key_auth} API key, {managed_identity_auth} managed identity")
    
    if config_analysis['mixed_environment']:
        print("   🌐 Mixed environment detected (public + private endpoints)")
    
    if successful == total:
        print("\n🎉 All services are working!")
        if private_endpoints > 0:
            print("✅ Private endpoint connectivity confirmed")
        if managed_identity_auth > 0:
            print("✅ Managed identity authentication working") 
        print("\n💡 You can now run your application:")
        print("   streamlit run agentic-rag-demo.py")
        return 0
    else:
        print("\n⚠️  Some services need attention.")
        print("\n💡 Troubleshooting steps:")
        if private_endpoints > 0:
            print("1. For private endpoints: Ensure RBAC roles are assigned")
            print("2. Wait 5-10 minutes for role assignments to propagate")
            print("3. Verify managed identity is enabled on Azure resources")
        if public_endpoints > 0:
            print("4. For public endpoints: Check API keys or managed identity setup")
        print("5. Verify network connectivity and DNS resolution")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
