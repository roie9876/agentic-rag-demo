# CLI Deployment Guide - M365 Agent

## 🚀 Direct PowerShell Deployment

If the UI deployment times out due to interactive authentication, you can deploy directly via CLI.

### ✅ Verified Working (June 26, 2025)

**Latest successful deployment:**
- App ID: `2fd55ca5-95d3-4bc0-bc42-201cf292d5ad`
- App Name: "Azure Function Proxy"
- Status: Successfully uploaded to Teams App Catalog

### 📋 Prerequisites

1. **Package Built**: Use the UI to build your `appPackage.zip` first
2. **M365 Credentials**: Ensure `.env` file has M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET
3. **PowerShell**: Install PowerShell Core (`pwsh`) if on macOS/Linux

### 🔧 CLI Deployment Steps

#### Step 1: Build Package (via UI)
```bash
# Run Streamlit UI
streamlit run ui/main.py

# Go to M365 Agent tab
# Configure Azure Function URL and build package
# This creates appPackage.zip
```

#### Step 2: Deploy via CLI
```bash
# Navigate to your project directory
cd /Users/robenhai/agentic-rag-demo

# Run PowerShell deployment script
pwsh ./deploy_m365_powershell.ps1
```

### 📤 Expected Output

```
🚀 M365 Agent PowerShell Deployment
==================================================
🔍 Checking Microsoft Teams PowerShell module...
✅ Microsoft Teams module found
✅ Package found: appPackage.zip
🔐 Connecting to Microsoft Teams...
⚠️  Interactive login required - a browser window will open
   This is required because app catalog operations need delegated permissions

✅ Connected to Microsoft Teams successfully
📦 Uploading M365 Agent package...
✅ M365 Agent uploaded successfully!
App ID: [your-app-id]
App Name: Azure Function Proxy

📝 Next Steps:
1. Open Teams Admin Center: https://admin.teams.microsoft.com
2. Go to Teams apps → Manage apps  
3. Find your app: Azure Function Proxy
4. Set Publishing State = 'Published'
5. Configure permissions and policies as needed
6. The app will be available in Microsoft 365 Copilot!

🎉 Deployment completed successfully!
```

### ⏱️ Timing Expectations

- **Interactive Auth**: 2-5 minutes (browser login)
- **Package Upload**: 30-60 seconds
- **Total Time**: 3-6 minutes typically

### 🔧 Troubleshooting

#### Authentication Issues
```bash
# If authentication fails, try clearing Teams session
Disconnect-MicrosoftTeams
# Then retry deployment
```

#### Module Issues
```bash
# Update Teams PowerShell module
Update-Module MicrosoftTeams -Force
```

#### Permission Issues
- Ensure your Azure AD app has `AppCatalog.Submit` permission
- Grant admin consent in Azure Portal

### ✅ Success Indicators

1. **App ID Generated**: You'll get a GUID like `2fd55ca5-95d3-4bc0-bc42-201cf292d5ad`
2. **App Name Confirmed**: Should show "Azure Function Proxy" (or your custom name)
3. **Upload Success**: Message "M365 Agent uploaded successfully!"
4. **Admin Center**: App appears in Teams Admin Center → Manage apps

### 📝 Post-Deployment

1. **Publish App**: Set Publishing State to "Published" in Teams Admin Center
2. **Configure Policies**: Set up user access policies if needed
3. **Test Access**: Verify app appears for authorized users
4. **Monitor Usage**: Check Azure Function logs for routing verification

### 🎯 Why CLI Works Better

- **No UI Timeout**: Interactive auth can take longer than UI timeout
- **Better Error Messages**: Full PowerShell output available
- **Direct Control**: Can troubleshoot authentication issues immediately
- **Reliable**: No intermediate layers that might cause issues

---

**💡 Pro Tip**: Build the package in the UI for convenience, then deploy via CLI for reliability! This gives you the best of both worlds. 🚀
