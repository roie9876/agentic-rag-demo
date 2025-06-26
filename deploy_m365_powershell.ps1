# M365 Agent PowerShell Deployment Script
# ======================================
# This script uses the Microsoft Teams PowerShell module to deploy M365 agents
# since AppCatalog.Submit is not available as an Application permission.

param(
    [Parameter(Mandatory=$false)]
    [string]$PackagePath = "appPackage.zip",
    
    [Parameter(Mandatory=$false)]
    [string]$TenantId = $env:M365_TENANT_ID,
    
    [Parameter(Mandatory=$false)]
    [string]$ClientId = $env:M365_CLIENT_ID,
    
    [Parameter(Mandatory=$false)]
    [string]$ClientSecret = $env:M365_CLIENT_SECRET
)

Write-Host "🚀 M365 Agent PowerShell Deployment" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

# Check if Teams module is installed
Write-Host "🔍 Checking Microsoft Teams PowerShell module..." -ForegroundColor Yellow

if (-not (Get-Module -ListAvailable -Name MicrosoftTeams)) {
    Write-Host "❌ Microsoft Teams PowerShell module not found" -ForegroundColor Red
    Write-Host "Installing Microsoft Teams module..." -ForegroundColor Yellow
    
    try {
        Install-Module -Name MicrosoftTeams -Force -AllowClobber -Scope CurrentUser
        Write-Host "✅ Microsoft Teams module installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to install Microsoft Teams module: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "✅ Microsoft Teams module found" -ForegroundColor Green
}

# Import the module
Import-Module MicrosoftTeams

# Check if package exists
if (-not (Test-Path $PackagePath)) {
    Write-Host "❌ Package not found: $PackagePath" -ForegroundColor Red
    Write-Host "💡 Please run the M365 Agent tab to create the package first" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Package found: $PackagePath" -ForegroundColor Green

# Connect to Microsoft Teams
Write-Host "🔐 Connecting to Microsoft Teams..." -ForegroundColor Yellow

try {
    # For M365 app deployment, we need to use interactive login
    # because AppCatalog.Submit requires delegated permissions
    Write-Host "⚠️  Interactive login required - a browser window will open" -ForegroundColor Yellow
    Write-Host "   This is required because app catalog operations need delegated permissions" -ForegroundColor Cyan
    
    if ($TenantId) {
        Connect-MicrosoftTeams -TenantId $TenantId
    }
    else {
        Connect-MicrosoftTeams
    }
    
    Write-Host "✅ Connected to Microsoft Teams successfully" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to connect to Microsoft Teams: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Interactive login is required for app deployment operations" -ForegroundColor Yellow
    Write-Host "   Please make sure you have Teams admin permissions" -ForegroundColor Yellow
    exit 1
}

# Upload the app package
Write-Host "📦 Uploading M365 Agent package..." -ForegroundColor Yellow

try {
    # Upload the app with DistributionMethod specified
    $AppUploadResult = New-TeamsApp -Path $PackagePath -DistributionMethod "organization"
    
    if ($AppUploadResult) {
        Write-Host "✅ M365 Agent uploaded successfully!" -ForegroundColor Green
        Write-Host "App ID: $($AppUploadResult.Id)" -ForegroundColor Cyan
        Write-Host "App Name: $($AppUploadResult.DisplayName)" -ForegroundColor Cyan
        
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
    
    # Provide troubleshooting tips
    Write-Host ""
    Write-Host "🔧 Troubleshooting Tips:" -ForegroundColor Yellow
    Write-Host "1. Ensure you have Teams admin permissions" -ForegroundColor White
    Write-Host "2. Check that the package is valid (manifest.json, icons, etc.)" -ForegroundColor White
    Write-Host "3. Try uploading manually via Teams Admin Center first" -ForegroundColor White
    Write-Host "4. Check if your account has the necessary permissions" -ForegroundColor White
    
    exit 1
}
finally {
    # Disconnect from Teams
    try {
        Disconnect-MicrosoftTeams
        Write-Host "🔓 Disconnected from Microsoft Teams" -ForegroundColor Gray
    }
    catch {
        # Ignore disconnect errors
    }
}
