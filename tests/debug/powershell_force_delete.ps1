# PowerShell Script to Force Remove Stuck Resource Group
# This script uses Azure PowerShell to attempt force removal

# Install Azure PowerShell module if not present
if (-not (Get-Module -ListAvailable -Name Az)) {
    Install-Module -Name Az -Force -AllowClobber -Scope CurrentUser
}

# Connect to Azure
Connect-AzAccount

# Set subscription
$subscriptionId = "7aa77d2e-cbec-48b4-8518-9802543b25af"
Set-AzContext -SubscriptionId $subscriptionId

# Resource group details
$resourceGroupName = "bciep-test-8"
$vnetName = "agent-vnet-test"
$subnetName = "agent-subnet"

Write-Host "🔍 Attempting PowerShell-based force deletion..." -ForegroundColor Yellow

# Method 1: Try to force remove the service association link directly
try {
    Write-Host "📋 Step 1: Attempting to clear service association links via PowerShell..." -ForegroundColor Yellow
    
    # Get the virtual network
    $vnet = Get-AzVirtualNetwork -ResourceGroupName $resourceGroupName -Name $vnetName
    
    # Get the subnet
    $subnet = $vnet.Subnets | Where-Object { $_.Name -eq $subnetName }
    
    if ($subnet -and $subnet.ServiceAssociationLinks.Count -gt 0) {
        Write-Host "⚠️ Found $($subnet.ServiceAssociationLinks.Count) service association link(s)" -ForegroundColor Red
        
        # Clear service association links
        $subnet.ServiceAssociationLinks.Clear()
        $subnet.Delegations.Clear()
        
        # Update the virtual network
        $vnet | Set-AzVirtualNetwork
        
        Write-Host "✅ Service association links cleared via PowerShell" -ForegroundColor Green
        Start-Sleep -Seconds 30
    }
} catch {
    Write-Host "❌ PowerShell method failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Method 2: Try ARM template-based deletion
try {
    Write-Host "📋 Step 2: Attempting ARM template-based force deletion..." -ForegroundColor Yellow
    
    $armTemplate = @{
        '$schema' = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
        'contentVersion' = '1.0.0.0'
        'parameters' = @{}
        'variables' = @{}
        'resources' = @()
        'outputs' = @{}
    }
    
    $templateFile = [System.IO.Path]::GetTempFileName() + ".json"
    $armTemplate | ConvertTo-Json -Depth 10 | Out-File -FilePath $templateFile
    
    # Deploy empty template to force cleanup
    New-AzResourceGroupDeployment -ResourceGroupName $resourceGroupName -TemplateFile $templateFile -Mode Complete -Force
    
    Remove-Item $templateFile
    Write-Host "✅ ARM template deployment completed" -ForegroundColor Green
    
} catch {
    Write-Host "❌ ARM template method failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Method 3: Final force deletion attempt
try {
    Write-Host "📋 Step 3: Final force deletion attempt..." -ForegroundColor Yellow
    
    Remove-AzResourceGroup -Name $resourceGroupName -Force -AsJob
    
    Write-Host "✅ Force deletion job started" -ForegroundColor Green
    Write-Host "ℹ️ Check Azure portal for deletion status" -ForegroundColor Blue
    
} catch {
    Write-Host "❌ Force deletion failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "🏁 PowerShell script completed. Check Azure portal for final status." -ForegroundColor Blue
