#!/usr/bin/env pwsh
<#
.SYNOPSIS
    PowerShell Force Delete Script for Stuck Resource Group
    
.DESCRIPTION
    This PowerShell script uses Azure PowerShell modules to force delete
    the stuck resource group 'bciep-test-8' with Container Apps service association links.
    PowerShell sometimes succeeds where Azure CLI fails.
    
.NOTES
    Requires Azure PowerShell module: Install-Module Az
#>

param(
    [string]$ResourceGroupName = "bciep-test-8",
    [switch]$Force
)

# Set error action preference
$ErrorActionPreference = "Continue"

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Color
}

# Function to test Azure PowerShell connection
function Test-AzureConnection {
    Write-ColorOutput "🔑 Testing Azure PowerShell connection..." "Cyan"
    
    try {
        $context = Get-AzContext
        if ($null -eq $context) {
            Write-ColorOutput "❌ Not connected to Azure. Please run: Connect-AzAccount" "Red"
            return $false
        }
        
        Write-ColorOutput "✅ Connected to Azure as: $($context.Account.Id)" "Green"
        Write-ColorOutput "✅ Subscription: $($context.Subscription.Name) ($($context.Subscription.Id))" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "❌ Error checking Azure connection: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Function to find and delete Container App Environments
function Remove-ContainerAppEnvironments {
    param([string]$ResourceGroupName)
    
    Write-ColorOutput "🔍 Searching for Container App Environments..." "Cyan"
    
    try {
        # Get all Container App Environments
        $environments = Get-AzResource -ResourceType "Microsoft.App/managedEnvironments"
        
        if ($environments.Count -eq 0) {
            Write-ColorOutput "✅ No Container App Environments found" "Green"
            return $true
        }
        
        Write-ColorOutput "📊 Found $($environments.Count) Container App Environment(s)" "Yellow"
        
        $problematicEnvs = @()
        
        foreach ($env in $environments) {
            Write-ColorOutput "🏗️ Checking environment: $($env.Name) in RG: $($env.ResourceGroupName)" "White"
            
            try {
                # Get detailed environment info
                $envDetails = Get-AzContainerAppManagedEnv -ResourceGroupName $env.ResourceGroupName -Name $env.Name
                
                if ($envDetails.VnetConfiguration -and $envDetails.VnetConfiguration.InfrastructureSubnetId) {
                    $subnetId = $envDetails.VnetConfiguration.InfrastructureSubnetId
                    Write-ColorOutput "   🌐 Linked to subnet: $subnetId" "Gray"
                    
                    # Check if this is linked to our problematic subnet
                    if ($subnetId -like "*bciep-test-8*" -and $subnetId -like "*agent-subnet*") {
                        Write-ColorOutput "   ⚠️ THIS ENVIRONMENT IS LINKED TO OUR PROBLEMATIC SUBNET!" "Red"
                        $problematicEnvs += $env
                    }
                }
                else {
                    Write-ColorOutput "   ✅ No VNet configuration" "Green"
                }
            }
            catch {
                Write-ColorOutput "   ⚠️ Could not get details for environment $($env.Name): $($_.Exception.Message)" "Yellow"
            }
        }
        
        # Delete problematic environments
        if ($problematicEnvs.Count -gt 0) {
            Write-ColorOutput "🗑️ Found $($problematicEnvs.Count) problematic environment(s) to delete" "Red"
            
            foreach ($env in $problematicEnvs) {
                Write-ColorOutput "🗑️ Deleting Container App Environment: $($env.Name)" "Red"
                
                try {
                    # First, try to get and delete any container apps in this environment
                    $containerApps = Get-AzContainerApp -ResourceGroupName $env.ResourceGroupName | Where-Object { $_.ManagedEnvironmentId -like "*$($env.Name)*" }
                    
                    foreach ($app in $containerApps) {
                        Write-ColorOutput "   🗑️ Deleting Container App: $($app.Name)" "Red"
                        Remove-AzContainerApp -ResourceGroupName $env.ResourceGroupName -Name $app.Name -Force
                    }
                    
                    # Now delete the environment
                    Write-ColorOutput "   🗑️ Deleting Container App Environment: $($env.Name)" "Red"
                    Remove-AzContainerAppManagedEnv -ResourceGroupName $env.ResourceGroupName -Name $env.Name -Force
                    Write-ColorOutput "   ✅ Successfully deleted Container App Environment: $($env.Name)" "Green"
                }
                catch {
                    Write-ColorOutput "   ❌ Failed to delete Container App Environment $($env.Name): $($_.Exception.Message)" "Red"
                    return $false
                }
            }
        }
        else {
            Write-ColorOutput "✅ No problematic Container App Environments found" "Green"
        }
        
        return $true
    }
    catch {
        Write-ColorOutput "❌ Error searching for Container App Environments: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Function to force clear subnet associations
function Clear-SubnetAssociations {
    param([string]$ResourceGroupName)
    
    Write-ColorOutput "🔧 Attempting to clear subnet associations..." "Cyan"
    
    try {
        # Get the VNet
        $vnet = Get-AzVirtualNetwork -ResourceGroupName $ResourceGroupName -Name "agent-vnet-test"
        
        if ($null -eq $vnet) {
            Write-ColorOutput "⚠️ VNet 'agent-vnet-test' not found" "Yellow"
            return $true
        }
        
        # Find the problematic subnet
        $subnet = $vnet.Subnets | Where-Object { $_.Name -eq "agent-subnet" }
        
        if ($null -eq $subnet) {
            Write-ColorOutput "⚠️ Subnet 'agent-subnet' not found" "Yellow"
            return $true
        }
        
        Write-ColorOutput "🔧 Found problematic subnet: $($subnet.Name)" "White"
        
        # Method 1: Try to clear delegations and service association links
        Write-ColorOutput "🔧 Method 1: Clearing delegations and service associations..." "Cyan"
        
        $subnet.Delegations.Clear()
        $subnet.ServiceAssociationLinks.Clear()
        
        try {
            $vnet | Set-AzVirtualNetwork
            Write-ColorOutput "✅ Successfully cleared subnet associations" "Green"
            return $true
        }
        catch {
            Write-ColorOutput "⚠️ Method 1 failed: $($_.Exception.Message)" "Yellow"
        }
        
        # Method 2: Try to remove the subnet entirely
        Write-ColorOutput "🔧 Method 2: Removing problematic subnet..." "Cyan"
        
        try {
            Remove-AzVirtualNetworkSubnetConfig -VirtualNetwork $vnet -Name "agent-subnet"
            $vnet | Set-AzVirtualNetwork
            Write-ColorOutput "✅ Successfully removed problematic subnet" "Green"
            return $true
        }
        catch {
            Write-ColorOutput "⚠️ Method 2 failed: $($_.Exception.Message)" "Yellow"
        }
        
        Write-ColorOutput "❌ All subnet clearing methods failed" "Red"
        return $false
    }
    catch {
        Write-ColorOutput "❌ Error clearing subnet associations: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Function to attempt PowerShell-specific force deletion
function Invoke-PowerShellForceDelete {
    param([string]$ResourceGroupName)
    
    Write-ColorOutput "💥 Attempting PowerShell-specific force deletion..." "Cyan"
    
    try {
        # Method 1: Standard removal with force
        Write-ColorOutput "🔧 Method 1: Standard removal with -Force..." "Cyan"
        
        try {
            Remove-AzResourceGroup -Name $ResourceGroupName -Force -AsJob
            Write-ColorOutput "✅ Force deletion job submitted" "Green"
            
            # Wait a bit and check status
            Start-Sleep -Seconds 30
            
            $rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
            if ($null -eq $rg) {
                Write-ColorOutput "✅ Resource group successfully deleted!" "Green"
                return $true
            }
            else {
                Write-ColorOutput "⏳ Deletion in progress..." "Yellow"
            }
        }
        catch {
            Write-ColorOutput "⚠️ Standard force deletion failed: $($_.Exception.Message)" "Yellow"
        }
        
        # Method 2: Delete resources individually with PowerShell
        Write-ColorOutput "🔧 Method 2: Individual resource deletion..." "Cyan"
        
        try {
            $resources = Get-AzResource -ResourceGroupName $ResourceGroupName
            
            foreach ($resource in $resources) {
                Write-ColorOutput "🗑️ Deleting resource: $($resource.Name) ($($resource.ResourceType))" "White"
                
                try {
                    Remove-AzResource -ResourceId $resource.ResourceId -Force
                    Write-ColorOutput "   ✅ Deleted: $($resource.Name)" "Green"
                }
                catch {
                    Write-ColorOutput "   ⚠️ Failed to delete: $($resource.Name) - $($_.Exception.Message)" "Yellow"
                }
            }
            
            # Now try to delete the empty resource group
            Start-Sleep -Seconds 10
            Remove-AzResourceGroup -Name $ResourceGroupName -Force
            Write-ColorOutput "✅ Resource group deleted after individual resource cleanup" "Green"
            return $true
        }
        catch {
            Write-ColorOutput "⚠️ Individual resource deletion failed: $($_.Exception.Message)" "Yellow"
        }
        
        # Method 3: REST API call via PowerShell
        Write-ColorOutput "🔧 Method 3: REST API via PowerShell..." "Cyan"
        
        try {
            $context = Get-AzContext
            $subscriptionId = $context.Subscription.Id
            
            # Get access token
            $token = [Microsoft.Azure.Commands.Common.Authentication.AzureSession]::Instance.AuthenticationFactory.Authenticate($context.Account, $context.Environment, $context.Tenant.Id, $null, "https://management.azure.com/").AccessToken
            
            $headers = @{
                'Authorization' = "Bearer $token"
                'Content-Type' = 'application/json'
            }
            
            $uri = "https://management.azure.com/subscriptions/$subscriptionId/resourcegroups/$ResourceGroupName" + "?forceDeletionTypes=Microsoft.App/managedEnvironments,Microsoft.Network/virtualNetworks&api-version=2021-04-01"
            
            $response = Invoke-RestMethod -Uri $uri -Method Delete -Headers $headers
            Write-ColorOutput "✅ REST API deletion request submitted" "Green"
            
            # Check if deletion completed
            Start-Sleep -Seconds 30
            $rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
            if ($null -eq $rg) {
                Write-ColorOutput "✅ Resource group successfully deleted via REST API!" "Green"
                return $true
            }
            else {
                Write-ColorOutput "⏳ REST API deletion in progress..." "Yellow"
            }
        }
        catch {
            Write-ColorOutput "⚠️ REST API deletion failed: $($_.Exception.Message)" "Yellow"
        }
        
        return $false
    }
    catch {
        Write-ColorOutput "❌ PowerShell force deletion failed: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Function to monitor deletion progress
function Watch-DeletionProgress {
    param([string]$ResourceGroupName, [int]$MaxAttempts = 20)
    
    Write-ColorOutput "⏳ Monitoring deletion progress..." "Cyan"
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        Write-ColorOutput "🔍 Check $i/$MaxAttempts - Verifying if resource group still exists..." "White"
        
        $rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
        
        if ($null -eq $rg) {
            Write-ColorOutput "✅ Resource group '$ResourceGroupName' successfully deleted!" "Green"
            return $true
        }
        else {
            $resources = Get-AzResource -ResourceGroupName $ResourceGroupName -ErrorAction SilentlyContinue
            Write-ColorOutput "⏳ Still exists with $($resources.Count) resource(s). Waiting..." "Yellow"
            Start-Sleep -Seconds 30
        }
    }
    
    Write-ColorOutput "⚠️ Deletion monitoring timeout reached" "Yellow"
    return $false
}

# Main execution
function Main {
    Write-ColorOutput "💥 POWERSHELL FORCE DELETE TOOL FOR AZURE RESOURCE GROUP" "Magenta"
    Write-ColorOutput "============================================================" "Magenta"
    Write-ColorOutput "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "Gray"
    Write-ColorOutput "Target Resource Group: $ResourceGroupName" "Gray"
    Write-ColorOutput "============================================================" "Magenta"
    
    # Check if running with Force parameter
    if (-not $Force) {
        Write-ColorOutput "⚠️ WARNING: This will aggressively attempt to delete the resource group" "Red"
        Write-ColorOutput "⚠️ This should only be used when standard deletion has been stuck" "Red"
        Write-ColorOutput "⚠️ This process may take up to 30 minutes" "Red"
        
        $confirmation = Read-Host "`nType 'FORCE DELETE NOW' to proceed"
        if ($confirmation -ne "FORCE DELETE NOW") {
            Write-ColorOutput "❌ Force deletion not confirmed" "Red"
            return 1
        }
    }
    
    # Test Azure connection
    if (-not (Test-AzureConnection)) {
        Write-ColorOutput "❌ Please connect to Azure first: Connect-AzAccount" "Red"
        return 1
    }
    
    # Check if resource group exists
    $rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
    if ($null -eq $rg) {
        Write-ColorOutput "✅ Resource group '$ResourceGroupName' does not exist (already deleted?)" "Green"
        return 0
    }
    
    Write-ColorOutput "📊 Resource group exists. Starting comprehensive deletion process..." "White"
    
    # Step 1: Remove Container App Environments
    Write-ColorOutput "`n📋 Step 1: Removing Container App Environments..." "Cyan"
    $envSuccess = Remove-ContainerAppEnvironments -ResourceGroupName $ResourceGroupName
    
    if ($envSuccess) {
        Write-ColorOutput "✅ Container App Environment cleanup completed" "Green"
        Start-Sleep -Seconds 60  # Wait for cleanup to propagate
    }
    
    # Step 2: Clear subnet associations
    Write-ColorOutput "`n📋 Step 2: Clearing subnet associations..." "Cyan"
    $subnetSuccess = Clear-SubnetAssociations -ResourceGroupName $ResourceGroupName
    
    if ($subnetSuccess) {
        Write-ColorOutput "✅ Subnet association cleanup completed" "Green"
        Start-Sleep -Seconds 30
    }
    
    # Step 3: PowerShell force deletion
    Write-ColorOutput "`n📋 Step 3: PowerShell force deletion..." "Cyan"
    $deleteSuccess = Invoke-PowerShellForceDelete -ResourceGroupName $ResourceGroupName
    
    # Step 4: Monitor progress
    if ($deleteSuccess -or $envSuccess -or $subnetSuccess) {
        Write-ColorOutput "`n📋 Step 4: Monitoring deletion progress..." "Cyan"
        $monitorSuccess = Watch-DeletionProgress -ResourceGroupName $ResourceGroupName
        
        if ($monitorSuccess) {
            Write-ColorOutput "`n🎉 FORCE DELETION COMPLETED SUCCESSFULLY!" "Green"
            return 0
        }
    }
    
    # If we get here, provide manual guidance
    Write-ColorOutput "`n💔 AUTOMATED DELETION FAILED" "Red"
    Write-ColorOutput "============================================================" "Red"
    Write-ColorOutput "Manual steps to try:" "Yellow"
    Write-ColorOutput "1. Wait 2-4 hours and try again (sometimes it resolves itself)" "White"
    Write-ColorOutput "2. Try deleting through Azure Portal" "White"
    Write-ColorOutput "3. Open a Microsoft Support ticket" "White"
    Write-ColorOutput "4. Use Azure CLI: az group delete --name $ResourceGroupName --force-deletion-types Microsoft.App/managedEnvironments" "White"
    
    return 1
}

# Execute main function
exit (Main)
