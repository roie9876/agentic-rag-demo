#!/usr/bin/env python3
"""
Test script for M365 PowerShell deployment functionality
"""

import os
import sys
from pathlib import Path
import tempfile
import platform

def test_powershell_availability():
    """Test if PowerShell is available on the system"""
    import subprocess
    
    print("🔍 Testing PowerShell availability...")
    
    system = platform.system().lower()
    if system == "windows":
        ps_cmd = ["powershell.exe", "-Command", "Get-Host | Select-Object Version"]
    else:
        ps_cmd = ["pwsh", "-Command", "Get-Host | Select-Object Version"]
    
    try:
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ PowerShell available: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ PowerShell test failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print(f"❌ PowerShell not found for {system}")
        if system != "windows":
            print("💡 Install PowerShell Core: https://github.com/PowerShell/PowerShell")
        return False
    except subprocess.TimeoutExpired:
        print("❌ PowerShell test timed out")
        return False

def test_teams_module_check():
    """Test PowerShell script to check Teams module"""
    import subprocess
    
    print("🔍 Testing Teams module availability check...")
    
    script_content = '''
try {
    if (Get-Module -ListAvailable -Name MicrosoftTeams) {
        Write-Host "MicrosoftTeams module is available"
        $module = Get-Module -ListAvailable -Name MicrosoftTeams | Select-Object -First 1
        Write-Host "Version: $($module.Version)"
    } else {
        Write-Host "MicrosoftTeams module not found - would be installed automatically"
    }
} catch {
    Write-Host "Error checking Teams module: $($_.Exception.Message)"
}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as temp_script:
        temp_script.write(script_content)
        script_path = temp_script.name
    
    try:
        system = platform.system().lower()
        if system == "windows":
            ps_cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path]
        else:
            ps_cmd = ["pwsh", "-File", script_path]
        
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30)
        
        print(f"Teams module check output:")
        print(result.stdout)
        
        if result.stderr:
            print(f"Warnings/Errors: {result.stderr}")
        
        return result.returncode == 0
        
    finally:
        try:
            os.unlink(script_path)
        except:
            pass

def test_m365_credentials():
    """Test M365 credentials availability"""
    print("🔍 Testing M365 credentials...")
    
    tenant_id = os.getenv("M365_TENANT_ID")
    client_id = os.getenv("M365_CLIENT_ID")
    client_secret = os.getenv("M365_CLIENT_SECRET")
    
    if all([tenant_id, client_id, client_secret]):
        print("✅ M365 credentials found in environment")
        print(f"   Tenant ID: {tenant_id[:8]}..." if tenant_id else "   Tenant ID: Missing")
        print(f"   Client ID: {client_id[:8]}..." if client_id else "   Client ID: Missing")
        print(f"   Client Secret: {'*' * 8}" if client_secret else "   Client Secret: Missing")
        return True
    else:
        print("❌ M365 credentials missing")
        print("💡 Set these environment variables:")
        print("   - M365_TENANT_ID")
        print("   - M365_CLIENT_ID")
        print("   - M365_CLIENT_SECRET")
        return False

def main():
    """Run all tests"""
    print("🧪 M365 PowerShell Deployment Test Suite")
    print("=" * 50)
    
    results = []
    
    # Test PowerShell availability
    results.append(test_powershell_availability())
    print()
    
    # Test Teams module check
    results.append(test_teams_module_check())
    print()
    
    # Test M365 credentials
    results.append(test_m365_credentials())
    print()
    
    # Summary
    print("📊 Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All tests passed ({passed}/{total})")
        print("🚀 PowerShell deployment should work!")
    else:
        print(f"⚠️ {total - passed} test(s) failed ({passed}/{total})")
        print("🔧 Fix the issues above before attempting deployment")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
