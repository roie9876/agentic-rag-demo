#!/usr/bin/env python3
"""
Teams Administrator Permission Finder
=====================================
Help locate the exact Teams Administrator permission in Azure Portal
"""

def find_teams_admin_permission():
    print("=" * 70)
    print("🔍 FINDING TEAMS ADMINISTRATOR PERMISSION")
    print("=" * 70)
    
    print("\n📍 POSSIBLE LOCATIONS & NAMES:")
    print("-" * 40)
    
    print("1. 🎯 Azure Portal - User Roles")
    print("   URL: https://portal.azure.com")
    print("   Path: Azure Active Directory → Users → [Your User] → Assigned roles")
    print("   Look for these EXACT names:")
    print("   • Teams Administrator")
    print("   • Microsoft Teams Administrator")
    print("   • Teams Service Administrator")
    print("   • Global Administrator (also works)")
    print()
    
    print("2. 🎯 Microsoft 365 Admin Center")
    print("   URL: https://admin.microsoft.com")
    print("   Path: Users → Active users → [Your User] → Manage roles")
    print("   Look for:")
    print("   • Teams Administrator")
    print("   • Teams service administrator")
    print("   • Global Administrator")
    print()
    
    print("3. 🎯 Azure AD Roles and Administrators")
    print("   URL: https://portal.azure.com")
    print("   Path: Azure Active Directory → Roles and administrators")
    print("   Search for: 'Teams'")
    print("   Should show:")
    print("   • Teams Administrator")
    print("   • Teams Communications Administrator")
    print("   • Teams Communications Support Engineer")

def troubleshoot_missing_permission():
    print("\n" + "=" * 70)
    print("🔧 TROUBLESHOOTING: CAN'T FIND TEAMS ADMINISTRATOR")
    print("=" * 70)
    
    print("\n❓ POSSIBLE REASONS:")
    print("-" * 30)
    print("1. 🔍 Different Name/Display")
    print("   • Might be called 'Microsoft Teams Administrator'")
    print("   • Could be abbreviated as 'Teams Admin'")
    print("   • Check for ANY role with 'Teams' in the name")
    print()
    
    print("2. 🏢 Organization Restrictions")
    print("   • Your organization might use custom role names")
    print("   • Teams admin might be part of a custom role")
    print("   • Check for roles like 'IT Administrator' or similar")
    print()
    
    print("3. 🔐 Insufficient Permissions to View")
    print("   • You might not have permission to see all roles")
    print("   • Contact IT admin to check your roles")
    print()
    
    print("4. 🌐 Different Tenant Type")
    print("   • Some tenant types have different role structures")
    print("   • Education/Government tenants might vary")

def alternative_permission_checks():
    print("\n" + "=" * 70)
    print("🔄 ALTERNATIVE WAYS TO CHECK PERMISSIONS")
    print("=" * 70)
    
    print("\n1. 🧪 TEST ACCESS METHOD:")
    print("-" * 30)
    print("Go to: https://admin.teams.microsoft.com")
    print("Try to access: Teams apps → Manage apps")
    print()
    print("✅ If you can see 'Upload new app' button:")
    print("   → You have Teams admin permissions (regardless of role name)")
    print("   → Try manual upload: Upload your appPackage.zip")
    print()
    print("❌ If you get 'Access denied' or can't see the option:")
    print("   → You don't have Teams admin permissions")
    print("   → Need to request proper role assignment")
    
    print("\n2. 🔍 POWERSHELL CHECK:")
    print("-" * 30)
    print("Run this PowerShell command to check your roles:")
    print()
    print("```powershell")
    print("# Connect to Azure AD PowerShell")
    print("Install-Module AzureAD -Force")
    print("Connect-AzureAD")
    print()
    print("# Get your roles")
    print("$user = Get-AzureADUser -ObjectId 'your-email@domain.com'")
    print("$roles = Get-AzureADUserMembership -ObjectId $user.ObjectId")
    print("$roles | Where-Object {$_.ObjectType -eq 'Role'} | Select DisplayName")
    print("```")
    
    print("\n3. 🌐 TEAMS ADMIN CENTER DIRECT TEST:")
    print("-" * 30)
    print("URLs to test:")
    print("• https://admin.teams.microsoft.com/policies/manage-apps")
    print("• https://admin.teams.microsoft.com/teams/manage")
    print("• https://admin.teams.microsoft.com/dashboard")
    print()
    print("If ANY of these work, you have some level of Teams admin access")

def what_permissions_actually_needed():
    print("\n" + "=" * 70)
    print("💡 WHAT PERMISSIONS DO YOU ACTUALLY NEED?")
    print("=" * 70)
    
    print("\n🎯 FOR POWERSHELL DEPLOYMENT:")
    print("-" * 35)
    print("You need permission to:")
    print("• Upload custom apps to Teams app catalog")
    print("• Use New-TeamsApp PowerShell cmdlet")
    print("• Access Teams Admin Center")
    print()
    print("This typically requires:")
    print("• Teams Administrator role, OR")
    print("• Global Administrator role, OR")
    print("• Custom role with app upload permissions")
    
    print("\n🎯 FOR MANUAL UPLOAD:")
    print("-" * 25)
    print("You need permission to:")
    print("• Access https://admin.teams.microsoft.com")
    print("• Navigate to 'Manage apps' section")
    print("• See 'Upload new app' button")
    print()
    print("This might work with:")
    print("• Teams Communications Administrator")
    print("• Teams Communications Support Engineer")
    print("• Or even basic Teams user permissions (in some orgs)")

def request_help_from_admin():
    print("\n" + "=" * 70)
    print("📧 REQUEST HELP FROM IT ADMIN")
    print("=" * 70)
    
    print("\n📝 EMAIL TEMPLATE (Copy & Send):")
    print("-" * 35)
    print("""
Subject: Help with Teams App Upload Permissions

Hi [IT Admin Name],

I'm trying to deploy a Microsoft 365 Copilot plugin for our organization, 
but I'm having trouble finding the right permissions.

My User ID: 94ba51d0-9bb4-493b-9a64-c45eb1fb7074
Tenant ID: 2ee5505f-a354-47ca-98b8-5581f62b8d62

Could you please:
1. Check what Teams-related roles I currently have
2. Grant me permission to upload custom Teams apps
3. Let me know if our organization has custom role names

I need to be able to:
• Access https://admin.teams.microsoft.com/policies/manage-apps
• Upload custom app packages (.zip files)
• Use PowerShell Teams module for deployment

Standard role needed: "Teams Administrator" or equivalent

Thanks for your help!
""")

def immediate_workarounds():
    print("\n" + "=" * 70)
    print("🚀 IMMEDIATE WORKAROUNDS (While Waiting for Admin)")
    print("=" * 70)
    
    print("\n1. 🔄 TRY SIDELOADING (No admin needed):")
    print("-" * 40)
    print("• Open Microsoft Teams desktop/web app")
    print("• Go to: Apps → Upload a custom app")
    print("• Select your appPackage.zip")
    print("• This installs app just for you/your team")
    print("• Good for testing the app functionality")
    
    print("\n2. 📱 TRY DIFFERENT TEAMS ADMIN URLS:")
    print("-" * 40)
    print("Sometimes different URLs have different permission requirements:")
    print("• https://admin.teams.microsoft.com/policies/manage-apps")
    print("• https://admin.teams.microsoft.com/teams/apps")
    print("• https://admin.teams.microsoft.com/app-policies")
    print()
    print("Try each one - you might have access to one of them")
    
    print("\n3. 🔍 CHECK MICROSOFT 365 APPS ADMIN:")
    print("-" * 40)
    print("• Go to: https://config.office.com")
    print("• Check if you can manage Office apps there")
    print("• Some orgs separate Office and Teams app management")

def main():
    find_teams_admin_permission()
    troubleshoot_missing_permission()
    alternative_permission_checks()
    what_permissions_actually_needed()
    request_help_from_admin()
    immediate_workarounds()
    
    print("\n" + "=" * 70)
    print("🎯 QUICK ACTION PLAN")
    print("=" * 70)
    print("1. Test access: https://admin.teams.microsoft.com/policies/manage-apps")
    print("2. If it works: Try manual upload of appPackage.zip")
    print("3. If it doesn't: Email IT admin with template above")
    print("4. While waiting: Try sideloading in Teams client")
    print("5. Remember: Our PowerShell solution works once you have permissions!")
    print("=" * 70)

if __name__ == "__main__":
    main()
