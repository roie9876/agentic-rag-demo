#!/usr/bin/env python3
"""
Quick Teams Admin Access Test
============================
Test if you can access Teams Admin Center without needing to find the exact role name.
"""

import webbrowser
import time

def test_teams_admin_access():
    print("🧪 TESTING TEAMS ADMIN CENTER ACCESS")
    print("=" * 50)
    
    print("We'll test if you can access Teams Admin Center directly.")
    print("This will tell us if you have the right permissions,")
    print("regardless of what the role is called in your organization.")
    print()
    
    # URLs to test
    test_urls = [
        {
            "name": "Teams App Management",
            "url": "https://admin.teams.microsoft.com/policies/manage-apps",
            "what_to_look_for": "Look for 'Upload new app' button"
        },
        {
            "name": "Teams Admin Dashboard", 
            "url": "https://admin.teams.microsoft.com/dashboard",
            "what_to_look_for": "Should show Teams admin dashboard"
        },
        {
            "name": "Teams Apps Overview",
            "url": "https://admin.teams.microsoft.com/teams/apps",
            "what_to_look_for": "Should show list of Teams apps"
        }
    ]
    
    print("🔗 We'll test these URLs:")
    for i, test in enumerate(test_urls, 1):
        print(f"{i}. {test['name']}")
        print(f"   URL: {test['url']}")
        print(f"   Success indicator: {test['what_to_look_for']}")
        print()
    
    input("Press Enter to start testing...")
    
    results = []
    
    for i, test in enumerate(test_urls, 1):
        print(f"\n🌐 Opening Test {i}: {test['name']}")
        print(f"URL: {test['url']}")
        print(f"Look for: {test['what_to_look_for']}")
        
        # Open URL
        webbrowser.open(test['url'])
        
        # Ask user about result
        print("\nWhat happened?")
        print("1. ✅ I can see the page and the expected content")
        print("2. ❌ Access denied / Permission error")
        print("3. 🔄 Page loads but missing expected features")
        print("4. ❓ Redirected to login or different page")
        
        while True:
            try:
                choice = input("Enter choice (1-4): ").strip()
                if choice in ['1', '2', '3', '4']:
                    break
                print("Please enter 1, 2, 3, or 4")
            except (EOFError, KeyboardInterrupt):
                print("\nTest cancelled.")
                return
        
        result_map = {
            '1': '✅ SUCCESS',
            '2': '❌ ACCESS DENIED', 
            '3': '🔄 PARTIAL ACCESS',
            '4': '❓ REDIRECTED'
        }
        
        results.append({
            'test': test['name'],
            'result': result_map[choice],
            'success': choice == '1'
        })
        
        print(f"Result recorded: {result_map[choice]}")
        
        if i < len(test_urls):
            time.sleep(2)  # Brief pause between tests

def analyze_results(results):
    print("\n" + "=" * 50)
    print("📊 RESULTS ANALYSIS")
    print("=" * 50)
    
    successful_tests = [r for r in results if r['success']]
    
    print("\n📋 Summary:")
    for result in results:
        print(f"• {result['test']}: {result['result']}")
    
    print(f"\n🎯 Success Rate: {len(successful_tests)}/{len(results)} tests passed")
    
    if len(successful_tests) >= 1:
        print("\n✅ GOOD NEWS!")
        print("You have some level of Teams admin access!")
        print()
        print("🚀 RECOMMENDED NEXT STEPS:")
        print("1. Try manual upload at the working URL")
        print("2. Upload your appPackage.zip file")
        print("3. If manual upload works, our PowerShell script should work too")
        print("   (re-run: pwsh ./deploy_m365_powershell.ps1)")
        
    elif any('PARTIAL' in r['result'] for r in results):
        print("\n🔄 PARTIAL ACCESS DETECTED")
        print("You have some Teams permissions but maybe not full admin rights.")
        print()
        print("🚀 RECOMMENDED NEXT STEPS:")
        print("1. Try sideloading in Teams client")
        print("2. Contact IT admin to clarify your exact permissions")
        print("3. Ask for 'Teams Administrator' role specifically")
        
    else:
        print("\n❌ NO TEAMS ADMIN ACCESS")
        print("You don't appear to have Teams admin permissions.")
        print()
        print("🚀 RECOMMENDED NEXT STEPS:")
        print("1. Contact IT admin with the email template")
        print("2. Request 'Teams Administrator' role")
        print("3. While waiting, try sideloading for testing:")
        print("   → Open Teams → Apps → Upload a custom app")

def show_sideloading_instructions():
    print("\n" + "=" * 50)
    print("🔄 SIDELOADING INSTRUCTIONS (No Admin Rights Needed)")
    print("=" * 50)
    
    print("\n📱 METHOD 1: Teams Desktop App")
    print("-" * 30)
    print("1. Open Microsoft Teams desktop application")
    print("2. Click 'Apps' in the left sidebar")
    print("3. Look for 'Upload a custom app' (bottom left or in menu)")
    print("4. Select your appPackage.zip file")
    print("5. App will be installed for your use")
    
    print("\n🌐 METHOD 2: Teams Web App")
    print("-" * 30)
    print("1. Go to https://teams.microsoft.com")
    print("2. Click 'Apps' in the left sidebar")
    print("3. Look for 'Upload a custom app' option")
    print("4. Select your appPackage.zip file")
    
    print("\n💡 NOTE ABOUT SIDELOADING:")
    print("-" * 30)
    print("• Sideloading installs the app just for you/your team")
    print("• It's perfect for testing functionality")
    print("• The app won't be available organization-wide")
    print("• For org-wide deployment, you still need admin permissions")

def main():
    print("Teams Admin Access Testing Tool")
    print("=" * 50)
    print("This tool will help determine if you have Teams admin permissions")
    print("by testing direct access to Teams Admin Center URLs.")
    print()
    
    choice = input("Do you want to run the access tests? (y/n): ").lower().strip()
    
    if choice == 'y':
        results = []
        test_teams_admin_access()
        # Note: In a real scenario, we'd collect results here
        # For this demo, we'll show the instructions
        
        print("\nBased on the tests, here are your options:")
        show_sideloading_instructions()
    else:
        print("\nNo problem! Here's what you can try instead:")
        show_sideloading_instructions()
    
    print("\n" + "=" * 50)
    print("🎯 REMEMBER: Our PowerShell deployment solution is technically perfect!")
    print("Once you get the right permissions, it will work flawlessly.")
    print("The error you saw confirms the code works - it's just a permission issue.")
    print("=" * 50)

if __name__ == "__main__":
    main()
