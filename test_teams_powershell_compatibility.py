#!/usr/bin/env python3
"""
Teams PowerShell Module Compatibility Checker
===========================================
This script tests the MicrosoftTeams PowerShell module and checks authentication compatibility.
"""

import subprocess
import platform
import tempfile
import os

def test_teams_module_compatibility():
    """Test Teams PowerShell module authentication methods"""
    
    print("🔍 Testing Teams PowerShell Module Compatibility")
    print("=" * 55)
    
    # Get credentials
    tenant_id = os.getenv("M365_TENANT_ID")
    client_id = os.getenv("M365_CLIENT_ID")
    client_secret = os.getenv("M365_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        print("❌ M365 credentials not found. Please set environment variables:")
        print("   - M365_TENANT_ID")
        print("   - M365_CLIENT_ID") 
        print("   - M365_CLIENT_SECRET")
        return False
    
    # PowerShell script to test authentication methods
    test_script = f'''
Write-Host "🔍 Testing MicrosoftTeams PowerShell Module Compatibility"
Write-Host "=" * 55

try {{
    # Check if module is available
    if (-not (Get-Module -ListAvailable -Name MicrosoftTeams)) {{
        Write-Host "📦 MicrosoftTeams module not found, installing..."
        Install-Module -Name MicrosoftTeams -Force -AllowClobber -Scope CurrentUser -Repository PSGallery
    }}
    
    # Import and get version
    Import-Module MicrosoftTeams -Force
    $Module = Get-Module MicrosoftTeams
    Write-Host "📋 Module Version: $($Module.Version)"
    
    # Test authentication methods
    Write-Host ""
    Write-Host "🧪 Testing Authentication Methods:"
    
    # Method 1: Modern app-based authentication
    Write-Host "1. Testing ApplicationId + ClientSecret authentication..."
    try {{
        Connect-MicrosoftTeams -TenantId "{tenant_id}" -ApplicationId "{client_id}" -ClientSecret "{client_secret}" -ErrorAction Stop
        Write-Host "   ✅ ApplicationId authentication: SUPPORTED"
        Disconnect-MicrosoftTeams -Confirm:$false
        $Method1 = $true
    }} catch {{
        Write-Host "   ❌ ApplicationId authentication: NOT SUPPORTED"
        Write-Host "   Error: $($_.Exception.Message)"
        $Method1 = $false
    }}
    
    Start-Sleep -Seconds 2
    
    # Method 2: Credential-based authentication
    Write-Host "2. Testing Credential-based authentication..."
    try {{
        $SecurePassword = ConvertTo-SecureString "{client_secret}" -AsPlainText -Force
        $Credential = New-Object System.Management.Automation.PSCredential("{client_id}", $SecurePassword)
        Connect-MicrosoftTeams -TenantId "{tenant_id}" -Credential $Credential -ErrorAction Stop
        Write-Host "   ✅ Credential authentication: SUPPORTED"
        Disconnect-MicrosoftTeams -Confirm:$false
        $Method2 = $true
    }} catch {{
        Write-Host "   ❌ Credential authentication: NOT SUPPORTED"
        Write-Host "   Error: $($_.Exception.Message)"
        $Method2 = $false
    }}
    
    Start-Sleep -Seconds 2
    
    # Method 3: Basic tenant connection
    Write-Host "3. Testing basic tenant connection..."
    try {{
        Connect-MicrosoftTeams -TenantId "{tenant_id}" -ErrorAction Stop
        Write-Host "   ✅ Basic tenant authentication: SUPPORTED"
        Disconnect-MicrosoftTeams -Confirm:$false
        $Method3 = $true
    }} catch {{
        Write-Host "   ❌ Basic tenant authentication: NOT SUPPORTED"
        Write-Host "   Error: $($_.Exception.Message)"
        $Method3 = $false
    }}
    
    # Summary
    Write-Host ""
    Write-Host "📊 Compatibility Summary:"
    Write-Host "   Module Version: $($Module.Version)"
    Write-Host "   ApplicationId Auth: $(if ($Method1) {{'✅ Supported'}} else {{'❌ Not Supported'}})"
    Write-Host "   Credential Auth: $(if ($Method2) {{'✅ Supported'}} else {{'❌ Not Supported'}})"
    Write-Host "   Basic Auth: $(if ($Method3) {{'✅ Supported'}} else {{'❌ Not Supported'}})"
    
    # Recommendation
    Write-Host ""
    Write-Host "💡 Recommendation:"
    if ($Method1) {{
        Write-Host "   Use ApplicationId + ClientSecret authentication (most secure)"
    }} elseif ($Method2) {{
        Write-Host "   Use Credential-based authentication (compatible with older modules)"
    }} elseif ($Method3) {{
        Write-Host "   Use basic tenant authentication (may require interactive login)"
    }} else {{
        Write-Host "   ⚠️ No authentication methods worked - check credentials and permissions"
    }}
    
    # JSON output for parsing
    $Result = @{{
        "success" = ($Method1 -or $Method2 -or $Method3)
        "module_version" = $Module.Version.ToString()
        "applicationid_auth" = $Method1
        "credential_auth" = $Method2
        "basic_auth" = $Method3
    }}
    
    Write-Host ""
    Write-Host "RESULT_JSON:" + ($Result | ConvertTo-Json -Compress)
    
}} catch {{
    Write-Host "❌ Module test failed: $($_.Exception.Message)"
    $ErrorResult = @{{
        "success" = $false
        "error" = $_.Exception.Message
    }}
    Write-Host "RESULT_JSON:" + ($ErrorResult | ConvertTo-Json -Compress)
    exit 1
}}
'''
    
    # Create temporary script file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as temp_script:
        temp_script.write(test_script)
        script_path = temp_script.name
    
    try:
        # Determine PowerShell executable
        system = platform.system().lower()
        if system == "windows":
            ps_cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path]
        else:
            ps_cmd = ["pwsh", "-File", script_path]
        
        print(f"Executing compatibility test...")
        
        # Run the script
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=120)
        
        print("🔍 Test Results:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Errors:")
            print(result.stderr)
        
        # Parse JSON result
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if line.startswith("RESULT_JSON:"):
                try:
                    import json
                    json_str = line.replace("RESULT_JSON:", "")
                    json_result = json.loads(json_str)
                    
                    print("\n📋 Parsed Results:")
                    print(f"   Success: {json_result.get('success', False)}")
                    print(f"   Module Version: {json_result.get('module_version', 'Unknown')}")
                    print(f"   ApplicationId Auth: {json_result.get('applicationid_auth', False)}")
                    print(f"   Credential Auth: {json_result.get('credential_auth', False)}")
                    print(f"   Basic Auth: {json_result.get('basic_auth', False)}")
                    
                    return json_result.get('success', False)
                except json.JSONDecodeError:
                    print("⚠️ Could not parse JSON result")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except FileNotFoundError:
        print(f"❌ PowerShell not found for {system}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            os.unlink(script_path)
        except:
            pass

def main():
    """Main function"""
    success = test_teams_module_compatibility()
    
    print("\n" + "=" * 55)
    if success:
        print("✅ Teams PowerShell module compatibility test passed!")
        print("🚀 PowerShell deployment should work with the updated script.")
    else:
        print("❌ Teams PowerShell module compatibility test failed!")
        print("🔧 Manual deployment or alternative methods may be needed.")
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
