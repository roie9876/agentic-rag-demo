#!/usr/bin/env python3
"""
M365 Package Validator and Deployment Diagnostics
=================================================
This script validates the M365 app package and provides deployment diagnostics.
"""

import os
import zipfile
import json
from dotenv import load_dotenv

load_dotenv()

def validate_app_package(package_path="appPackage.zip"):
    """Validate the M365 app package structure and content"""
    print("🔍 Validating M365 App Package")
    print("=" * 50)
    
    if not os.path.exists(package_path):
        print(f"❌ Package not found: {package_path}")
        return False
    
    print(f"✅ Package found: {package_path}")
    print(f"📦 Package size: {os.path.getsize(package_path)} bytes")
    
    try:
        with zipfile.ZipFile(package_path, 'r') as zip_file:
            files = zip_file.namelist()
            print(f"📁 Files in package: {len(files)}")
            
            # Check required files
            required_files = ['manifest.json']
            optional_files = ['color.png', 'outline.png']
            
            print("\n📋 File Check:")
            for file in required_files:
                if file in files:
                    print(f"✅ {file}")
                else:
                    print(f"❌ {file} (REQUIRED)")
                    return False
            
            for file in optional_files:
                if file in files:
                    print(f"✅ {file}")
                else:
                    print(f"⚠️  {file} (optional but recommended)")
            
            # Validate manifest.json
            if 'manifest.json' in files:
                print("\n📄 Validating manifest.json:")
                try:
                    manifest_data = zip_file.read('manifest.json')
                    manifest = json.loads(manifest_data)
                    
                    # Check required fields
                    required_fields = [
                        'id', 'version', 'developer', 'name', 
                        'description', 'icons', 'accentColor'
                    ]
                    
                    for field in required_fields:
                        if field in manifest:
                            print(f"  ✅ {field}: {str(manifest[field])[:50]}...")
                        else:
                            print(f"  ❌ Missing field: {field}")
                    
                    # Check M365 specific fields
                    if 'copilotExtensions' in manifest:
                        print(f"  ✅ copilotExtensions: Found")
                        copilot = manifest['copilotExtensions']
                        if 'plugins' in copilot:
                            plugins = copilot['plugins']
                            print(f"    ✅ plugins: {len(plugins)} plugin(s)")
                            for i, plugin in enumerate(plugins):
                                if 'file' in plugin:
                                    print(f"      ✅ Plugin {i+1} file: {plugin['file']}")
                                if 'id' in plugin:
                                    print(f"      ✅ Plugin {i+1} id: {plugin['id']}")
                        else:
                            print(f"    ❌ No plugins found in copilotExtensions")
                    else:
                        print(f"  ❌ Missing copilotExtensions (required for M365 Copilot)")
                    
                    return True
                    
                except json.JSONDecodeError as e:
                    print(f"  ❌ Invalid JSON in manifest.json: {e}")
                    return False
            
    except zipfile.BadZipFile:
        print(f"❌ Invalid ZIP file: {package_path}")
        return False
    except Exception as e:
        print(f"❌ Error validating package: {e}")
        return False

def check_powershell_requirements():
    """Check PowerShell and Teams module requirements"""
    print("\n🔧 PowerShell Requirements Check")
    print("=" * 50)
    
    # These checks would need to be run in PowerShell
    print("📝 To check PowerShell requirements, run these commands:")
    print()
    print("pwsh -Command \"$PSVersionTable.PSVersion\"")
    print("pwsh -Command \"Get-Module -ListAvailable -Name MicrosoftTeams\"")
    print("pwsh -Command \"Get-Module -ListAvailable -Name Microsoft.Graph\"")
    print()

def check_teams_admin_permissions():
    """Provide guidance on checking Teams admin permissions"""
    print("\n🔐 Teams Admin Permissions Check")
    print("=" * 50)
    
    print("To verify you have the correct permissions:")
    print()
    print("1. 🌐 Open Teams Admin Center:")
    print("   https://admin.teams.microsoft.com")
    print()
    print("2. 📱 Navigate to: Teams apps → Manage apps")
    print()
    print("3. 🔍 Check if you can see the 'Upload' button")
    print("   - If YES: You have the right permissions")
    print("   - If NO: Contact your Teams admin")
    print()
    print("4. 👤 Required roles (one of these):")
    print("   - Global Administrator")
    print("   - Teams Administrator") 
    print("   - Teams App Administrator")
    print()

def suggest_deployment_alternatives():
    """Suggest alternative deployment methods"""
    print("\n🚀 Alternative Deployment Methods")
    print("=" * 50)
    
    print("If PowerShell deployment fails, try these alternatives:")
    print()
    print("1. 🖱️ Manual Upload (Most Reliable):")
    print("   - Open: https://admin.teams.microsoft.com/policies/manage-apps")
    print("   - Click 'Upload new app'")
    print("   - Select appPackage.zip")
    print("   - Follow the wizard")
    print()
    print("2. 🤖 Browser Automation:")
    print("   - Use Selenium/Playwright")
    print("   - Automate the manual upload process")
    print()
    print("3. 📞 Contact Teams Admin:")
    print("   - Send them the appPackage.zip")
    print("   - Ask them to upload it manually")
    print()

def main():
    print("🔍 M365 Package Validation & Deployment Diagnostics")
    print("=" * 60)
    
    # Validate the package
    package_valid = validate_app_package()
    
    # Check requirements
    check_powershell_requirements()
    check_teams_admin_permissions()
    
    # Suggest alternatives
    suggest_deployment_alternatives()
    
    print("\n" + "=" * 60)
    print("📝 SUMMARY:")
    print("=" * 60)
    
    if package_valid:
        print("✅ App package is valid")
        print("🎯 Try the PowerShell deployment again")
        print("💡 If it fails, use manual upload as fallback")
    else:
        print("❌ App package has issues")
        print("🔧 Fix the package first, then try deployment")
    
    print()
    print("🔗 Useful Links:")
    print(f"- Teams Admin Center: https://admin.teams.microsoft.com")
    print(f"- App Upload Page: https://admin.teams.microsoft.com/policies/manage-apps")
    print(f"- M365 Developer Docs: https://docs.microsoft.com/en-us/microsoftteams/platform/")

if __name__ == "__main__":
    main()
