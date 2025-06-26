#!/usr/bin/env python3
"""
Test the new manifest structure for M365 deployment
Rebuilds package with updated Teams-compatible manifest
"""

import os
import sys
import json
import zipfile
from pathlib import Path
from m365_agent_tab import M365AgentManager

def test_manifest_structure():
    """Test the new manifest structure"""
    print("🔧 Testing new manifest structure...")
    
    manager = M365AgentManager()
    
    # Test manifest creation
    manifest = manager.create_manifest_json("https://test-function.azurewebsites.net/api/AgentFunction")
    print(f"✅ Manifest created with schema: {manifest.get('$schema')}")
    print(f"✅ Manifest version: {manifest.get('manifestVersion')}")
    
    # Check for correct structure
    if 'composeExtensions' in manifest:
        print("✅ Using 'composeExtensions' (messaging extensions)")
        commands = manifest['composeExtensions'][0].get('commands', [])
        print(f"   Commands: {len(commands)} defined")
    else:
        print("❌ No 'composeExtensions' property found")
        return False
    
    if 'plugins' in manifest:
        print("⚠️  Still contains 'plugins' - should be removed for compatibility")
        return False
    else:
        print("✅ No 'plugins' property (good for Teams compatibility)")
    
    if 'copilotExtensions' in manifest:
        print("⚠️  Still contains 'copilotExtensions' - should be removed")
        return False
    else:
        print("✅ No 'copilotExtensions' property (good for Teams compatibility)")
    
    # Check webApplicationInfo for bot registration
    if 'webApplicationInfo' in manifest:
        print("✅ Contains 'webApplicationInfo' for app registration")
        app_id = manifest['webApplicationInfo'].get('id')
        resource = manifest['webApplicationInfo'].get('resource')
        print(f"   App ID: {app_id}")
        print(f"   Resource: {resource}")
    
    return True

def rebuild_package_with_new_manifest():
    """Rebuild the M365 package with the new manifest"""
    print("\n🔧 Rebuilding M365 package with new manifest...")
    
    # Example function URL (replace with your actual function URL)
    func_url = "https://your-function-app.azurewebsites.net/api/AgentFunction"
    
    if 'AZURE_FUNCTION_URL' in os.environ:
        func_url = os.environ['AZURE_FUNCTION_URL']
        print(f"Using function URL from environment: {func_url}")
    else:
        print(f"Using default function URL: {func_url}")
        print("Set AZURE_FUNCTION_URL environment variable for your actual function")
    
    manager = M365AgentManager()
    
    # Build package
    success, message, zip_path = manager.build_package(func_url)
    
    if success and zip_path:
        print(f"✅ Package built successfully: {zip_path}")
        
        # Inspect package contents
        print("\n📦 Package contents:")
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            for file_info in zip_file.filelist:
                print(f"   {file_info.filename}")
        
        # Check manifest.json in the package
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            if 'manifest.json' in zip_file.namelist():
                manifest_content = zip_file.read('manifest.json').decode('utf-8')
                manifest_json = json.loads(manifest_content)
                
                print("\n📋 Manifest structure in package:")
                print(f"   Schema: {manifest_json.get('$schema')}")
                print(f"   Version: {manifest_json.get('manifestVersion')}")
                print(f"   Has 'plugins': {'plugins' in manifest_json}")
                print(f"   Has 'copilotExtensions': {'copilotExtensions' in manifest_json}")
                print(f"   Has 'composeExtensions': {'composeExtensions' in manifest_json}")
                
                if 'plugins' in manifest_json:
                    print(f"   Plugin count: {len(manifest_json['plugins'])}")
        
        return zip_path
    else:
        print(f"❌ Package build failed: {message}")
        return None

def main():
    """Main test function"""
    print("🚀 Testing new M365 manifest structure for Teams compatibility")
    print("=" * 60)
    
    # Test 1: Manifest structure
    if not test_manifest_structure():
        print("❌ Manifest structure test failed")
        sys.exit(1)
    
    # Test 2: Package rebuild
    package_path = rebuild_package_with_new_manifest()
    if not package_path:
        print("❌ Package rebuild failed")
        sys.exit(1)
    
    print("\n✅ All tests passed!")
    print(f"📦 New package ready: {package_path}")
    print("\n🎯 Next steps:")
    print("1. Use the PowerShell deployment script from the UI")
    print("2. Or manually upload the package to Teams Admin Center")
    print("3. The new manifest should be accepted by Teams App Catalog")
    
    return True

if __name__ == "__main__":
    main()
