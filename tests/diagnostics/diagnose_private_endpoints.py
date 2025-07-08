#!/usr/bin/env python3
"""
Quick Private Endpoint Diagnostics Script
=========================================
This script provides immediate diagnostics for private endpoint issues.
Run this script to quickly identify authentication and connectivity problems.
"""

import os
import sys
import subprocess
import json
from typing import Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_environment_variables():
    """Check if required environment variables are set."""
    print("🔍 Checking Environment Variables...")
    print("=" * 50)
    
    required_vars = {
        "OpenAI": [
            "AZURE_OPENAI_ENDPOINT_41",
            "AZURE_OPENAI_ENDPOINT", 
            "AZURE_OPENAI_KEY_41",
            "AZURE_OPENAI_KEY"
        ],
        "Document Intelligence": [
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
            "DOCUMENT_INTEL_ENDPOINT",
            "DOCUMENT_INTEL_KEY"
        ],
        "AI Search": [
            "AZURE_SEARCH_ENDPOINT",
            "AZURE_SEARCH_KEY"
        ]
    }
    
    for service, vars_list in required_vars.items():
        print(f"\n📋 {service}:")
        for var in vars_list:
            value = os.getenv(var, "")
            if value:
                # Show only first and last 4 characters for security
                if len(value) > 8:
                    display_value = f"{value[:4]}...{value[-4:]}"
                else:
                    display_value = "****"
                print(f"  ✅ {var}: {display_value}")
            else:
                print(f"  ❌ {var}: Not set")

def check_azure_cli():
    """Check Azure CLI authentication."""
    print("\n🔐 Checking Azure CLI Authentication...")
    print("=" * 50)
    
    try:
        result = subprocess.run(
            ["az", "account", "show", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            account_info = json.loads(result.stdout)
            print(f"✅ Azure CLI authenticated")
            print(f"   User: {account_info.get('name', 'Unknown')}")
            print(f"   Tenant: {account_info.get('tenantId', 'Unknown')}")
            print(f"   Subscription: {account_info.get('name', 'Unknown')} ({account_info.get('id', 'Unknown')})")
            return True
        else:
            print(f"❌ Azure CLI not authenticated: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Azure CLI not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking Azure CLI: {str(e)}")
        return False

def check_managed_identity():
    """Check if managed identity is available."""
    print("\n🤖 Checking Managed Identity...")
    print("=" * 50)
    
    try:
        # Try to access IMDS endpoint
        result = subprocess.run(
            ["curl", "-s", "-H", "Metadata:true", "--max-time", "5",
             "http://169.254.169.254/metadata/instance?api-version=2021-02-01"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                instance_info = json.loads(result.stdout)
                print("✅ Managed Identity available (IMDS accessible)")
                compute_info = instance_info.get("compute", {})
                print(f"   VM: {compute_info.get('name', 'Unknown')}")
                print(f"   Resource Group: {compute_info.get('resourceGroupName', 'Unknown')}")
                print(f"   Location: {compute_info.get('location', 'Unknown')}")
                return True
            except json.JSONDecodeError:
                print("⚠️ IMDS accessible but response not valid JSON")
                return False
        else:
            print("❌ Managed Identity not available (IMDS not accessible)")
            return False
            
    except Exception as e:
        print(f"❌ Error checking managed identity: {str(e)}")
        return False

def check_network_connectivity():
    """Check network connectivity to Azure services."""
    print("\n🌐 Checking Network Connectivity...")
    print("=" * 50)
    
    endpoints = {
        "OpenAI": os.getenv("AZURE_OPENAI_ENDPOINT_41") or os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "Document Intelligence": (os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT") or 
                                os.getenv("DOCUMENT_INTEL_ENDPOINT", "")),
        "AI Search": os.getenv("AZURE_SEARCH_ENDPOINT", "")
    }
    
    for service, endpoint in endpoints.items():
        if not endpoint:
            print(f"❌ {service}: No endpoint configured")
            continue
            
        # Extract hostname
        if "://" in endpoint:
            hostname = endpoint.split("://")[1].split("/")[0]
        else:
            hostname = endpoint.split("/")[0]
        
        try:
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
                private_patterns = ["10.", "172.1", "172.2", "172.3", "192.168."]
                is_private = any(pattern in output for pattern in private_patterns)
                
                if is_private:
                    print(f"✅ {service}: Resolves to private IP (private endpoint)")
                else:
                    print(f"⚠️ {service}: Resolves to public IP (not private endpoint)")
            else:
                print(f"❌ {service}: DNS resolution failed")
                
        except Exception as e:
            print(f"❌ {service}: Network check failed - {str(e)}")

def test_service_connections():
    """Test actual connections to services."""
    print("\n🔌 Testing Service Connections...")
    print("=" * 50)
    
    # Test AI Search (the failing service)
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    if search_endpoint:
        print(f"🔍 Testing AI Search: {search_endpoint}")
        
        try:
            from azure.identity import DefaultAzureCredential
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents.indexes import SearchIndexClient
            
            # Try with API key first
            api_key = os.getenv("AZURE_SEARCH_KEY")
            if api_key:
                print("  🔑 Trying API key authentication...")
                try:
                    client = SearchIndexClient(
                        endpoint=search_endpoint,
                        credential=AzureKeyCredential(api_key)
                    )
                    indexes = list(client.list_indexes())
                    print(f"    ✅ Success with API key! Found {len(indexes)} indexes")
                except Exception as e:
                    print(f"    ❌ API key failed: {str(e)}")
            else:
                print("  ⚠️ No API key configured")
            
            # Try with managed identity
            print("  🤖 Trying managed identity authentication...")
            try:
                credential = DefaultAzureCredential()
                client = SearchIndexClient(
                    endpoint=search_endpoint,
                    credential=credential
                )
                indexes = list(client.list_indexes())
                print(f"    ✅ Success with managed identity! Found {len(indexes)} indexes")
            except Exception as e:
                print(f"    ❌ Managed identity failed: {str(e)}")
                
        except ImportError as e:
            print(f"  ❌ Import error: {str(e)}")
    else:
        print("❌ No AI Search endpoint configured")

def generate_fix_recommendations():
    """Generate specific fix recommendations based on the diagnostics."""
    print("\n🔧 Fix Recommendations...")
    print("=" * 50)
    
    # Check what authentication methods are available
    has_cli = check_azure_cli()
    has_mi = check_managed_identity()
    
    search_key = os.getenv("AZURE_SEARCH_KEY")
    openai_key = os.getenv("AZURE_OPENAI_KEY_41") or os.getenv("AZURE_OPENAI_KEY")
    doc_key = os.getenv("DOCUMENT_INTEL_KEY")
    
    print("\n📋 Immediate Actions:")
    
    if not search_key and not openai_key and not doc_key:
        print("1. 🔑 IMMEDIATE FIX: Add API keys to your .env file:")
        print("   AZURE_SEARCH_KEY=your_search_key_here")
        print("   AZURE_OPENAI_KEY_41=your_openai_key_here") 
        print("   DOCUMENT_INTEL_KEY=your_doc_intel_key_here")
        print("")
        print("2. 🔐 LONG-TERM: Configure managed identity RBAC roles")
    
    if has_cli and not has_mi:
        print("3. 🚀 You're using Azure CLI - assign RBAC roles to your user:")
        print("   az role assignment create --assignee $(az account show --query user.name -o tsv) \\")
        print("     --role 'Search Service Contributor' \\")
        print("     --scope /subscriptions/YOUR_SUB/resourceGroups/YOUR_RG/providers/Microsoft.Search/searchServices/YOUR_SEARCH")
    
    if has_mi:
        print("4. 🤖 You have managed identity - assign RBAC roles to your VM:")
        print("   # Get your VM's managed identity principal ID")
        print("   PRINCIPAL_ID=$(az vm identity show --name YOUR_VM_NAME --resource-group YOUR_RG --query principalId -o tsv)")
        print("   # Assign roles")
        print("   az role assignment create --assignee $PRINCIPAL_ID --role 'Search Service Contributor' --scope YOUR_SEARCH_RESOURCE_ID")

def main():
    """Main diagnostics function."""
    print("🔒 Private Endpoint Diagnostics for Agentic RAG Demo")
    print("=" * 60)
    print("This script will help diagnose authentication and connectivity issues")
    print("with your private endpoint Azure resources.\n")
    
    # Load environment variables from .env file if it exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print(f"📄 Loading environment from: {env_file}")
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print("✅ Environment variables loaded")
        except ImportError:
            print("⚠️ python-dotenv not installed, using system environment")
        except Exception as e:
            print(f"⚠️ Error loading .env file: {str(e)}")
    else:
        print("⚠️ No .env file found, using system environment")
    
    print()
    
    # Run all diagnostics
    check_environment_variables()
    check_azure_cli()
    check_managed_identity()
    check_network_connectivity()
    test_service_connections()
    generate_fix_recommendations()
    
    print("\n" + "=" * 60)
    print("🎯 Diagnostics Complete!")
    print("   Use the recommendations above to fix authentication issues.")
    print("   For more detailed help, run the Streamlit app and go to:")
    print("   Health Check → Private Endpoint Check")

if __name__ == "__main__":
    main()
