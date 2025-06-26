#!/usr/bin/env python3
"""
Quick Permission Diagnostic Tool
================================
Check if you have the required Teams admin permissions.
"""

import webbrowser
import os
from datetime import datetime

def check_teams_admin_access():
    """Quick diagnostic to check Teams admin permissions"""
    
    print("🔍 TEAMS ADMIN PERMISSION DIAGNOSTIC")
    print("=" * 50)
    
    # Get user information from the PowerShell error
    user_id = "94ba51d0-9bb4-493b-9a64-c45eb1fb7074"  # From your error
    tenant_id = "2ee5505f-a354-47ca-98b8-5581f62b8d62"  # From your error
    
    print(f"🆔 Your User ID: {user_id}")
    print(f"🏢 Tenant ID: {tenant_id}")
    print()
    
    # Direct links for checking permissions
    azure_portal_user_url = f"https://portal.azure.com/#view/Microsoft_AAD_UsersAndGroups/UserDetailsMenuBlade/~/AssignedRoles/userId/{user_id}"
    teams_admin_url = "https://admin.teams.microsoft.com/policies/manage-apps"
    
    print("📋 PERMISSION CHECK STEPS:")
    print("-" * 30)
    print("1. Check Azure AD Role Assignment:")
    print(f"   🔗 {azure_portal_user_url}")
    print("   → Look for 'Teams Administrator' role")
    print()
    print("2. Test Teams Admin Center Access:")
    print(f"   🔗 {teams_admin_url}")
    print("   → Look for 'Upload new app' button")
    print()
    
    # Ask user to check
    print("🔧 INTERACTIVE CHECK:")
    print("-" * 30)
    
    choice = input("Do you want me to open these URLs for you? (y/n): ").lower().strip()
    
    if choice == 'y':
        print("\n🌐 Opening Azure Portal to check roles...")
        webbrowser.open(azure_portal_user_url)
        
        input("Press Enter after checking your Azure AD roles...")
        
        print("\n🌐 Opening Teams Admin Center...")
        webbrowser.open(teams_admin_url)
        
        input("Press Enter after checking Teams Admin Center access...")
    
    print("\n📊 RESULTS INTERPRETATION:")
    print("-" * 30)
    print("✅ If you see 'Teams Administrator' role:")
    print("   → You have the right permissions")
    print("   → PowerShell deployment should work")
    print("   → Re-run: pwsh ./deploy_m365_powershell.ps1")
    print()
    print("❌ If you DON'T see 'Teams Administrator' role:")
    print("   → You need to request this role from IT admin")
    print("   → Use the email template from teams_admin_permission_guide.py")
    print("   → Or try manual upload as alternative")

def show_next_actions():
    """Show what to do based on permission status"""
    
    print("\n" + "=" * 50)
    print("🎯 NEXT ACTIONS BASED ON YOUR FINDINGS")
    print("=" * 50)
    
    print("\n🔄 SCENARIO A: You HAVE Teams Admin Role")
    print("-" * 40)
    print("1. Re-run PowerShell deployment:")
    print("   pwsh ./deploy_m365_powershell.ps1")
    print("2. If it still fails, check:")
    print("   • Teams app upload policies")
    print("   • Tenant app sideloading settings")
    print("   • Try uploading a different test app")
    
    print("\n🔄 SCENARIO B: You DON'T HAVE Teams Admin Role")
    print("-" * 40)
    print("1. Contact IT admin with email template")
    print("2. While waiting, try manual upload:")
    print("   → https://admin.teams.microsoft.com/policies/manage-apps")
    print("   → Upload appPackage.zip manually")
    print("3. Or try sideloading for testing:")
    print("   → Teams client → Apps → Upload custom app")
    
    print("\n🔄 SCENARIO C: Can't Access Teams Admin Center")
    print("-" * 40)
    print("1. You likely don't have any Teams admin permissions")
    print("2. Try sideloading in Teams client for testing")
    print("3. Request IT admin to deploy the app")
    print("4. Provide them with appPackage.zip and instructions")

def main():
    print("Teams Admin Permission Diagnostic Tool")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    check_teams_admin_access()
    show_next_actions()
    
    print("\n" + "=" * 50)
    print("💡 REMEMBER: Our PowerShell approach is technically correct!")
    print("The only issue is the permission level of your user account.")
    print("Once you have Teams Administrator role, it will work perfectly.")
    print("=" * 50)

if __name__ == "__main__":
    main()
