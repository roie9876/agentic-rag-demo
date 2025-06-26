#!/usr/bin/env pwsh
# Teams PowerShell Module Version Checker and Compatibility Guide

Write-Host "🔍 Teams PowerShell Module Compatibility Checker" -ForegroundColor Cyan
Write-Host ("=" * 50) -ForegroundColor Cyan

try {
    # Check if Teams module is installed
    $TeamsModule = Get-Module -ListAvailable -Name MicrosoftTeams | Sort-Object Version -Descending | Select-Object -First 1
    
    if ($TeamsModule) {
        $TeamsVersion = $TeamsModule.Version.ToString()
        $MajorVersion = $TeamsModule.Version.Major
        
        Write-Host "📋 MicrosoftTeams module found:"
        Write-Host "   Version: $TeamsVersion" -ForegroundColor Green
        Write-Host "   Location: $($TeamsModule.ModuleBase)"
        
        # Provide compatibility guidance
        if ($MajorVersion -ge 7) {
            Write-Host ""
            Write-Host "🚨 COMPATIBILITY ALERT:" -ForegroundColor Red
            Write-Host "   Teams module 7.x+ has breaking changes" -ForegroundColor Yellow
            Write-Host "   Client secret authentication is NO LONGER SUPPORTED" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "📋 For M365 Agent deployment with Teams 7.x+:" -ForegroundColor Cyan
            Write-Host "   ✅ RECOMMENDED: Use manual upload in Teams Admin Center"
            Write-Host "   ⚠️  PowerShell automation may fail"
            Write-Host "   🔧 Alternative: Downgrade to Teams module 6.x"
            Write-Host ""
            Write-Host "💡 Downgrade command:" -ForegroundColor Cyan
            Write-Host "   Uninstall-Module MicrosoftTeams -Force" -ForegroundColor Gray
            Write-Host "   Install-Module MicrosoftTeams -RequiredVersion 6.6.0 -Force" -ForegroundColor Gray
        } else {
            Write-Host ""
            Write-Host "✅ COMPATIBILITY: GOOD" -ForegroundColor Green
            Write-Host "   Teams module $MajorVersion.x supports client secret authentication" -ForegroundColor Green
            Write-Host "   PowerShell automation should work normally" -ForegroundColor Green
        }
        
    } else {
        Write-Host "❌ MicrosoftTeams module not found" -ForegroundColor Red
        Write-Host ""
        Write-Host "📦 To install Teams module:" -ForegroundColor Cyan
        Write-Host "   Install-Module -Name MicrosoftTeams -Force -AllowClobber" -ForegroundColor Gray
        Write-Host ""
        Write-Host "💡 For M365 Agent compatibility, you may want to install version 6.x:" -ForegroundColor Cyan
        Write-Host "   Install-Module MicrosoftTeams -RequiredVersion 6.6.0 -Force" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "❌ Error checking Teams module: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "📚 Additional Resources:" -ForegroundColor Cyan
Write-Host "   - Teams Admin Center: https://admin.teams.microsoft.com"
Write-Host "   - Teams module docs: https://docs.microsoft.com/powershell/teams/"
Write-Host "   - Manual upload guide: Use Teams Admin Center > Teams apps > Manage apps > Upload"
