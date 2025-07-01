#!/bin/bash
"""
RBAC Role Assignment Script for Private Endpoint Resources
=========================================================
This script assigns the necessary RBAC roles to your VM's managed identity
for accessing Azure OpenAI, Document Intelligence, and AI Search through private endpoints.
"""

# Set error handling
set -e

echo "🔒 Setting up RBAC permissions for Private Endpoint Resources"
echo "============================================================="

# Get current subscription and tenant info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "📋 Current Context:"
echo "   Subscription: $SUBSCRIPTION_ID"
echo "   Tenant: $TENANT_ID"

# VM details from diagnostics
VM_NAME="linux-private-vm"
RESOURCE_GROUP="private-rg"

echo ""
echo "🔍 Getting VM's Managed Identity Principal ID..."
PRINCIPAL_ID=$(az vm identity show --name $VM_NAME --resource-group $RESOURCE_GROUP --query principalId -o tsv)

if [ -z "$PRINCIPAL_ID" ]; then
    echo "❌ No managed identity found for VM $VM_NAME"
    echo "   Please enable system-assigned managed identity first:"
    echo "   az vm identity assign --name $VM_NAME --resource-group $RESOURCE_GROUP"
    exit 1
fi

echo "✅ VM Managed Identity Principal ID: $PRINCIPAL_ID"

# Resource details - you'll need to replace these with your actual resource names
echo ""
echo "🔧 Please update the resource names in this script with your actual resources:"
echo "   - Replace OPENAI_RESOURCE_NAME with your OpenAI resource name"
echo "   - Replace DOC_INTEL_RESOURCE_NAME with your Document Intelligence resource name"  
echo "   - Replace SEARCH_RESOURCE_NAME with your AI Search resource name"
echo "   - Replace RESOURCE_GROUP_NAME with your resource group (if different)"
echo ""

# You need to update these with your actual resource names
OPENAI_RESOURCE_NAME="private-openai-agentic"
DOC_INTEL_RESOURCE_NAME="private-doc-int"
SEARCH_RESOURCE_NAME="private-ai-search"
RESOURCE_GROUP_NAME="private-rg"  # Update if your resources are in a different RG

echo "🚀 Assigning RBAC roles..."
echo ""

# OpenAI roles
echo "🧠 Assigning OpenAI roles..."
OPENAI_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.CognitiveServices/accounts/$OPENAI_RESOURCE_NAME"

echo "   Assigning 'Cognitive Services OpenAI User' role..."
az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Cognitive Services OpenAI User" \
    --scope "$OPENAI_SCOPE" \
    --output table

echo "   Assigning 'Cognitive Services User' role..."
az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Cognitive Services User" \
    --scope "$OPENAI_SCOPE" \
    --output table

# Document Intelligence roles
echo ""
echo "📄 Assigning Document Intelligence roles..."
DOC_INTEL_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.CognitiveServices/accounts/$DOC_INTEL_RESOURCE_NAME"

echo "   Assigning 'Cognitive Services User' role..."
az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Cognitive Services User" \
    --scope "$DOC_INTEL_SCOPE" \
    --output table

# AI Search roles
echo ""
echo "🔍 Assigning AI Search roles..."
SEARCH_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Search/searchServices/$SEARCH_RESOURCE_NAME"

echo "   Assigning 'Search Index Data Reader' role..."
az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Search Index Data Reader" \
    --scope "$SEARCH_SCOPE" \
    --output table

echo "   Assigning 'Search Service Contributor' role..."
az role assignment create \
    --assignee "$PRINCIPAL_ID" \
    --role "Search Service Contributor" \
    --scope "$SEARCH_SCOPE" \
    --output table

echo ""
echo "✅ RBAC role assignments completed!"
echo ""
echo "🔄 Note: It may take a few minutes for the role assignments to propagate."
echo "   Wait 2-3 minutes before testing the connections again."
echo ""
echo "🧪 To test the setup:"
echo "   1. Wait 2-3 minutes for propagation"
echo "   2. Run: python3 diagnose_private_endpoints.py"
echo "   3. Or use the Streamlit app Health Check tab"
echo ""
echo "📋 Summary of roles assigned to VM '$VM_NAME' managed identity:"
echo "   OpenAI: Cognitive Services OpenAI User, Cognitive Services User"
echo "   Document Intelligence: Cognitive Services User"
echo "   AI Search: Search Index Data Reader, Search Service Contributor"
