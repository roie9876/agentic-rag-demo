#!/bin/bash

# Azure Bicep Deployment Script for Private DNS Configuration
# This script deploys DNS zones and configurations for existing private endpoints

set -e  # Exit on any error

# Configuration
RESOURCE_GROUP="private-rg"
LOCATION="swedencentral"
DEPLOYMENT_NAME="private-dns-deployment-$(date +%Y%m%d%H%M%S)"
BICEP_FILE="private-endpoint-and-dns.bicep"
PARAMETERS_FILE="private-endpoint-and-dns.parameters.json"

echo "🚀 Starting Azure Private DNS Configuration Deployment"
echo "======================================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Deployment Name: $DEPLOYMENT_NAME"
echo "Bicep File: $BICEP_FILE"
echo "Parameters File: $PARAMETERS_FILE"
echo ""

# Check if Azure CLI is logged in
echo "🔍 Checking Azure CLI authentication..."
if ! az account show > /dev/null 2>&1; then
    echo "❌ Error: Not logged into Azure CLI. Please run 'az login' first."
    exit 1
fi

# Get current subscription info
CURRENT_SUBSCRIPTION=$(az account show --query "name" -o tsv)
CURRENT_SUBSCRIPTION_ID=$(az account show --query "id" -o tsv)
echo "✅ Logged into Azure CLI"
echo "📋 Current Subscription: $CURRENT_SUBSCRIPTION ($CURRENT_SUBSCRIPTION_ID)"
echo ""

# Verify resource group exists
echo "🔍 Verifying resource group exists..."
if ! az group show --name "$RESOURCE_GROUP" > /dev/null 2>&1; then
    echo "❌ Error: Resource group '$RESOURCE_GROUP' not found."
    echo "Please create the resource group first or update the RESOURCE_GROUP variable."
    exit 1
fi
echo "✅ Resource group '$RESOURCE_GROUP' found"
echo ""

# Verify Bicep file exists
if [[ ! -f "$BICEP_FILE" ]]; then
    echo "❌ Error: Bicep file '$BICEP_FILE' not found."
    echo "Please ensure the file exists in the current directory."
    exit 1
fi

# Verify parameters file exists
if [[ ! -f "$PARAMETERS_FILE" ]]; then
    echo "❌ Error: Parameters file '$PARAMETERS_FILE' not found."
    echo "Please ensure the file exists in the current directory."
    exit 1
fi

echo "✅ Bicep and parameters files found"
echo ""

# Validate the Bicep template
echo "🔍 Validating Bicep template..."
if ! az deployment group validate \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$BICEP_FILE" \
    --parameters "@$PARAMETERS_FILE" > /dev/null 2>&1; then
    echo "❌ Error: Bicep template validation failed."
    echo "Running validation with detailed output:"
    az deployment group validate \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$BICEP_FILE" \
        --parameters "@$PARAMETERS_FILE"
    exit 1
fi
echo "✅ Bicep template validation successful"
echo ""

# Deploy the template
echo "🚀 Deploying Bicep template..."
echo "This will create:"
echo "  ✓ Private DNS zones for AI services, search, storage, and Cosmos DB"
echo "  ✓ VNet links for DNS zones"
echo "  ✓ DNS zone groups for existing private endpoints"
echo "  ✓ Skip creating new private endpoints (using existing ones)"
echo ""

read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled by user."
    exit 0
fi

echo "🚀 Starting deployment..."
if az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOYMENT_NAME" \
    --template-file "$BICEP_FILE" \
    --parameters "@$PARAMETERS_FILE" \
    --verbose; then
    echo ""
    echo "✅ Deployment completed successfully!"
    echo "======================================="
    echo ""
    echo "📋 Deployment Summary:"
    echo "  • Resource Group: $RESOURCE_GROUP"
    echo "  • Deployment Name: $DEPLOYMENT_NAME"
    echo "  • Status: Succeeded"
    echo ""
    echo "🔗 View deployment in Azure Portal:"
    echo "https://portal.azure.com/#@/resource/subscriptions/$CURRENT_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/deployments"
    echo ""
    echo "🎉 Your private DNS configuration is now ready!"
    echo "   Private endpoints can now resolve correctly within your VNet."
else
    echo ""
    echo "❌ Deployment failed!"
    echo "==================="
    echo ""
    echo "Please check the error messages above and:"
    echo "1. Verify all resource names in the parameters file are correct"
    echo "2. Ensure all existing private endpoints exist in the resource group"
    echo "3. Check that you have sufficient permissions"
    echo ""
    echo "For detailed logs, check the deployment in Azure Portal:"
    echo "https://portal.azure.com/#@/resource/subscriptions/$CURRENT_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/deployments"
    exit 1
fi
