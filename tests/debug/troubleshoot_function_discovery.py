#!/usr/bin/env python3
"""
Troubleshoot Function App Discovery Issues
"""

import subprocess
import json
import os
import sys
from azure.identity import DefaultAzureCredential
from azure.mgmt.web import WebSiteManagementClient

def test_azure_cli():
    """Test Azure CLI authentication and subscription access"""
    print("🔍 Testing Azure CLI Authentication")
    print("=" * 50)
    
    try:
        # Test basic Azure CLI connectivity
        result = subprocess.run(["az", "account", "show"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            account_info = json.loads(result.stdout)
            print(f"✅ Azure CLI is authenticated")
            print(f"   Current subscription: {account_info.get('name', 'Unknown')}")
            print(f"   Subscription ID: {account_info.get('id', 'Unknown')}")
            print(f"   User: {account_info.get('user', {}).get('name', 'Unknown')}")
            return account_info.get('id', '')
        else:
            print(f"❌ Azure CLI authentication failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing Azure CLI: {e}")
        return None

def test_subscription_access(subscription_id):
    """Test access to all subscriptions"""
    print(f"\n🔍 Testing Subscription Access")
    print("=" * 50)
    
    try:
        result = subprocess.run(["az", "account", "list", "-o", "json"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            subscriptions = json.loads(result.stdout)
            print(f"✅ Found {len(subscriptions)} accessible subscriptions:")
            
            for sub in subscriptions:
                sub_id = sub.get('id', '')
                sub_name = sub.get('name', 'Unknown')
                state = sub.get('state', 'Unknown')
                is_default = sub.get('isDefault', False)
                
                marker = " (current)" if is_default or sub_id == subscription_id else ""
                print(f"   • {sub_name} ({sub_id}) - {state}{marker}")
                
            return subscriptions
        else:
            print(f"❌ Failed to list subscriptions: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"❌ Error listing subscriptions: {e}")
        return []

def test_function_apps_cli(subscription_id):
    """Test Function App discovery via Azure CLI"""
    print(f"\n🔍 Testing Function Apps via Azure CLI")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            "az", "functionapp", "list",
            "--subscription", subscription_id,
            "-o", "json"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            apps = json.loads(result.stdout)
            print(f"✅ Found {len(apps)} Function Apps via CLI:")
            
            for app in apps:
                name = app.get('name', 'Unknown')
                rg = app.get('resourceGroup', 'Unknown')
                kind = app.get('kind', 'Unknown')
                state = app.get('state', 'Unknown')
                location = app.get('location', 'Unknown')
                
                print(f"   • {name} ({rg}) - {kind} - {state} - {location}")
                
            return apps
        else:
            print(f"❌ Failed to list Function Apps: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"❌ Error listing Function Apps: {e}")
        return []

def test_function_apps_sdk(subscription_id):
    """Test Function App discovery via Azure SDK"""
    print(f"\n🔍 Testing Function Apps via Azure SDK")
    print("=" * 50)
    
    try:
        cred = DefaultAzureCredential()
        wcli = WebSiteManagementClient(cred, subscription_id)
        
        apps = []
        for site in wcli.web_apps.list():
            if site.kind and "functionapp" in site.kind:
                apps.append({
                    'name': site.name,
                    'resource_group': site.resource_group,
                    'kind': site.kind,
                    'location': site.location,
                    'state': site.state,
                    'default_hostname': getattr(site, 'default_host_name', 'Unknown')
                })
                
        print(f"✅ Found {len(apps)} Function Apps via SDK:")
        
        for app in apps:
            print(f"   • {app['name']} ({app['resource_group']}) - {app['kind']} - {app['state']} - {app['location']}")
            
        return apps
        
    except Exception as e:
        print(f"❌ Error using Azure SDK: {e}")
        return []

def main():
    print("🚀 Azure Function App Discovery Troubleshooting")
    print("=" * 60)
    
    # Test 1: Azure CLI Authentication
    subscription_id = test_azure_cli()
    if not subscription_id:
        print("\n❌ Cannot proceed without Azure CLI authentication.")
        print("💡 Try running: az login")
        return
        
    # Test 2: Subscription Access
    subscriptions = test_subscription_access(subscription_id)
    if not subscriptions:
        print("\n❌ Cannot access subscriptions.")
        return
        
    # Test 3: Function Apps via CLI
    cli_apps = test_function_apps_cli(subscription_id)
    
    # Test 4: Function Apps via SDK
    sdk_apps = test_function_apps_sdk(subscription_id)
    
    # Summary
    print(f"\n📊 Summary")
    print("=" * 50)
    print(f"Current Subscription: {subscription_id}")
    print(f"Function Apps found via CLI: {len(cli_apps)}")
    print(f"Function Apps found via SDK: {len(sdk_apps)}")
    
    if cli_apps and not sdk_apps:
        print("\n💡 CLI works but SDK doesn't - this suggests a permission or credential issue")
    elif not cli_apps and not sdk_apps:
        print("\n💡 Neither CLI nor SDK found Function Apps - check if they exist in this subscription")
    elif cli_apps and sdk_apps:
        print("\n✅ Both methods work - the issue might be in the Streamlit app")
        
    print(f"\n🔧 Next Steps:")
    print("1. If no Function Apps found, verify they exist in Azure Portal")
    print("2. If CLI works but SDK doesn't, check Azure permissions")
    print("3. If both work, try the 🔄 Refresh button in the Streamlit app")
    print("4. If issues persist, use manual input in the Function Config tab")

if __name__ == "__main__":
    main()
