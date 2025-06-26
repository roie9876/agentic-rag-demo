"""
M365 Agent Deployment Guide
==========================
Complete guide for deploying M365 agents after discovering permission limitations.
"""

def print_deployment_guide():
    """Print comprehensive deployment guide"""
    print("🔍 M365 Agent Deployment - Complete Guide")
    print("=" * 60)
    
    print("\n🚨 IMPORTANT DISCOVERY:")
    print("-" * 30)
    print("❌ AppCatalog.Submit is NOT available as Application permission")
    print("✅ AppCatalog.Submit is ONLY available as Delegated permission")
    print("⚠️  This means automated upload requires user interaction")
    
    print("\n🛠️ DEPLOYMENT OPTIONS:")
    print("-" * 30)
    
    print("\n🥇 OPTION 1: PowerShell Deployment (Recommended)")
    print("   1. Install Microsoft Teams PowerShell module:")
    print("      Install-Module -Name MicrosoftTeams -Force -AllowClobber")
    print("   2. Run the PowerShell script (deploy_m365_powershell.ps1)")
    print("   3. Login interactively when prompted")
    print("   4. Script will upload the app package automatically")
    
    print("\n🥈 OPTION 2: Manual Upload via Teams Admin Center")
    print("   1. Download the appPackage.zip from the M365 Agent tab")
    print("   2. Go to: https://admin.teams.microsoft.com")
    print("   3. Navigate to: Teams apps → Manage apps")
    print("   4. Click: Upload new app → Upload")
    print("   5. Select the appPackage.zip file")
    print("   6. Set Publishing State to 'Published'")
    
    print("\n🥉 OPTION 3: Teams Developer Portal")
    print("   1. Go to: https://dev.teams.microsoft.com")
    print("   2. Sign in with your M365 account")
    print("   3. Click: Apps → Import app")
    print("   4. Upload the appPackage.zip")
    print("   5. Publish to your organization")
    
    print("\n📋 PREREQUISITES:")
    print("-" * 30)
    print("✅ You need Teams Admin permissions")
    print("✅ Package must be built first (use M365 Agent tab)")
    print("✅ Function key must be configured in .env")
    print("✅ Azure Function must be accessible")
    
    print("\n🎯 AFTER DEPLOYMENT:")
    print("-" * 30)
    print("1. App will appear in Teams Admin Center")
    print("2. Set Publishing State to 'Published'")
    print("3. Configure any additional policies")
    print("4. App will be available in Microsoft 365 Copilot")
    print("5. Users can ask questions and get responses from your Azure Function")
    
    print("\n💡 WHY AUTOMATED UPLOAD DOESN'T WORK:")
    print("-" * 30)
    print("• Microsoft requires user consent for app catalog operations")
    print("• AppCatalog.Submit permission is delegated-only (not application)")
    print("• This is a security measure to prevent unauthorized app uploads")
    print("• Client credentials flow cannot be used for this operation")
    
    print("\n🔧 TROUBLESHOOTING:")
    print("-" * 30)
    print("• If PowerShell fails: Check Teams admin permissions")
    print("• If manual upload fails: Verify package structure")
    print("• If app doesn't work: Check function key and URL")
    print("• If permissions error: Ensure you're a Teams admin")

if __name__ == "__main__":
    print_deployment_guide()
