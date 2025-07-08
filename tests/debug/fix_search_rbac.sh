#!/bin/bash
# Fix AI Search RBAC Permissions for Managed Identity
# This script assigns the necessary roles to the VM's managed identity for AI Search access

echo "🔧 Fixing AI Search RBAC permissions for managed identity..."

# Get the VM's managed identity principal ID
echo "📋 Getting VM's managed identity information..."
PRINCIPAL_ID=$(az vm identity show --name $(hostname) --resource-group $(curl -s -H Metadata:true "http://169.254.169.254/metadata/instance/compute/resourceGroupName?api-version=2021-02-01&format=text") --query principalId -o tsv 2>/dev/null)

if [ -z "$PRINCIPAL_ID" ]; then
    echo "❌ Could not get managed identity principal ID. Make sure managed identity is enabled on this VM."
    echo "ℹ️  Run: az vm identity assign --name $(hostname) --resource-group <YOUR_RG>"
    exit 1
fi

echo "✅ Found managed identity principal ID: $PRINCIPAL_ID"

# Get current subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "📋 Using subscription: $SUBSCRIPTION_ID"

# Get resource group from instance metadata
RESOURCE_GROUP=$(curl -s -H Metadata:true "http://169.254.169.254/metadata/instance/compute/resourceGroupName?api-version=2021-02-01&format=text")
echo "📋 Using resource group: $RESOURCE_GROUP"

# Assign Search Index Data Reader role
echo "🔧 Assigning 'Search Index Data Reader' role..."
az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Search Index Data Reader" \
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/private-ai-search" \
    --output table

# Assign Search Service Contributor role  
echo "🔧 Assigning 'Search Service Contributor' role..."
az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Search Service Contributor" \
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/private-ai-search" \
    --output table

echo ""
echo "✅ RBAC roles assigned successfully!"
echo "⏳ Note: It may take 5-10 minutes for permissions to propagate."
echo "🔄 Run the health check again in a few minutes to verify."
