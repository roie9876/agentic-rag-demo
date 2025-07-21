#!/usr/bin/env python3
"""
Diagnostic script to compare Azure CLI vs Python SDK results.
This will help identify why the Python SDK sees different accounts than Azure CLI.
"""

import subprocess
import json
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/azureuser/agentic-rag-demo')

def run_command(cmd: str) -> tuple:
    """Run a command and return (success, output, error)."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def get_azure_cli_accounts():
    """Get Cognitive Services accounts using Azure CLI."""
    print("🔍 Getting accounts via Azure CLI...")
    
    # First, get current subscription
    success, output, error = run_command("az account show --output json")
    if not success:
        print(f"❌ Failed to get current subscription: {error}")
        return []
    
    try:
        current_sub = json.loads(output)
        subscription_id = current_sub.get('id')
        subscription_name = current_sub.get('name')
        print(f"✅ Current subscription: {subscription_name} ({subscription_id[:8]}...)")
    except:
        print("❌ Failed to parse current subscription")
        return []
    
    # Get Cognitive Services accounts
    cmd = f"az cognitiveservices account list --subscription {subscription_id} --output json"
    success, output, error = run_command(cmd)
    
    if not success:
        print(f"❌ Failed to list Cognitive Services via CLI: {error}")
        return []
    
    try:
        accounts = json.loads(output)
        print(f"✅ Azure CLI found {len(accounts)} Cognitive Services accounts")
        
        ai_services_count = 0
        for account in accounts:
            kind = account.get('kind', 'Unknown')
            name = account.get('name', 'Unknown')
            if kind == 'AIServices':
                ai_services_count += 1
                print(f"  🎯 CLI AIServices: {name}")
            else:
                print(f"  📋 CLI Other: {name} (kind: {kind})")
        
        print(f"💡 Azure CLI found {ai_services_count} AIServices accounts")
        return accounts
    except Exception as e:
        print(f"❌ Failed to parse CLI accounts: {e}")
        return []

def get_python_sdk_accounts():
    """Get Cognitive Services accounts using Python SDK."""
    print("\n🔍 Getting accounts via Python SDK...")
    
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
        
        # Get current subscription from CLI for consistency
        success, output, error = run_command("az account show --output json")
        if not success:
            print(f"❌ Failed to get subscription for SDK: {error}")
            return []
        
        current_sub = json.loads(output)
        subscription_id = current_sub.get('id')
        print(f"✅ Using subscription for SDK: {subscription_id[:8]}...")
        
        # Initialize SDK client
        credential = DefaultAzureCredential()
        client = CognitiveServicesManagementClient(credential, subscription_id)
        
        # List accounts
        accounts = list(client.accounts.list())
        print(f"✅ Python SDK found {len(accounts)} Cognitive Services accounts")
        
        ai_services_count = 0
        for account in accounts:
            kind = account.kind
            name = account.name
            if kind == 'AIServices':
                ai_services_count += 1
                print(f"  🎯 SDK AIServices: {name}")
            else:
                print(f"  📋 SDK Other: {name} (kind: {kind})")
        
        print(f"💡 Python SDK found {ai_services_count} AIServices accounts")
        return accounts
        
    except Exception as e:
        print(f"❌ Python SDK error: {e}")
        import traceback
        traceback.print_exc()
        return []

def compare_results(cli_accounts, sdk_accounts):
    """Compare the results from CLI vs SDK."""
    print("\n" + "="*80)
    print("🔬 COMPARISON ANALYSIS")
    print("="*80)
    
    cli_names = set(acc.get('name', 'Unknown') for acc in cli_accounts)
    sdk_names = set(acc.name for acc in sdk_accounts)
    
    print(f"📊 Account Count:")
    print(f"  - Azure CLI: {len(cli_accounts)} accounts")
    print(f"  - Python SDK: {len(sdk_accounts)} accounts")
    
    print(f"\n📋 Account Names:")
    print(f"  - CLI accounts: {sorted(cli_names)}")
    print(f"  - SDK accounts: {sorted(sdk_names)}")
    
    # Find differences
    only_in_cli = cli_names - sdk_names
    only_in_sdk = sdk_names - cli_names
    common_accounts = cli_names & sdk_names
    
    print(f"\n🔍 Differences:")
    print(f"  - ✅ Common accounts: {len(common_accounts)} -> {sorted(common_accounts)}")
    print(f"  - ❌ Only in CLI: {len(only_in_cli)} -> {sorted(only_in_cli)}")
    print(f"  - ⚠️  Only in SDK: {len(only_in_sdk)} -> {sorted(only_in_sdk)}")
    
    # Analyze AIServices specifically
    cli_ai_services = [acc for acc in cli_accounts if acc.get('kind') == 'AIServices']
    sdk_ai_services = [acc for acc in sdk_accounts if acc.kind == 'AIServices']
    
    print(f"\n🎯 AIServices Analysis:")
    print(f"  - CLI AIServices: {len(cli_ai_services)}")
    print(f"  - SDK AIServices: {len(sdk_ai_services)}")
    
    if len(cli_ai_services) != len(sdk_ai_services):
        print(f"  🚨 **MISMATCH DETECTED**: CLI and SDK see different AIServices accounts!")
        print(f"     This explains why the discovery service finds 0 accounts!")
        
        print(f"\n🔧 Possible Causes:")
        print(f"  1. **Subscription Context**: SDK might be using a different subscription")
        print(f"  2. **Authentication Scope**: SDK might have different permissions")
        print(f"  3. **Resource Group Filter**: SDK might be filtered to specific resource groups")
        print(f"  4. **API Version**: Different API versions might return different results")
        
        if only_in_cli:
            print(f"\n💡 **The missing AIServices accounts are only visible to CLI:**")
            for name in sorted(only_in_cli):
                # Find the account details
                for acc in cli_accounts:
                    if acc.get('name') == name and acc.get('kind') == 'AIServices':
                        location = acc.get('location', 'Unknown')
                        rg = acc.get('resourceGroup', 'Unknown')
                        print(f"     - {name} (location: {location}, RG: {rg})")
    else:
        print(f"  ✅ AIServices counts match - this is unexpected given the issue")

def diagnose_authentication():
    """Diagnose authentication differences between CLI and SDK."""
    print(f"\n🔐 Authentication Diagnosis:")
    
    # Check Azure CLI token
    success, output, error = run_command("az account get-access-token --output json")
    if success:
        try:
            token_info = json.loads(output)
            print(f"  ✅ CLI Token: Valid (expires: {token_info.get('expiresOn', 'Unknown')[:19]})")
        except:
            print(f"  ❌ CLI Token: Failed to parse")
    else:
        print(f"  ❌ CLI Token: {error}")
    
    # Check Python SDK authentication
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        # Try to get a token for the Cognitive Services scope
        token = credential.get_token("https://management.azure.com/.default")
        print(f"  ✅ SDK Token: Valid (expires: {token.expires_on})")
    except Exception as e:
        print(f"  ❌ SDK Token: {e}")

def main():
    """Main diagnostic function."""
    print("🔬 Azure CLI vs Python SDK Diagnostic Script")
    print("="*80)
    print("This will compare what Azure CLI sees vs what the Python SDK sees")
    print("to identify why the discovery service finds 0 AIServices accounts.")
    print("="*80)
    
    # Get accounts from both sources
    cli_accounts = get_azure_cli_accounts()
    sdk_accounts = get_python_sdk_accounts()
    
    # Compare results
    if cli_accounts or sdk_accounts:
        compare_results(cli_accounts, sdk_accounts)
        diagnose_authentication()
        
        print(f"\n🎯 **CONCLUSION**:")
        if len(cli_accounts) > len(sdk_accounts):
            print(f"  The Python SDK is missing accounts that Azure CLI can see.")
            print(f"  This explains why the discovery service returns 0 AIServices accounts.")
            print(f"  The fix is to resolve the SDK authentication or subscription context issue.")
        elif len(cli_accounts) == len(sdk_accounts):
            print(f"  Both CLI and SDK see the same number of accounts.")
            print(f"  The issue might be in the discovery service filtering logic.")
        else:
            print(f"  Unexpected: SDK sees more accounts than CLI.")
    else:
        print(f"❌ Failed to get accounts from both CLI and SDK")
    
    print(f"\n🔧 **NEXT STEPS**:")
    print(f"  1. If SDK is missing accounts, check subscription/authentication context")
    print(f"  2. If counts match, check discovery service filtering logic")
    print(f"  3. Ensure DefaultAzureCredential uses the same identity as Azure CLI")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
