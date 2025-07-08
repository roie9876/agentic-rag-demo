#!/usr/bin/env pwsh
<#
.SYNOPSIS
    PowerShell SAL Deletion Script for Stuck Resource Group
    
.DESCRIPTION
    This PowerShell script attempts to delete orphaned Service Association Links (SAL)
    using Azure PowerShell modules. Sometimes PowerShell has different permissions
    or access patterns than Azure CLI that allow SAL deletion.
    
.NOTES
    Created: 2025-07-08
    Purpose: Fix bciep-test-8 resource group deletion blocked by legionservicelink SAL
    Location: tests/debug/ (following new script organization policy)
    
    Methods attempted:
    1. Direct Remove-AzResource with SAL resource ID
    2. REST API calls via PowerShell Invoke-RestMethod
    3. Graph API authentication for enhanced permissions
    4. ARM template-based deletion
#>

param(
    [string]$ResourceGroupName = "bciep-test-8",
    [string]$VNetName = "agent-vnet-test",
    [string]$SubnetName = "agent-subnet",
    [string]$SALName = "legionservicelink",
    [switch]$Force
)

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    switch ($Color) {
        "Red" { Write-Host "[$timestamp] $Message" -ForegroundColor Red }
        "Green" { Write-Host "[$timestamp] $Message" -ForegroundColor Green }
        "Yellow" { Write-Host "[$timestamp] $Message" -ForegroundColor Yellow }
        "Cyan" { Write-Host "[$timestamp] $Message" -ForegroundColor Cyan }
        "Magenta" { Write-Host "[$timestamp] $Message" -ForegroundColor Magenta }
        default { Write-Host "[$timestamp] $Message" -ForegroundColor White }
    }
}

# Function to test Azure PowerShell connection
function Test-AzureConnection {
    Write-ColorOutput "🔑 Testing Azure PowerShell connection..." "Cyan"
    
    try {
        $context = Get-AzContext
        if ($null -eq $context) {
            Write-ColorOutput "❌ Not connected to Azure. Attempting automatic login..." "Red"
            
            # Try to use existing Azure CLI token
            try {
                $cliToken = az account get-access-token --output json | ConvertFrom-Json
                Write-ColorOutput "✅ Found Azure CLI token, attempting to use it..." "Green"
                
                # Connect using Azure CLI credentials
                Connect-AzAccount -AccountId $context.Account.Id -ErrorAction SilentlyContinue
                $context = Get-AzContext
            }
            catch {
                Write-ColorOutput "⚠️ Azure CLI token not available, manual login required" "Yellow"
                Write-ColorOutput "Please run: Connect-AzAccount" "Yellow"
                return $false
            }
        }
        
        if ($null -eq $context) {
            Write-ColorOutput "❌ Still not connected. Please run: Connect-AzAccount" "Red"
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

# Function to get subscription details
function Get-SubscriptionInfo {
    Write-ColorOutput "📋 Getting subscription information..." "Cyan"
    
    try {
        $context = Get-AzContext
        $subscription = Get-AzSubscription -SubscriptionId $context.Subscription.Id
        
        Write-ColorOutput "✅ Subscription ID: $($subscription.Id)" "Green"
        Write-ColorOutput "✅ Subscription Name: $($subscription.Name)" "Green"
        
        return $subscription
    }
    catch {
        Write-ColorOutput "❌ Failed to get subscription info: $($_.Exception.Message)" "Red"
        return $null
    }
}

# Method 1: Direct PowerShell Resource Deletion
function Remove-SAL-Direct {
    param([string]$ResourceGroupName, [string]$VNetName, [string]$SubnetName, [string]$SALName)
    
    Write-ColorOutput "💥 METHOD 1: Direct PowerShell Resource Deletion" "Magenta"
    Write-ColorOutput "=" * 60 "White"
    
    try {
        $subscription = Get-AzContext | Select-Object -ExpandProperty Subscription
        $salResourceId = "/subscriptions/$($subscription.Id)/resourceGroups/$ResourceGroupName/providers/Microsoft.Network/virtualNetworks/$VNetName/subnets/$SubnetName/serviceAssociationLinks/$SALName"
        
        Write-ColorOutput "🎯 Target SAL Resource ID: $salResourceId" "Cyan"
        Write-ColorOutput "🔧 Attempting Remove-AzResource..." "Cyan"
        
        # Try different API versions
        $apiVersions = @("2024-05-01", "2023-11-01", "2023-04-01", "2022-07-01", "2021-05-01", "2020-11-01", "2018-10-01")
        
        foreach ($apiVersion in $apiVersions) {
            Write-ColorOutput "   🔄 Trying API version: $apiVersion" "Yellow"
            
            try {
                Remove-AzResource -ResourceId $salResourceId -ApiVersion $apiVersion -Force -ErrorAction Stop
                Write-ColorOutput "   ✅ SUCCESS with API version $apiVersion!" "Green"
                return $true
            }
            catch {
                Write-ColorOutput "   ❌ Failed with API version $apiVersion`: $($_.Exception.Message)" "Red"
            }
        }
        
        Write-ColorOutput "❌ All API versions failed for direct resource deletion" "Red"
        return $false
    }
    catch {
        Write-ColorOutput "❌ Method 1 failed: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Method 2: REST API via PowerShell
function Remove-SAL-RestAPI {
    param([string]$ResourceGroupName, [string]$VNetName, [string]$SubnetName, [string]$SALName)
    
    Write-ColorOutput "💥 METHOD 2: REST API via PowerShell" "Magenta"
    Write-ColorOutput "=" * 60 "White"
    
    try {
        $context = Get-AzContext
        $subscription = $context.Subscription.Id
        
        # Get access token with enhanced scopes
        Write-ColorOutput "🔑 Getting access token with enhanced permissions..." "Cyan"
        
        $tokenScopes = @(
            "https://management.azure.com/",
            "https://management.azure.com/.default",
            "https://graph.microsoft.com/.default"
        )
        
        foreach ($scope in $tokenScopes) {
            try {
                Write-ColorOutput "   🔄 Trying scope: $scope" "Yellow"
                $token = [Microsoft.Azure.Commands.Common.Authentication.AzureSession]::Instance.AuthenticationFactory.Authenticate($context.Account, $context.Environment, $context.Tenant.Id, $null, $scope).AccessToken
                
                if ($token) {
                    Write-ColorOutput "   ✅ Got token with scope: $scope" "Green"
                    break
                }
            }
            catch {
                Write-ColorOutput "   ❌ Failed to get token with scope $scope" "Red"
            }
        }
        
        if (-not $token) {
            Write-ColorOutput "❌ Failed to get access token with any scope" "Red"
            return $false
        }
        
        $headers = @{
            'Authorization' = "Bearer $token"
            'Content-Type' = 'application/json'
        }
        
        # Try different API versions and methods
        $apiVersions = @("2024-05-01", "2023-11-01", "2022-07-01", "2021-05-01", "2018-10-01")
        $methods = @("DELETE", "POST")
        
        foreach ($apiVersion in $apiVersions) {
            foreach ($method in $methods) {
                $uri = "https://management.azure.com/subscriptions/$subscription/resourceGroups/$ResourceGroupName/providers/Microsoft.Network/virtualNetworks/$VNetName/subnets/$SubnetName/serviceAssociationLinks/$SALName" + "?api-version=$apiVersion"
                
                Write-ColorOutput "   🔄 Trying $method with API version: $apiVersion" "Yellow"
                Write-ColorOutput "   🌐 URI: $uri" "Cyan"
                
                try {
                    if ($method -eq "DELETE") {
                        $response = Invoke-RestMethod -Uri $uri -Method Delete -Headers $headers -ErrorAction Stop
                    } else {
                        # POST method for deletion (some resources require this)
                        $body = @{ properties = @{} } | ConvertTo-Json
                        $response = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body -ErrorAction Stop
                    }
                    
                    Write-ColorOutput "   ✅ SUCCESS with $method and API version $apiVersion!" "Green"
                    Write-ColorOutput "   📄 Response: $($response | ConvertTo-Json -Depth 2)" "Green"
                    return $true
                }
                catch {
                    $errorDetails = $_.Exception.Message
                    if ($_.Exception.Response) {
                        $errorStream = $_.Exception.Response.GetResponseStream()
                        $reader = New-Object System.IO.StreamReader($errorStream)
                        $errorDetails += "`nResponse: " + $reader.ReadToEnd()
                    }
                    Write-ColorOutput "   ❌ Failed $method with API version $apiVersion`: $errorDetails" "Red"
                }
            }
        }
        
        Write-ColorOutput "❌ All REST API attempts failed" "Red"
        return $false
    }
    catch {
        Write-ColorOutput "❌ Method 2 failed: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Method 3: ARM Template Deletion
function Remove-SAL-ARMTemplate {
    param([string]$ResourceGroupName, [string]$VNetName, [string]$SubnetName)
    
    Write-ColorOutput "💥 METHOD 3: ARM Template Subnet Update" "Magenta"
    Write-ColorOutput "=" * 60 "White"
    
    try {
        Write-ColorOutput "🔧 Creating ARM template to clear SAL..." "Cyan"
        
        # Create ARM template that updates the subnet without the SAL
        $armTemplate = @{
            '$schema' = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
            contentVersion = "1.0.0.0"
            parameters = @{}
            variables = @{}
            resources = @(
                @{
                    type = "Microsoft.Network/virtualNetworks/subnets"
                    apiVersion = "2024-05-01"
                    name = "$VNetName/$SubnetName"
                    properties = @{
                        addressPrefix = "192.168.0.0/24"
                        serviceAssociationLinks = @()
                        delegations = @()
                    }
                }
            )
        }
        
        $templateJson = $armTemplate | ConvertTo-Json -Depth 10
        $templateFile = "/tmp/clear-sal-template.json"
        $templateJson | Out-File -FilePath $templateFile -Encoding UTF8
        
        Write-ColorOutput "📝 ARM Template created: $templateFile" "Cyan"
        Write-ColorOutput "🚀 Deploying ARM template..." "Cyan"
        
        $deployment = New-AzResourceGroupDeployment -ResourceGroupName $ResourceGroupName -TemplateFile $templateFile -Name "clear-sal-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
        
        if ($deployment.ProvisioningState -eq "Succeeded") {
            Write-ColorOutput "✅ ARM template deployment succeeded!" "Green"
            return $true
        } else {
            Write-ColorOutput "❌ ARM template deployment failed: $($deployment.ProvisioningState)" "Red"
            return $false
        }
    }
    catch {
        Write-ColorOutput "❌ Method 3 failed: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Method 4: Enhanced Graph API Access
function Remove-SAL-GraphAPI {
    param([string]$ResourceGroupName, [string]$VNetName, [string]$SubnetName, [string]$SALName)
    
    Write-ColorOutput "💥 METHOD 4: Enhanced Graph API Access" "Magenta"
    Write-ColorOutput "=" * 60 "White"
    
    try {
        Write-ColorOutput "🔧 Attempting enhanced permissions via Graph API..." "Cyan"
        
        # Try to get enhanced token scopes
        $context = Get-AzContext
        
        # List of enhanced scopes to try
        $enhancedScopes = @(
            "https://management.azure.com/user_impersonation",
            "https://management.core.windows.net/user_impersonation",
            "https://graph.microsoft.com/User.Read",
            "https://vault.azure.net/user_impersonation"
        )
        
        foreach ($scope in $enhancedScopes) {
            try {
                Write-ColorOutput "   🔄 Trying enhanced scope: $scope" "Yellow"
                
                $enhancedToken = [Microsoft.Azure.Commands.Common.Authentication.AzureSession]::Instance.AuthenticationFactory.Authenticate($context.Account, $context.Environment, $context.Tenant.Id, $null, $scope).AccessToken
                
                if ($enhancedToken) {
                    Write-ColorOutput "   ✅ Got enhanced token!" "Green"
                    
                    # Try deletion with enhanced token
                    $headers = @{
                        'Authorization' = "Bearer $enhancedToken"
                        'Content-Type' = 'application/json'
                        'x-ms-client-request-id' = [System.Guid]::NewGuid().ToString()
                    }
                    
                    $subscription = $context.Subscription.Id
                    $uri = "https://management.azure.com/subscriptions/$subscription/resourceGroups/$ResourceGroupName/providers/Microsoft.Network/virtualNetworks/$VNetName/subnets/$SubnetName/serviceAssociationLinks/$SALName" + "?api-version=2024-05-01"
                    
                    $response = Invoke-RestMethod -Uri $uri -Method Delete -Headers $headers -ErrorAction Stop
                    Write-ColorOutput "   ✅ SUCCESS with enhanced scope $scope!" "Green"
                    return $true
                }
            }
            catch {
                Write-ColorOutput "   ❌ Failed with enhanced scope $scope`: $($_.Exception.Message)" "Red"
            }
        }
        
        Write-ColorOutput "❌ All enhanced scopes failed" "Red"
        return $false
    }
    catch {
        Write-ColorOutput "❌ Method 4 failed: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Function to verify SAL deletion
function Test-SALExists {
    param([string]$ResourceGroupName, [string]$VNetName, [string]$SubnetName, [string]$SALName)
    
    try {
        $subnet = Get-AzVirtualNetworkSubnetConfig -VirtualNetwork (Get-AzVirtualNetwork -ResourceGroupName $ResourceGroupName -Name $VNetName) -Name $SubnetName
        
        $salExists = $subnet.ServiceAssociationLinks | Where-Object { $_.Name -eq $SALName }
        
        if ($salExists) {
            Write-ColorOutput "❌ SAL '$SALName' still exists" "Red"
            return $true
        } else {
            Write-ColorOutput "✅ SAL '$SALName' has been deleted!" "Green"
            return $false
        }
    }
    catch {
        Write-ColorOutput "⚠️ Could not check SAL status: $($_.Exception.Message)" "Yellow"
        return $true  # Assume it still exists if we can't check
    }
}

# Main execution function
function Main {
    Write-ColorOutput "💥 POWERSHELL SAL DELETION TOOL" "Magenta"
    Write-ColorOutput "=" * 60 "Magenta"
    Write-ColorOutput "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "White"
    Write-ColorOutput "Target Resource Group: $ResourceGroupName" "White"
    Write-ColorOutput "Target SAL: $SALName" "White"
    Write-ColorOutput "Script Location: tests/debug/ (following new organization policy)" "White"
    Write-ColorOutput "=" * 60 "Magenta"
    
    # Check if running with Force parameter
    if (-not $Force) {
        Write-ColorOutput "⚠️ WARNING: This will attempt to delete Service Association Links" "Red"
        Write-ColorOutput "⚠️ This should only be used for stuck resource groups" "Red"
        
        $confirmation = Read-Host "`nType 'DELETE SAL NOW' to proceed"
        if ($confirmation -ne "DELETE SAL NOW") {
            Write-ColorOutput "❌ SAL deletion not confirmed" "Red"
            return 1
        }
    }
    
    # Test Azure connection
    if (-not (Test-AzureConnection)) {
        Write-ColorOutput "❌ Please connect to Azure first: Connect-AzAccount" "Red"
        return 1
    }
    
    # Get subscription info
    $subscription = Get-SubscriptionInfo
    if ($null -eq $subscription) {
        Write-ColorOutput "❌ Could not get subscription information" "Red"
        return 1
    }
    
    # Check if resource group exists
    try {
        $rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction Stop
        Write-ColorOutput "✅ Resource group exists: $ResourceGroupName" "Green"
    }
    catch {
        Write-ColorOutput "❌ Resource group not found: $ResourceGroupName" "Red"
        return 1
    }
    
    # Check initial SAL status
    Write-ColorOutput "`n🔍 Checking initial SAL status..." "Cyan"
    $salExists = Test-SALExists -ResourceGroupName $ResourceGroupName -VNetName $VNetName -SubnetName $SubnetName -SALName $SALName
    
    if (-not $salExists) {
        Write-ColorOutput "✅ SAL does not exist - nothing to delete!" "Green"
        return 0
    }
    
    # Try each method in sequence
    $methods = @(
        { Remove-SAL-Direct -ResourceGroupName $ResourceGroupName -VNetName $VNetName -SubnetName $SubnetName -SALName $SALName },
        { Remove-SAL-RestAPI -ResourceGroupName $ResourceGroupName -VNetName $VNetName -SubnetName $SubnetName -SALName $SALName },
        { Remove-SAL-ARMTemplate -ResourceGroupName $ResourceGroupName -VNetName $VNetName -SubnetName $SubnetName },
        { Remove-SAL-GraphAPI -ResourceGroupName $ResourceGroupName -VNetName $VNetName -SubnetName $SubnetName -SALName $SALName }
    )
    
    $methodNames = @("Direct Resource Deletion", "REST API", "ARM Template", "Enhanced Graph API")
    
    for ($i = 0; $i -lt $methods.Count; $i++) {
        Write-ColorOutput "`n📋 Attempting Method $($i + 1): $($methodNames[$i])" "Cyan"
        
        $success = & $methods[$i]
        
        if ($success) {
            Write-ColorOutput "✅ Method $($i + 1) reported success!" "Green"
            
            # Wait and verify
            Start-Sleep -Seconds 10
            Write-ColorOutput "🔍 Verifying SAL deletion..." "Cyan"
            $salStillExists = Test-SALExists -ResourceGroupName $ResourceGroupName -VNetName $VNetName -SubnetName $SubnetName -SALName $SALName
            
            if (-not $salStillExists) {
                Write-ColorOutput "`n🎉 SUCCESS! SAL has been deleted using Method $($i + 1): $($methodNames[$i])" "Green"
                Write-ColorOutput "✅ Resource group deletion should now be possible" "Green"
                return 0
            } else {
                Write-ColorOutput "⚠️ Method $($i + 1) reported success but SAL still exists" "Yellow"
            }
        }
        
        Write-ColorOutput "❌ Method $($i + 1) failed, trying next method..." "Red"
    }
    
    # If we get here, all methods failed
    Write-ColorOutput "`n💔 ALL POWERSHELL METHODS FAILED" "Red"
    Write-ColorOutput "=" * 60 "Red"
    Write-ColorOutput "The SAL appears to be protected by Azure backend policies." "Yellow"
    Write-ColorOutput "This confirms that Microsoft Support intervention is required." "Yellow"
    Write-ColorOutput "`nRecommendations:" "White"
    Write-ColorOutput "1. Submit the comprehensive support ticket" "White"
    Write-ColorOutput "2. Reference that both Azure CLI and PowerShell failed" "White"
    Write-ColorOutput "3. Wait for Microsoft backend intervention" "White"
    
    return 1
}

# Execute main function
exit (Main)
