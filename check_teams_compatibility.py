#!/usr/bin/env python3
"""
Teams Module Version Checker for M365 Agent Deployment
====================================================
This script helps determine the best deployment method based on your Teams PowerShell module version.
"""

import subprocess
import sys
import platform
from pathlib import Path

def check_teams_module_version():
    """Check the installed Teams PowerShell module version"""
    print("🔍 Checking Teams PowerShell Module Version...")
    print("=" * 50)
    
    try:
        # Determine PowerShell command based on OS
        if platform.system().lower() == "windows":
            ps_cmd = ["powershell.exe", "-Command"]
        else:
            ps_cmd = ["pwsh", "-Command"]
        
        # PowerShell command to check Teams module version
        check_command = """
        try {
            $TeamsModule = Get-Module MicrosoftTeams -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1
            if ($TeamsModule) {
                $Version = $TeamsModule.Version.ToString()
                $Location = $TeamsModule.ModuleBase
                Write-Host "TEAMS_MODULE_FOUND:$Version"
                Write-Host "LOCATION:$Location"
            } else {
                Write-Host "TEAMS_MODULE_NOT_FOUND"
            }
        } catch {
            Write-Host "TEAMS_MODULE_ERROR:$($_.Exception.Message)"
        }
        """
        
        result = subprocess.run(
            ps_cmd + [check_command],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            
            if "TEAMS_MODULE_FOUND:" in output:
                # Parse version and location
                lines = output.split('\n')
                version = None
                location = "Unknown"
                
                for line in lines:
                    if line.startswith("TEAMS_MODULE_FOUND:"):
                        version = line.split("TEAMS_MODULE_FOUND:")[1].strip()
                    elif line.startswith("LOCATION:"):
                        location = line.split("LOCATION:")[1].strip()
                
                if version:
                    print(f"✅ Microsoft Teams PowerShell Module Found")
                    print(f"   Version: {version}")
                    print(f"   Location: {location}")
                    print()
                    
                    # Analyze version and provide recommendations
                    version_parts = version.split('.')
                    major_version = int(version_parts[0]) if version_parts else 0
                
                if major_version >= 7:
                    print("🚨 TEAMS MODULE 7.x+ DETECTED")
                    print("=" * 40)
                    print("⚠️  Breaking changes in authentication!")
                    print("⚠️  Client secret authentication NO LONGER SUPPORTED")
                    print()
                    print("📋 RECOMMENDED DEPLOYMENT METHOD:")
                    print("   ✅ MANUAL UPLOAD in Teams Admin Center")
                    print("   ❌ PowerShell automation will likely FAIL")
                    print()
                    print("🔗 Manual Upload Steps:")
                    print("   1. Build package in M365 Agent tab")
                    print("   2. Download the appPackage.zip")
                    print("   3. Go to https://admin.teams.microsoft.com")
                    print("   4. Teams apps → Manage apps → Upload")
                    print("   5. Upload appPackage.zip")
                    print("   6. Set Publishing State = 'Published'")
                    print()
                    print("🔧 Alternative Options:")
                    print("   - Downgrade to Teams module 6.x:")
                    print("     Uninstall-Module MicrosoftTeams -Force")
                    print("     Install-Module MicrosoftTeams -RequiredVersion 6.6.0 -Force")
                    print("   - Try PowerShell automation anyway (may work with interactive auth)")
                    
                else:
                    print("✅ TEAMS MODULE < 7.0 DETECTED")
                    print("=" * 35)
                    print("✅ Compatible with PowerShell automation")
                    print("✅ Client secret authentication supported")
                    print()
                    print("📋 RECOMMENDED DEPLOYMENT METHODS:")
                    print("   1. HTTP deployment (fastest)")
                    print("   2. PowerShell automation")
                    print("   3. Manual upload (always works)")
                
            elif "TEAMS_MODULE_NOT_FOUND" in output:
                print("❌ Microsoft Teams PowerShell Module NOT FOUND")
                print()
                print("📦 Installation Required:")
                print("   Install-Module -Name MicrosoftTeams -Force -Scope CurrentUser")
                print()
                print("💡 After installation:")
                print("   - Teams module 6.x: PowerShell automation will work")
                print("   - Teams module 7.x+: Manual upload recommended")
                
            else:
                print("⚠️  Could not determine Teams module status")
                print(f"Output: {output}")
                
        else:
            print("❌ Failed to check Teams module")
            print(f"Error: {result.stderr}")
            
    except FileNotFoundError:
        print("❌ PowerShell not found")
        if platform.system().lower() == "windows":
            print("   Please ensure PowerShell is installed")
        else:
            print("   Please install PowerShell Core: https://github.com/PowerShell/PowerShell")
    except subprocess.TimeoutExpired:
        print("❌ PowerShell command timed out")
    except Exception as e:
        print(f"❌ Error checking Teams module: {e}")
    
    print()
    print("🎯 SUMMARY:")
    print("   - Teams 7.x+: Use manual upload")
    print("   - Teams 6.x: Automation works")
    print("   - Not installed: Install first, then check version")
    print()
    print("📚 Resources:")
    print("   - Teams Admin Center: https://admin.teams.microsoft.com")
    print("   - PowerShell Gallery: https://www.powershellgallery.com/packages/MicrosoftTeams")

if __name__ == "__main__":
    check_teams_module_version()
