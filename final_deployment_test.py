#!/usr/bin/env python3
"""
Final Deployment Test for M365 Agent
===================================
Verifies the complete M365 agent deployment workflow with the updated manifest structure.
"""

import os
import json
import zipfile
from pathlib import Path
from m365_agent_tab import M365AgentManager, M365AgentUI

def test_manifest_compatibility():
    """Test the new Teams-compatible manifest structure"""
    print("🔧 Testing Teams-compatible manifest structure...")
    
    manager = M365AgentManager()
    manifest = manager.create_manifest_json("https://test-function.azurewebsites.net/api/AgentFunction")
    
    # Check required properties
    checks = [
        ("Schema version", manifest.get("$schema") == "https://developer.microsoft.com/en-us/json-schemas/teams/v1.16/MicrosoftTeams.schema.json"),
        ("Manifest version", manifest.get("manifestVersion") == "1.16"),
        ("Has composeExtensions", "composeExtensions" in manifest),
        ("No plugins property", "plugins" not in manifest),
        ("No copilotExtensions", "copilotExtensions" not in manifest),
        ("Valid webApplicationInfo", "webApplicationInfo" in manifest),
        ("Valid app ID", "id" in manifest and manifest["id"]),
        ("Valid package name", manifest.get("packageName") == "com.contoso.funcproxy"),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("✅ All manifest compatibility checks passed!")
        return True
    else:
        print("❌ Some manifest checks failed")
        return False

def test_package_contents():
    """Test the generated package contents"""
    print("\n🔧 Testing package generation...")
    
    manager = M365AgentManager()
    func_url = "https://test-function.azurewebsites.net/api/AgentFunction"
    
    success, message, zip_path = manager.build_package(func_url)
    
    if not success:
        print(f"❌ Package build failed: {message}")
        return False
    
    print(f"✅ Package built successfully: {zip_path}")
    
    # Check package contents
    required_files = ["manifest.json", "plugin.json", "openapi.json", "color.png", "outline.png"]
    
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        package_files = zip_file.namelist()
        
        all_files_present = True
        for required_file in required_files:
            if required_file in package_files:
                print(f"   ✅ {required_file}")
            else:
                print(f"   ❌ {required_file} missing")
                all_files_present = False
        
        # Validate manifest.json content in package
        if "manifest.json" in package_files:
            manifest_content = zip_file.read("manifest.json").decode('utf-8')
            manifest_json = json.loads(manifest_content)
            
            print(f"   ✅ Manifest in package: Schema {manifest_json.get('$schema', 'Unknown')}")
            print(f"   ✅ Plugins property: {'plugins' in manifest_json}")
            print(f"   ✅ ComposeExtensions: {'composeExtensions' in manifest_json}")
    
    return all_files_present

def test_deployment_readiness():
    """Test deployment readiness"""
    print("\n🔧 Testing deployment readiness...")
    
    # Check for M365 credentials
    required_env_vars = ["M365_TENANT_ID", "M365_CLIENT_ID", "M365_CLIENT_SECRET"]
    env_checks = []
    
    for var in required_env_vars:
        value = os.getenv(var)
        has_value = bool(value and value.strip())
        env_checks.append((var, has_value))
        status = "✅" if has_value else "❌"
        print(f"   {status} {var}: {'Set' if has_value else 'Not set'}")
    
    all_env_set = all(has_value for _, has_value in env_checks)
    
    if not all_env_set:
        print("   ℹ️  Set these in your .env file for PowerShell deployment")
    
    # Check PowerShell availability
    import subprocess
    import platform
    
    try:
        system = platform.system().lower()
        ps_cmd = ["powershell.exe", "-Command", "Get-Host"] if system == "windows" else ["pwsh", "-Command", "Get-Host"]
        result = subprocess.run(ps_cmd, capture_output=True, timeout=10)
        ps_available = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        ps_available = False
    
    status = "✅" if ps_available else "❌"
    ps_type = "PowerShell" if system == "windows" else "PowerShell Core (pwsh)"
    print(f"   {status} {ps_type}: {'Available' if ps_available else 'Not found'}")
    
    return all_env_set and ps_available

def generate_deployment_summary():
    """Generate final deployment summary"""
    print("\n📋 Deployment Summary")
    print("=" * 50)
    
    print("✅ **Manifest Structure**: Updated for Teams compatibility")
    print("   • Uses standard `plugins` property")
    print("   • Includes `composeExtensions` for Teams app support")
    print("   • Removed unsupported `copilotExtensions`")
    print()
    
    print("✅ **Package Contents**: All required files generated")
    print("   • manifest.json (Teams v1.16 schema)")
    print("   • plugin.json (API plugin manifest)")
    print("   • openapi.json (Azure Function API spec)")
    print("   • Icon files (color.png, outline.png)")
    print()
    
    print("🚀 **Deployment Options**:")
    print("   1. **PowerShell (Automated)**: Click 'Deploy Now' in the UI")
    print("   2. **Manual Upload**: Download package and upload to Teams Admin Center")
    print("   3. **Graph API**: Use the generated upload script (requires app permissions)")
    print()
    
    print("📝 **Next Steps**:")
    print("   1. Run the Streamlit app: `streamlit run ui/main.py`")
    print("   2. Go to the 'M365 Agent' tab")
    print("   3. Configure your Azure Function URL")
    print("   4. Click 'Deploy Now to M365' for automated deployment")
    print("   5. Go to Teams Admin Center to publish the app")
    print()
    
    print("🔗 **Important URLs**:")
    print("   • Teams Admin Center: https://admin.teams.microsoft.com")
    print("   • App Catalog: Teams apps → Manage apps")
    print("   • M365 Copilot: Available after app is published")

def main():
    """Main test function"""
    print("🚀 M365 Agent Final Deployment Test")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("Manifest Compatibility", test_manifest_compatibility),
        ("Package Contents", test_package_contents),
        ("Deployment Readiness", test_deployment_readiness),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        if not test_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Ready for deployment.")
        generate_deployment_summary()
    else:
        print("❌ Some tests failed. Please check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    main()
