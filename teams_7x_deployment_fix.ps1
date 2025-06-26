# M365 Agent PowerShell Deployment - Teams 7.x+ Compatible
param(
    [Parameter(Mandatory=$true)]
       # Teams 7.x+ requires DistributionMethod parameter
    if ($MajorVersion -ge 7) {
        Write-Host "🔧 Using Teams 7.x+ compatible upload with DistributionMethod..."
        # Try Organization first (most common for enterprise tenants), then Store as fallback
        try {
            Write-Host "🏢 Attempting upload with DistributionMethod: Organization"
            $AppResult = New-TeamsApp -Path $PackagePath -DistributionMethod Organization
        } catch {
            Write-Host "⚠️ Organization method failed, trying Store method..."
            $AppResult = New-TeamsApp -Path $PackagePath -DistributionMethod Store
        }
    } else {
        Write-Host "🔧 Using legacy upload method..."
        $AppResult = New-TeamsApp -Path $PackagePath
    }]$TenantId,
    
    [Parameter(Mandatory=$false)]
    [string]$ClientId,
    
    [Parameter(Mandatory=$false)]
    [string]$ClientSecret,
    
    [Parameter(Mandatory=$true)]
    [string]$PackagePath
)

try {
    Write-Host "🔄 Starting M365 Agent deployment..."
    
    # Install and import Teams module
    if (-not (Get-Module -ListAvailable -Name MicrosoftTeams)) {
        Write-Host "📦 Installing MicrosoftTeams PowerShell module..."
        Install-Module -Name MicrosoftTeams -Force -AllowClobber -Scope CurrentUser -Repository PSGallery
    }
    Import-Module MicrosoftTeams -Force
    
    # Get module version
    $TeamsModule = Get-Module MicrosoftTeams -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1
    $TeamsVersion = $TeamsModule.Version.ToString()
    Write-Host "📋 MicrosoftTeams module version: $TeamsVersion"
    
    # Parse version for compatibility logic
    $VersionParts = $TeamsVersion.Split('.')
    $MajorVersion = [int]$VersionParts[0]
    
    $connected = $false
    
    # Handle Teams module 7.x+ with ONLY interactive authentication
    if ($MajorVersion -ge 7) {
        Write-Host "🔐 Teams module 7.x+ detected - interactive authentication required"
        Write-Host "⚠️ CRITICAL: Teams module 7.x+ no longer supports client secret authentication"
        Write-Host "💡 A browser window will open for authentication"
        
        try {
            Write-Host "🌐 Starting interactive authentication..."
            Connect-MicrosoftTeams -TenantId $TenantId
            $connected = $true
            Write-Host "✅ Successfully authenticated interactively"
        } catch {
            $errorMsg = $_.Exception.Message
            Write-Host "❌ Interactive authentication failed: $errorMsg"
            
            if ($errorMsg -like "*NonInteractive*") {
                Write-Host "🚨 Confirmed: Teams 7.x+ breaking change detected"
            } elseif ($errorMsg -like "*Unsupported User Type*") {
                Write-Host "🚨 Confirmed: Client secret authentication removed in Teams 7.x+"
            }
            
            Write-Host "📋 Teams module 7.x+ troubleshooting:"
            Write-Host "   1. Run PowerShell as administrator"
            Write-Host "   2. Ensure proper permissions in Azure AD"
            Write-Host "   3. Use manual upload in Teams Admin Center"
            Write-Host "   4. Consider downgrading to Teams module 6.x"
            
            throw "Teams 7.x+ authentication failed - manual upload recommended"
        }
    } else {
        # For Teams module < 7.0, use traditional authentication
        Write-Host "🔐 Teams module < 7.0 detected - using client secret authentication"
        try {
            Connect-MicrosoftTeams -TenantId $TenantId -ApplicationId $ClientId -ClientSecret $ClientSecret
            $connected = $true
            Write-Host "✅ Connected using client secret"
        } catch {
            Write-Host "⚠️ Client secret authentication failed: $($_.Exception.Message)"
            try {
                $SecurePassword = ConvertTo-SecureString $ClientSecret -AsPlainText -Force
                $Credential = New-Object System.Management.Automation.PSCredential($ClientId, $SecurePassword)
                Connect-MicrosoftTeams -TenantId $TenantId -Credential $Credential
                $connected = $true
                Write-Host "✅ Connected using credential fallback"
            } catch {
                throw "All authentication methods failed for Teams module $TeamsVersion"
            }
        }
    }
    
    if (-not $connected) {
        throw "Authentication failed for Teams module $TeamsVersion"
    }
    
    # Deploy the app package
    if (-not (Test-Path $PackagePath)) { 
        throw "Package file not found: $PackagePath" 
    }
    
    Write-Host "📤 Uploading app package: $PackagePath"
    Write-Host "⏳ This may take a few minutes..."
    
    # Parse version for Teams 7.x+ compatibility
    $VersionParts = $TeamsVersion.Split('.')
    $MajorVersion = [int]$VersionParts[0]
    
    # Teams 7.x+ requires DistributionMethod parameter
    if ($MajorVersion -ge 7) {
        Write-Host "🔧 Using Teams 7.x+ compatible upload with DistributionMethod..."
        $AppResult = New-TeamsApp -Path $PackagePath -DistributionMethod Store
    } else {
        Write-Host "🔧 Using legacy upload method..."
        $AppResult = New-TeamsApp -Path $PackagePath
    }
    
    Write-Host "📋 Upload completed, processing result..."
    
    if ($AppResult) {
        Write-Host "✅ App upload successful!"
        Write-Host "DEBUG: AppResult.Id = $($AppResult.Id)"
        Write-Host "DEBUG: AppResult.DisplayName = $($AppResult.DisplayName)"
        Write-Host "DEBUG: AppResult.Version = $($AppResult.Version)"
        
        $Result = @{
            "success" = $true
            "app_id" = $AppResult.Id
            "app_name" = $AppResult.DisplayName
            "app_version" = $AppResult.Version
            "module_version" = $TeamsVersion
        }
        $JsonOutput = $Result | ConvertTo-Json -Compress
        Write-Host "DEBUG: About to output JSON"
        Write-Host "RESULT_JSON:$JsonOutput"
        Write-Host "DEBUG: JSON output completed"
        Write-Host "🎉 Deployment completed successfully!"
    } else {
        throw "App upload returned null result"
    }
} catch {
    Write-Host "DEBUG: Caught exception in standalone PowerShell script"
    Write-Host "DEBUG: Exception message: $($_.Exception.Message)"
    
    $TeamsModule = Get-Module MicrosoftTeams -ListAvailable | Sort-Object Version -Descending | Select-Object -First 1
    $TeamsVersion = if ($TeamsModule) { $TeamsModule.Version.ToString() } else { "Unknown" }
    
    Write-Host "DEBUG: Teams version: $TeamsVersion"
    
    $ErrorResult = @{
        "success" = $false
        "error" = $_.Exception.Message
        "module_version" = $TeamsVersion
    }
    $ErrorJsonOutput = $ErrorResult | ConvertTo-Json -Compress
    Write-Host "DEBUG: About to output error JSON"
    Write-Host "RESULT_JSON:$ErrorJsonOutput"
    Write-Host "DEBUG: Error JSON output completed"
    exit 1
} finally {
    try { Disconnect-MicrosoftTeams -Confirm:$false } catch {}
}
