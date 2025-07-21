#!/usr/bin/env python3
"""
Cross-Tenant AI Services Solution Script

This script provides solutions for the cross-tenant subscription authentication issue
where AI Services accounts are visible in Azure Portal but not accessible via API.

Usage:
    python3 tests/debug/cross_tenant_ai_services_solution.py
"""

import subprocess
import json
import os
import sys
from typing import Dict, List, Optional

def run_command(cmd: str, capture_output: bool = True) -> tuple:
    """Run a command and return (success, output, error)."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def get_current_login_info() -> Dict:
    """Get current Azure CLI login information."""
    print("🔍 Checking current Azure CLI login status...")
    
    # Get current account
    success, output, error = run_command("az account show --output json")
    if not success:
        print(f"❌ Not logged in to Azure CLI: {error}")
        return {}
    
    try:
        account_info = json.loads(output)
        print(f"✅ Logged in as: {account_info.get('user', {}).get('name', 'Unknown')}")
        print(f"✅ Current subscription: {account_info.get('name', 'Unknown')} ({account_info.get('id', 'Unknown')[:8]}...)")
        print(f"✅ Tenant ID: {account_info.get('tenantId', 'Unknown')}")
        return account_info
    except json.JSONDecodeError:
        print(f"❌ Failed to parse account info: {output}")
        return {}

def list_all_subscriptions() -> List[Dict]:
    """List all available subscriptions."""
    print("\n🔍 Listing all available subscriptions...")
    
    success, output, error = run_command("az account list --output json")
    if not success:
        print(f"❌ Failed to list subscriptions: {error}")
        return []
    
    try:
        subscriptions = json.loads(output)
        print(f"✅ Found {len(subscriptions)} subscription(s)")
        
        for i, sub in enumerate(subscriptions):
            status = "✅" if sub.get('state') == 'Enabled' else "❌"
            print(f"  {i+1}. {status} {sub.get('name', 'Unknown')} ({sub.get('id', 'Unknown')[:8]}...)")
            print(f"     Tenant: {sub.get('tenantId', 'Unknown')}")
            print(f"     State: {sub.get('state', 'Unknown')}")
        
        return subscriptions
    except json.JSONDecodeError:
        print(f"❌ Failed to parse subscriptions: {output}")
        return []

def check_cognitive_services_in_subscription(subscription_id: str, subscription_name: str) -> List[Dict]:
    """Check for Cognitive Services accounts in a specific subscription."""
    print(f"\n🔍 Checking Cognitive Services in subscription: {subscription_name} ({subscription_id[:8]}...)")
    
    # Set the subscription context
    success, output, error = run_command(f"az account set --subscription {subscription_id}")
    if not success:
        print(f"❌ Failed to set subscription context: {error}")
        return []
    
    # List cognitive services accounts
    cmd = f"az cognitiveservices account list --subscription {subscription_id} --output json"
    success, output, error = run_command(cmd)
    
    if not success:
        print(f"❌ Failed to list Cognitive Services: {error}")
        if "InvalidAuthenticationTokenTenant" in error:
            print("🔐 ISSUE DETECTED: Cross-tenant authentication error")
            print("   The subscription is in a different Azure AD tenant")
        return []
    
    try:
        accounts = json.loads(output)
        print(f"✅ Found {len(accounts)} Cognitive Services account(s)")
        
        ai_services_count = 0
        for account in accounts:
            kind = account.get('kind', 'Unknown')
            name = account.get('name', 'Unknown')
            location = account.get('location', 'Unknown')
            
            if kind == 'AIServices':
                print(f"  🎯 AI SERVICES: {name} ({location}) - ✅ SUITABLE FOR AI FOUNDRY")
                ai_services_count += 1
            else:
                print(f"  📋 {kind}: {name} ({location}) - ❌ Not suitable for AI Foundry")
        
        print(f"💡 AI Services accounts suitable for AI Foundry: {ai_services_count}")
        return accounts
        
    except json.JSONDecodeError:
        print(f"❌ Failed to parse Cognitive Services accounts: {output}")
        return []

def provide_solutions(current_account: Dict, subscriptions: List[Dict], findings: Dict[str, List[Dict]]):
    """Provide solutions based on the analysis."""
    print("\n" + "="*80)
    print("🛠️  SOLUTION RECOMMENDATIONS")
    print("="*80)
    
    current_sub_id = current_account.get('id')
    current_tenant = current_account.get('tenantId')
    
    # Count AI Services in each subscription
    accessible_ai_services = 0
    inaccessible_ai_services = 0
    accessible_subscription = None
    
    for sub_id, accounts in findings.items():
        if sub_id == current_sub_id:
            accessible_ai_services = sum(1 for acc in accounts if acc.get('kind') == 'AIServices')
            accessible_subscription = sub_id
        else:
            # Check if this subscription has AI Services (even if inaccessible)
            for sub in subscriptions:
                if sub['id'] == sub_id and sub.get('tenantId') != current_tenant:
                    # This subscription is in a different tenant and likely has AI Services
                    # based on the user's original issue
                    inaccessible_ai_services += 1  # Estimate based on context
    
    print(f"📊 ANALYSIS SUMMARY:")
    print(f"   Current subscription AI Services: {accessible_ai_services}")
    print(f"   Cross-tenant AI Services (estimated): {inaccessible_ai_services}")
    
    if accessible_ai_services > 0:
        print("\n✅ SOLUTION 1: Use Existing AI Services (RECOMMENDED)")
        print("   You have AI Services accounts in your current subscription!")
        print("   The multi-subscription discovery should work now.")
        print("   🎯 Action: Go back to the AI Foundry tab and scan again.")
        
    elif inaccessible_ai_services > 0 or len(findings) > 1:
        print("\n⚠️  SOLUTION 2: Cross-Tenant Authentication (ADVANCED)")
        print("   Your AI Services accounts are in a different Azure AD tenant.")
        
        # Find the other tenant
        other_tenants = set()
        for sub in subscriptions:
            if sub.get('tenantId') != current_tenant:
                other_tenants.add(sub.get('tenantId'))
        
        if other_tenants:
            print(f"   Other tenant(s): {', '.join(other_tenants)}")
            print("   🎯 Actions:")
            print("   1. Login to the other tenant:")
            for tenant in other_tenants:
                print(f"      az login --tenant {tenant}")
            print("   2. Re-run the AI Foundry discovery")
            print("   3. Or use tenant-specific authentication in your app")
    
    print("\n✅ SOLUTION 3: Create New AI Services Account (EASIEST)")
    print("   Create a new AI Services account in your current accessible subscription.")
    print("   🎯 Actions:")
    print(f"   Subscription: {current_account.get('name')} ({current_sub_id[:8]}...)")
    print("   Command:")
    print(f"""   az cognitiveservices account create \\
       --name ai-foundry-services-$(date +%s) \\
       --resource-group private-rg \\
       --kind AIServices \\
       --sku S0 \\
       --location swedencentral \\
       --subscription {current_sub_id} \\
       --yes""")
    
    print("\n💡 SOLUTION 4: Azure Portal Cross-Tenant Access")
    print("   Sometimes the Azure Portal shows resources from multiple tenants,")
    print("   but API access requires explicit tenant authentication.")
    print("   🎯 Actions:")
    print("   1. In Azure Portal, check which tenant the AI Services are in")
    print("   2. Use 'az login --tenant <tenant-id>' to switch")
    print("   3. Set AZURE_TENANT_ID environment variable if needed")

def create_ai_services_account():
    """Interactive creation of AI Services account."""
    print("\n" + "="*80)
    print("🚀 CREATE AI SERVICES ACCOUNT")
    print("="*80)
    
    # Get current subscription
    success, output, error = run_command("az account show --output json")
    if not success:
        print("❌ Not logged in to Azure CLI")
        return False
    
    try:
        account_info = json.loads(output)
        subscription_id = account_info.get('id')
        subscription_name = account_info.get('name')
        print(f"✅ Target subscription: {subscription_name} ({subscription_id[:8]}...)")
    except:
        print("❌ Failed to get subscription info")
        return False
    
    # Get available resource groups
    print("\n🔍 Finding resource groups...")
    success, output, error = run_command("az group list --query '[].name' --output tsv")
    if success and output:
        rgs = output.strip().split('\n')
        print(f"✅ Found {len(rgs)} resource group(s): {', '.join(rgs)}")
        
        # Use the first resource group or let user choose
        if rgs:
            target_rg = rgs[0]  # Use first available
            print(f"🎯 Using resource group: {target_rg}")
        else:
            print("❌ No resource groups found")
            return False
    else:
        target_rg = "private-rg"  # Fallback based on earlier debugging
        print(f"🎯 Using default resource group: {target_rg}")
    
    # Generate unique name
    import time
    timestamp = int(time.time()) % 100000
    account_name = f"ai-foundry-{timestamp}"
    
    print(f"\n🚀 Creating AI Services account: {account_name}")
    print(f"   Resource Group: {target_rg}")
    print(f"   Location: swedencentral")
    print(f"   SKU: S0 (Standard)")
    
    # Ask for confirmation
    response = input("\n❓ Proceed with creation? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Creation cancelled")
        return False
    
    # Create the account
    create_cmd = f"""az cognitiveservices account create \\
    --name {account_name} \\
    --resource-group {target_rg} \\
    --kind AIServices \\
    --sku S0 \\
    --location swedencentral \\
    --subscription {subscription_id} \\
    --yes"""
    
    print(f"\n⏳ Running: {create_cmd}")
    success, output, error = run_command(create_cmd, capture_output=False)
    
    if success:
        print(f"✅ AI Services account created successfully!")
        print(f"   Account name: {account_name}")
        print(f"   Endpoint: https://{account_name}.services.ai.azure.com")
        print(f"   🎯 You can now use this with AI Foundry!")
        
        # Test the account
        print(f"\n🧪 Testing the new account...")
        test_cmd = f"az cognitiveservices account show --name {account_name} --resource-group {target_rg} --output json"
        success, output, error = run_command(test_cmd)
        
        if success:
            try:
                account_info = json.loads(output)
                endpoint = account_info.get('properties', {}).get('endpoint', 'Unknown')
                print(f"✅ Account verification successful!")
                print(f"   Endpoint: {endpoint}")
                print(f"   Kind: {account_info.get('kind')}")
                print(f"   Provisioning State: {account_info.get('properties', {}).get('provisioningState')}")
            except:
                print("✅ Account created but verification parsing failed")
        else:
            print("⚠️  Account created but verification failed")
        
        return True
    else:
        print(f"❌ Failed to create AI Services account: {error}")
        return False

def main():
    """Main function to run the cross-tenant AI Services solution analysis."""
    print("🔧 Cross-Tenant AI Services Solution Script")
    print("=" * 80)
    print("This script will analyze your Azure setup and provide solutions")
    print("for accessing AI Services accounts across different tenants.")
    print("=" * 80)
    
    # Step 1: Get current login info
    current_account = get_current_login_info()
    if not current_account:
        print("\n❌ Please login to Azure CLI first:")
        print("   az login")
        return 1
    
    # Step 2: List all subscriptions
    subscriptions = list_all_subscriptions()
    if not subscriptions:
        print("\n❌ No subscriptions found")
        return 1
    
    # Step 3: Check Cognitive Services in each subscription
    findings = {}
    for sub in subscriptions:
        if sub.get('state') == 'Enabled':
            sub_id = sub.get('id')
            sub_name = sub.get('name')
            accounts = check_cognitive_services_in_subscription(sub_id, sub_name)
            findings[sub_id] = accounts
    
    # Step 4: Provide solutions
    provide_solutions(current_account, subscriptions, findings)
    
    # Step 5: Offer to create AI Services account
    print("\n" + "="*80)
    response = input("❓ Would you like to create a new AI Services account? [y/N]: ").strip().lower()
    if response in ['y', 'yes']:
        create_ai_services_account()
    
    print("\n✅ Analysis complete! Use the solutions above to resolve the AI Foundry discovery issue.")
    print("🔄 After implementing a solution, go back to the AI Foundry tab and scan again.")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
