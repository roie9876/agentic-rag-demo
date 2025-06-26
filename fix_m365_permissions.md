📋 Fix M365 App Registration Permissions
==========================================

🚨 ISSUE IDENTIFIED: You have DELEGATED permissions, but need APPLICATION permissions

Current Setup (Incorrect):
- Microsoft Graph → AppCatalog.ReadWrite.All → Delegated ❌
- Microsoft Graph → AppCatalog.Submit → Delegated ❌

Required Setup (Correct):
- Microsoft Graph → AppCatalog.ReadWrite.All → Application ✅
- Microsoft Graph → AppCatalog.Submit → Application ✅

🔧 STEPS TO FIX:

1. In Azure Portal, go to your M365 app registration
2. Navigate to "API permissions"
3. Remove the current delegated permissions:
   - Click the "..." next to each permission
   - Select "Remove permission"
   - Confirm the removal

4. Add Application permissions:
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Select "Application permissions" (NOT Delegated permissions)
   - Search for and select:
     * AppCatalog.Submit
     * AppCatalog.ReadWrite.All (if available)
   - Click "Add permissions"

5. Grant admin consent:
   - Click "Grant admin consent for [Your Organization]"
   - Confirm by clicking "Yes"
   - Ensure both permissions show "Granted for [Your Organization]"

🎯 VERIFICATION:
After making these changes, both permissions should show:
- Type: Application
- Status: Granted for [Your Organization]

Then retry the M365 Agent deployment - it should work! 🚀

💡 WHY THIS MATTERS:
- Delegated permissions require a user to be present
- Application permissions work for automated scenarios (like our deployment script)
- Client credentials flow (what we're using) only works with Application permissions
