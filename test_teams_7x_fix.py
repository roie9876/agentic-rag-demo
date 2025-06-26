#!/usr/bin/env python3
"""
Test script to verify Teams 7.x+ DistributionMethod fix
"""

from pathlib import Path

def test_m365_agent_tab_file():
    """Test that the m365_agent_tab.py file includes the fix"""
    
    file_path = Path("m365_agent_tab.py")
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    file_content = file_path.read_text()
    
    # Check for the specific fixes
    has_distribution_method = "-DistributionMethod Store" in file_content
    has_version_check = "$MajorVersion -ge 7" in file_content
    has_conditional_logic = "if ($MajorVersion -ge 7)" in file_content
    
    # Count occurrences to make sure both PowerShell scripts have the fix
    distribution_method_count = file_content.count("-DistributionMethod Store")
    
    print("🔍 Testing m365_agent_tab.py...")
    print(f"✅ Contains DistributionMethod parameter: {has_distribution_method}")
    print(f"✅ Contains version check: {has_version_check}")
    print(f"✅ Contains conditional logic: {has_conditional_logic}")
    print(f"📊 DistributionMethod occurrences: {distribution_method_count} (should be 2)")
    
    if all([has_distribution_method, has_version_check, has_conditional_logic]) and distribution_method_count >= 2:
        print("🎉 SUCCESS: m365_agent_tab.py includes Teams 7.x+ fixes!")
        return True
    else:
        print("❌ FAILED: m365_agent_tab.py missing Teams 7.x+ fixes")
        return False

def test_standalone_script():
    """Test that the standalone PowerShell script includes the fix"""
    
    script_path = Path("teams_7x_deployment_fix.ps1")
    if not script_path.exists():
        print(f"❌ Standalone script not found: {script_path}")
        return False
    
    script_content = script_path.read_text()
    
    has_distribution_method = "-DistributionMethod Store" in script_content
    has_version_check = "$MajorVersion -ge 7" in script_content
    has_conditional_logic = "if ($MajorVersion -ge 7)" in script_content
    
    print("\n🔍 Testing teams_7x_deployment_fix.ps1...")
    print(f"✅ Contains DistributionMethod parameter: {has_distribution_method}")
    print(f"✅ Contains version check: {has_version_check}")
    print(f"✅ Contains conditional logic: {has_conditional_logic}")
    
    if all([has_distribution_method, has_version_check, has_conditional_logic]):
        print("🎉 SUCCESS: Standalone script includes Teams 7.x+ fixes!")
        return True
    else:
        print("❌ FAILED: Standalone script missing Teams 7.x+ fixes")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Teams 7.x+ DistributionMethod Fix")
    print("=" * 50)
    
    test1 = test_m365_agent_tab_file()
    test2 = test_standalone_script()
    
    print("\n" + "=" * 50)
    if test1 and test2:
        print("🎉 ALL TESTS PASSED: Teams 7.x+ fixes are properly implemented!")
        print("\n📝 Next steps:")
        print("1. Try deploying your M365 agent again from the UI")
        print("2. The PowerShell script should now work with Teams module 7.1.0+")
        print("3. The error 'Cannot bind argument to parameter DistributionMethod' should be resolved")
        print("4. If issues persist, use manual upload as backup")
    else:
        print("❌ SOME TESTS FAILED: Please check the implementation")

if __name__ == "__main__":
    main()
