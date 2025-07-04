#!/bin/bash

# Script to help request Azure OpenAI quota increase
# This script provides the information needed to submit a quota increase request

echo "🚀 Azure OpenAI Quota Increase Request Helper"
echo "============================================="

# Get current subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

echo ""
echo "📋 Current Subscription Information:"
echo "   Subscription ID: $SUBSCRIPTION_ID"
echo "   Subscription Name: $SUBSCRIPTION_NAME"
echo ""

# Check current OpenAI services
echo "🔍 Checking existing Azure OpenAI services..."
az cognitiveservices account list --query "[?kind=='OpenAI'].{Name:name,Location:location,ResourceGroup:resourceGroup}" -o table

echo ""
echo "📝 To request a quota increase:"
echo "1. Go to Azure Portal > Support > New Support Request"
echo "2. Select 'Service and subscription limits (quotas)'"
echo "3. Choose 'Cognitive Services' as the quota type"
echo "4. Request the following:"
echo "   - Service: Azure OpenAI"
echo "   - Model: GPT-4o"
echo "   - Current Limit: 450 TPM"
echo "   - Requested Limit: 1000 TPM (or higher)"
echo "   - Region: Your deployment region"
echo "   - Business Justification: AI Foundry Hub deployment and development"
echo ""

echo "⏱️  Processing time is typically 1-3 business days"
echo ""
echo "🔗 Direct link to quota requests:"
echo "https://portal.azure.com/#create/Microsoft.Support"
