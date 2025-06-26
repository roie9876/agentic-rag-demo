# Manual Upload Guide for M365 Agent - Teams 7.x+ Compatible

## 🚨 For Teams PowerShell Module 7.x+ Users

If you have Microsoft Teams PowerShell module version 7.0 or newer, **automated PowerShell deployment will likely fail** due to breaking changes Microsoft introduced. Manual upload is the most reliable method.

## ✅ Step-by-Step Manual Upload Process

### Step 1: Check Your Teams Module Version
```powershell
# Run this command to check your Teams module version
Get-Module -ListAvailable -Name MicrosoftTeams | Select-Object Version
```

If you see version 7.x or newer, use this manual process.

### Step 2: Build and Download the Package
1. In the M365 Agent UI, complete steps 1-4 to build your package
2. Click "📥 Download Package for Manual Upload" 
3. Save the `appPackage.zip` file to your computer

### Step 3: Access Teams Admin Center
1. Open your browser and go to: https://admin.teams.microsoft.com
2. Sign in with your Microsoft 365 admin account
3. Make sure you have Teams Administrator permissions

### Step 4: Upload Your Agent
1. In Teams Admin Center, navigate to:
   - **Teams apps** → **Manage apps**
2. Click **Upload** (usually in the top-right area)
3. Select "Upload an app to your org's app catalog"
4. Choose the `appPackage.zip` file you downloaded
5. Click **Upload**

### Step 5: Publish Your Agent
1. After upload, find your app in the list (search for "Azure Function Proxy")
2. Click on your app name
3. Change **Publishing State** from "Pending" to **"Published"**
4. Configure any additional settings as needed

### Step 6: Test Your Agent
1. Open Microsoft 365 Copilot
2. Look for your agent in the agent picker
3. Test with: `@AzureFunctionProxy Hello, can you help me?`
4. Verify questions are routed to your Azure Function

## 🔧 Troubleshooting

### Common Issues:
- **"App not found"**: Wait 5-10 minutes for propagation, then check again
- **"Permission denied"**: Ensure you have Teams Administrator role
- **"Package invalid"**: Re-download the package and try again

### Verification:
- Check Azure Function logs to confirm questions are being received
- Use Application Insights if enabled on your Function App
- Test different types of questions to verify routing

## 💡 Why Manual Upload is Better for Teams 7.x+

- ✅ **Always works** regardless of Teams module version
- ✅ **No authentication issues** with PowerShell
- ✅ **Same end result** as automated deployment
- ✅ **More reliable** than PowerShell automation
- ✅ **Better error messages** from Teams Admin Center

## 🔄 Alternative: Downgrade Teams Module

If you prefer PowerShell automation, you can downgrade:

```powershell
# Remove current version
Uninstall-Module MicrosoftTeams -Force

# Install compatible version
Install-Module MicrosoftTeams -RequiredVersion 6.6.0 -Force

# Verify version
Get-Module -ListAvailable -Name MicrosoftTeams | Select-Object Version
```

**Note**: Downgrading may affect other Teams PowerShell scripts you use.

## 📞 Need Help?

1. **Check the UI**: The M365 Agent Builder provides real-time guidance
2. **Verify credentials**: Ensure your .env file has correct M365 credentials  
3. **Test function**: Use the built-in function testing in the UI
4. **Check logs**: Monitor your Azure Function logs for incoming requests

---

**Bottom Line**: Manual upload is the most reliable method for M365 Agent deployment, especially with Teams PowerShell module 7.x+. It takes just a few minutes and always works!
