# M365 Agent Test Deployment Script
# ===================================
# Quick test to upload the M365 agent package

param(
    [Parameter(Mandatory=$false)]
    [string]$PackagePath = "appPackage.zip"
)

Write-Host "🚀 M365 Agent Test Deployment" -ForegroundColor Cyan
Write-Host "=" * 40 -ForegroundColor Cyan

# Check if package exists
if (-not (Test-Path $PackagePath)) {
    Write-Host "❌ Package not found: $PackagePath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Package found: $PackagePath" -ForegroundColor Green

# Check if already connected to Teams
try {
    $Context = Get-CsOnlineSession
    if ($Context) {
        Write-Host "✅ Already connected to Microsoft Teams" -ForegroundColor Green
    }
    else {
        Write-Host "🔐 Not connected - attempting connection..." -ForegroundColor Yellow
        Connect-MicrosoftTeams
        Write-Host "✅ Connected to Microsoft Teams successfully" -ForegroundColor Green
    }
}
catch {
    Write-Host "🔐 Connecting to Microsoft Teams..." -ForegroundColor Yellow
    try {
        Connect-MicrosoftTeams
        Write-Host "✅ Connected to Microsoft Teams successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to connect: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# Upload the app package with explicit parameters
Write-Host "📦 Uploading M365 Agent package..." -ForegroundColor Yellow

try {
    # Try with organization distribution method
    Write-Host "📋 Using distribution method: organization" -ForegroundColor White
    $AppUploadResult = New-TeamsApp -Path $PackagePath -DistributionMethod "organization"
    
    if ($AppUploadResult) {
        Write-Host "✅ M365 Agent uploaded successfully!" -ForegroundColor Green
        Write-Host "App ID: $($AppUploadResult.Id)" -ForegroundColor Cyan
        Write-Host "App Name: $($AppUploadResult.DisplayName)" -ForegroundColor Cyan
        Write-Host "Version: $($AppUploadResult.Version)" -ForegroundColor Cyan
        
        Write-Host ""
        Write-Host "📝 Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Open Teams Admin Center: https://admin.teams.microsoft.com" -ForegroundColor White
        Write-Host "2. Go to Teams apps → Manage apps" -ForegroundColor White
        Write-Host "3. Find your app: $($AppUploadResult.DisplayName)" -ForegroundColor White
        Write-Host "4. Set Publishing State = 'Published'" -ForegroundColor White
        Write-Host "5. Configure permissions and policies as needed" -ForegroundColor White
        Write-Host "6. The app will be available in Microsoft 365 Copilot!" -ForegroundColor White
        
        Write-Host ""
        Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Upload failed - no result returned" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "❌ Failed to upload app: $($_.Exception.Message)" -ForegroundColor Red
    
    # Try to get more details about the error
    if ($_.Exception.InnerException) {
        Write-Host "Inner Exception: $($_.Exception.InnerException.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "🔧 Troubleshooting Tips:" -ForegroundColor Yellow
    Write-Host "1. Ensure you have Teams admin permissions" -ForegroundColor White
    Write-Host "2. Check that the package is valid (manifest.json, icons, etc.)" -ForegroundColor White
    Write-Host "3. Try uploading manually via Teams Admin Center first" -ForegroundColor White
    Write-Host "4. Verify your account has AppCatalog permissions" -ForegroundColor White
    Write-Host "5. Check if the app ID already exists and needs updating" -ForegroundColor White
    
    # Try alternative methods
    Write-Host ""
    Write-Host "💡 Alternative: Try manual upload at:" -ForegroundColor Yellow
    Write-Host "https://admin.teams.microsoft.com/policies/manage-apps" -ForegroundColor Cyan
    
    exit 1
}

Write-Host ""
Write-Host "🔍 Additional Information:" -ForegroundColor Yellow
Write-Host "- Package uploaded to organization app catalog" -ForegroundColor White
Write-Host "- Admin approval may be required before users can access" -ForegroundColor White
Write-Host "- Check Teams Admin Center for app status and settings" -ForegroundColor White
