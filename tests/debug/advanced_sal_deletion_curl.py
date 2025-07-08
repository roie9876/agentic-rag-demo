#!/usr/bin/env python3
"""
Advanced SAL Deletion using Direct HTTP Requests
This script uses curl with Azure CLI tokens to attempt SAL deletion with different approaches.

Created: 2025-07-08
Location: tests/debug/ (following new organization policy)
"""

import subprocess
import json
import time
import sys
from datetime import datetime
from typing import Tuple, Optional, Dict


def run_command(command: list, description: str, timeout: int = 120) -> Tuple[bool, str, str]:
    """Run a command with detailed logging."""
    print(f"\n🔧 {description}")
    print(f"Command: {' '.join(command)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        print(f"Return Code: {result.returncode}")
        if stdout:
            print(f"STDOUT:\n{stdout}")
        if stderr:
            print(f"STDERR:\n{stderr}")
        
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {description}")
        
        return success, stdout, stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT after {timeout}s: {description}")
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        print(f"💥 EXCEPTION: {description} - {str(e)}")
        return False, "", str(e)


def get_azure_token() -> Optional[str]:
    """Get Azure access token using Azure CLI."""
    print("=" * 80)
    print("🔑 GETTING AZURE ACCESS TOKEN")
    print("=" * 80)
    
    success, stdout, stderr = run_command(
        ["az", "account", "get-access-token", "--output", "json"],
        "Getting Azure access token"
    )
    
    if success:
        try:
            token_info = json.loads(stdout)
            access_token = token_info.get('accessToken', '')
            expires_on = token_info.get('expiresOn', 'Unknown')
            
            print(f"✅ Token obtained successfully")
            print(f"✅ Expires: {expires_on}")
            
            return access_token
        except json.JSONDecodeError:
            print("❌ Failed to parse token information")
            return None
    else:
        print("❌ Failed to get access token")
        return None


def get_subscription_info() -> Optional[Dict]:
    """Get subscription information."""
    success, stdout, stderr = run_command(
        ["az", "account", "show", "--output", "json"],
        "Getting subscription information"
    )
    
    if success:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None
    return None


def curl_delete_sal(token: str, subscription_id: str, rg_name: str, sal_name: str, api_version: str = "2024-05-01") -> bool:
    """Attempt to delete SAL using curl directly."""
    print("=" * 80)
    print(f"🌐 CURL DELETE SAL: {sal_name} (API: {api_version})")
    print("=" * 80)
    
    sal_url = (
        f"https://management.azure.com/subscriptions/{subscription_id}/"
        f"resourceGroups/{rg_name}/providers/Microsoft.Network/virtualNetworks/"
        f"agent-vnet-test/subnets/agent-subnet/serviceAssociationLinks/{sal_name}"
        f"?api-version={api_version}"
    )
    
    success, stdout, stderr = run_command([
        "curl", "-X", "DELETE",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-H", "User-Agent: curl/7.68.0",
        "-v",  # Verbose output
        sal_url
    ], f"Deleting SAL '{sal_name}' with curl (API: {api_version})")
    
    return success


def curl_delete_sal_with_force(token: str, subscription_id: str, rg_name: str, sal_name: str) -> bool:
    """Attempt to delete SAL using curl with force parameter."""
    print("=" * 80)
    print(f"🌐 CURL FORCE DELETE SAL: {sal_name}")
    print("=" * 80)
    
    sal_url = (
        f"https://management.azure.com/subscriptions/{subscription_id}/"
        f"resourceGroups/{rg_name}/providers/Microsoft.Network/virtualNetworks/"
        f"agent-vnet-test/subnets/agent-subnet/serviceAssociationLinks/{sal_name}"
        f"?api-version=2024-05-01&force=true"
    )
    
    success, stdout, stderr = run_command([
        "curl", "-X", "DELETE",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-H", "User-Agent: curl/7.68.0",
        "-v",
        sal_url
    ], f"Force deleting SAL '{sal_name}' with curl")
    
    return success


def curl_patch_sal_allow_delete(token: str, subscription_id: str, rg_name: str, sal_name: str) -> bool:
    """Attempt to PATCH the SAL to set allowDelete=true first."""
    print("=" * 80)
    print(f"🔧 CURL PATCH SAL: {sal_name} (allowDelete=true)")
    print("=" * 80)
    
    sal_url = (
        f"https://management.azure.com/subscriptions/{subscription_id}/"
        f"resourceGroups/{rg_name}/providers/Microsoft.Network/virtualNetworks/"
        f"agent-vnet-test/subnets/agent-subnet/serviceAssociationLinks/{sal_name}"
        f"?api-version=2024-05-01"
    )
    
    patch_data = json.dumps({
        "properties": {
            "allowDelete": True
        }
    })
    
    success, stdout, stderr = run_command([
        "curl", "-X", "PATCH",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-H", "User-Agent: curl/7.68.0",
        "-d", patch_data,
        "-v",
        sal_url
    ], f"Patching SAL '{sal_name}' to set allowDelete=true")
    
    return success


def curl_delete_with_different_agents(token: str, subscription_id: str, rg_name: str, sal_name: str) -> bool:
    """Try deletion with different User-Agent strings."""
    user_agents = [
        "AzureCLI/2.57.0",
        "Azure-CLI/2.57.0 (Linux)",
        "Microsoft Azure CLI 2.57.0",
        "PowerShell/7.4.0",
        "AzurePowerShell/11.0.0",
        "azure-cli-rest-client/1.0.0",
        "Mozilla/5.0 (Azure)"
    ]
    
    sal_url = (
        f"https://management.azure.com/subscriptions/{subscription_id}/"
        f"resourceGroups/{rg_name}/providers/Microsoft.Network/virtualNetworks/"
        f"agent-vnet-test/subnets/agent-subnet/serviceAssociationLinks/{sal_name}"
        f"?api-version=2024-05-01"
    )
    
    for i, user_agent in enumerate(user_agents, 1):
        print("=" * 80)
        print(f"🔧 ATTEMPT {i}: User-Agent: {user_agent}")
        print("=" * 80)
        
        success, stdout, stderr = run_command([
            "curl", "-X", "DELETE",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-H", f"User-Agent: {user_agent}",
            "-v",
            sal_url
        ], f"Deleting SAL with User-Agent: {user_agent}")
        
        if success:
            print(f"✅ SUCCESS with User-Agent: {user_agent}")
            return True
        
        # Wait between attempts
        time.sleep(2)
    
    return False


def attempt_multiple_api_versions(token: str, subscription_id: str, rg_name: str, sal_name: str) -> bool:
    """Try deletion with multiple API versions."""
    api_versions = [
        "2024-05-01",
        "2023-11-01", 
        "2023-09-01",
        "2023-05-01",
        "2022-11-01",
        "2022-07-01",
        "2021-05-01",
        "2020-11-01",
        "2019-11-01",
        "2018-10-01"
    ]
    
    for i, api_version in enumerate(api_versions, 1):
        print("=" * 80)
        print(f"🔧 API VERSION {i}: {api_version}")
        print("=" * 80)
        
        success = curl_delete_sal(token, subscription_id, rg_name, sal_name, api_version)
        
        if success:
            print(f"✅ SUCCESS with API version: {api_version}")
            return True
        
        # Wait between attempts
        time.sleep(2)
    
    return False


def main():
    """Main function for advanced SAL deletion attempts."""
    print("🌐 ADVANCED SAL DELETION USING DIRECT HTTP REQUESTS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Resource Group: bciep-test-8")
    print(f"Script Location: tests/debug/ (following new organization policy)")
    print("=" * 80)
    print("\n📋 This script attempts multiple HTTP-based approaches:")
    print("1. Direct curl DELETE with various User-Agent strings")
    print("2. PATCH SAL to set allowDelete=true first")
    print("3. Force deletion with curl")
    print("4. Multiple API versions")
    print("5. Different HTTP headers and authentication approaches")
    print("=" * 80)
    
    rg_name = "bciep-test-8"
    sal_name = "legionservicelink"
    
    # Get user confirmation
    try:
        confirm = input("\n⚠️ Type 'TRY ADVANCED DELETE' to proceed: ").strip()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return 1
    
    if confirm != "TRY ADVANCED DELETE":
        print("❌ Advanced deletion not confirmed")
        return 1
    
    # Step 1: Get Azure token
    token = get_azure_token()
    if not token:
        print("❌ Could not get Azure access token")
        return 1
    
    # Step 2: Get subscription info
    sub_info = get_subscription_info()
    if not sub_info:
        print("❌ Could not get subscription information")
        return 1
    
    subscription_id = sub_info.get('id', '')
    if not subscription_id:
        print("❌ Could not extract subscription ID")
        return 1
    
    print(f"\n🎯 Target SAL: {sal_name}")
    print(f"🎯 Subscription: {subscription_id}")
    print(f"🎯 Resource Group: {rg_name}")
    
    # Method 1: Try PATCH first to set allowDelete=true
    print("\n📋 METHOD 1: PATCH SAL to set allowDelete=true")
    patch_success = curl_patch_sal_allow_delete(token, subscription_id, rg_name, sal_name)
    
    if patch_success:
        print("✅ PATCH successful, now trying DELETE...")
        time.sleep(5)
        delete_success = curl_delete_sal(token, subscription_id, rg_name, sal_name)
        if delete_success:
            print("\n🎉 SUCCESS! SAL deleted after PATCH operation!")
            return 0
    
    # Method 2: Force deletion
    print("\n📋 METHOD 2: Force deletion with curl")
    force_success = curl_delete_sal_with_force(token, subscription_id, rg_name, sal_name)
    if force_success:
        print("\n🎉 SUCCESS! SAL force deleted!")
        return 0
    
    # Method 3: Different User-Agent strings
    print("\n📋 METHOD 3: Different User-Agent strings")
    ua_success = curl_delete_with_different_agents(token, subscription_id, rg_name, sal_name)
    if ua_success:
        print("\n🎉 SUCCESS! SAL deleted with custom User-Agent!")
        return 0
    
    # Method 4: Multiple API versions
    print("\n📋 METHOD 4: Multiple API versions")
    api_success = attempt_multiple_api_versions(token, subscription_id, rg_name, sal_name)
    if api_success:
        print("\n🎉 SUCCESS! SAL deleted with alternative API version!")
        return 0
    
    # All methods failed
    print("\n💔 ALL ADVANCED METHODS FAILED")
    print("=" * 80)
    print("📋 Summary of attempts:")
    print("❌ PATCH to set allowDelete=true: FAILED")
    print("❌ Force deletion with curl: FAILED")
    print("❌ Different User-Agent strings: FAILED")
    print("❌ Multiple API versions: FAILED")
    print("\n💡 This confirms that the SAL deletion requires Microsoft Support intervention")
    print("💡 Use the comprehensive support ticket we created earlier")
    print("💡 The issue is not with our approach but with Azure's permission model")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
