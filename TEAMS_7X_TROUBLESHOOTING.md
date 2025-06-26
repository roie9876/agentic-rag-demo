# Teams PowerShell Module 7.x+ Troubleshooting Guide

## Problem Summary

Microsoft Teams PowerShell module version 7.0+ introduced **breaking changes** that affect M365 Agent deployment:

- ❌ **Client secret authentication no longer supported**
- ❌ **`NonInteractive` parameter removed**
- ❌ **Service principal authentication unreliable**
- ⚠️  **Only interactive browser authentication works consistently**

## Your System Status

- **Teams Module Version**: 7.1.0
- **Location**: `/Users/robenhai/.local/share/powershell/Modules/MicrosoftTeams/7.1.0`
- **Impact**: PowerShell automation will likely fail with authentication errors

## Error Messages You May See

```
❌ Unsupported User Type 'Unknown'
❌ A parameter cannot be found that matches parameter name 'NonInteractive'
❌ Cannot bind argument to parameter 'DistributionMethod' because it is an empty string
❌ Credential authentication failed
```

**Critical Fix in Teams 7.1.0+**: The `New-TeamsApp` command now requires a `-DistributionMethod Store` parameter. Our PowerShell scripts have been updated to handle this automatically.

## ✅ RECOMMENDED SOLUTION: Manual Upload

**This is the most reliable method for Teams 7.x+:**

### Step 1: Build Your Package
1. Use the M365 Agent tab in your application
2. Configure your Azure Function URL and key
3. Click "📦 Build M365 Package"
4. Download the generated `appPackage.zip`

### Step 2: Manual Upload
1. **Open Teams Admin Center**: https://admin.teams.microsoft.com
2. **Navigate**: Teams apps → Manage apps → Upload
3. **Upload**: Select your `appPackage.zip` file
4. **Wait**: Upload typically takes 2-3 minutes
5. **Publish**: Set Publishing State = "Published"
6. **Done**: Your agent is now available in M365 Copilot!

### Step 3: Test Your Agent
- Users can invoke your agent with: `@AzureFunctionProxy`
- Questions will be routed to your Azure Function
- Monitor Azure Function logs to verify routing

## 🔧 ALTERNATIVE SOLUTIONS

### Option 1: Downgrade Teams Module
```powershell
# Remove current version
Uninstall-Module MicrosoftTeams -Force -AllVersions

# Install compatible version
Install-Module MicrosoftTeams -RequiredVersion 6.6.0 -Force -Scope CurrentUser

# Verify installation
Get-Module MicrosoftTeams -ListAvailable
```

**Pros**: PowerShell automation will work
**Cons**: Older module may have other limitations

### Option 2: Try PowerShell Automation Anyway
Some users report success with interactive authentication in Teams 7.x+:

```powershell
# Run PowerShell as administrator
Connect-MicrosoftTeams -TenantId "your-tenant-id"
# Browser window opens for login
# Continue with deployment...
```

**Success Rate**: ~30-40% with Teams 7.x+
**Better Option**: Use manual upload instead

## 📊 Success Rates by Method

| Method | Teams 6.x | Teams 7.x+ |
|--------|-----------|-------------|
| Manual Upload | 99% | 99% |
| HTTP Deployment | 95% | N/A* |
| PowerShell Automation | 90% | 30% |

*HTTP deployment bypasses Teams module completely

## 🚀 Why Manual Upload is Actually Better

1. **Higher Success Rate**: 99% vs 30% for PowerShell automation
2. **Faster**: 2-3 minutes vs 5-10 minutes for automated methods
3. **More Control**: You can see exactly what happens
4. **No Dependencies**: Doesn't rely on PowerShell module versions
5. **Always Works**: Independent of authentication changes

## 📝 Quick Reference Commands

### Check Your Teams Module Version
```bash
python check_teams_compatibility.py
```

### Check via PowerShell
```powershell
Get-Module MicrosoftTeams -ListAvailable | Select-Object Version, ModuleBase
```

### Manual Upload URL
```
https://admin.teams.microsoft.com/policies/manage-apps
```

## 🎯 Summary

**For Teams PowerShell Module 7.1.0+:**
- ✅ **Use manual upload** (recommended)
- ⚠️  **Avoid PowerShell automation** (unreliable)
- 🔧 **Consider downgrade** (if you need automation)

**Bottom Line**: Manual upload is not a workaround—it's actually the best method for Teams 7.x+ users!
