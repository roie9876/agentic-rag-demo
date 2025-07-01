#!/bin/bash
"""
Quick Fix: Get API Keys for Private Endpoint Resources
=====================================================
This script retrieves the API keys for your private endpoint resources
as a temporary solution while you set up managed identity RBAC.
"""

set -e

echo "🔑 Retrieving API Keys for Private Endpoint Resources"
echo "====================================================="

# Resource details from your diagnostics
RESOURCE_GROUP="private-rg"
OPENAI_RESOURCE="private-openai-agentic"
DOC_INTEL_RESOURCE="private-doc-int"
SEARCH_RESOURCE="private-ai-search"

echo "📋 Resources:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   OpenAI: $OPENAI_RESOURCE"
echo "   Document Intelligence: $DOC_INTEL_RESOURCE"
echo "   AI Search: $SEARCH_RESOURCE"
echo ""

# Create a temporary .env additions file
ENV_ADDITION_FILE="/tmp/private_endpoint_keys.env"
echo "# Private Endpoint API Keys - Add these to your .env file" > $ENV_ADDITION_FILE
echo "# Generated on $(date)" >> $ENV_ADDITION_FILE
echo "" >> $ENV_ADDITION_FILE

# Get OpenAI API key
echo "🧠 Getting OpenAI API key..."
OPENAI_KEY=$(az cognitiveservices account keys list --name $OPENAI_RESOURCE --resource-group $RESOURCE_GROUP --query key1 -o tsv)
if [ ! -z "$OPENAI_KEY" ]; then
    echo "✅ OpenAI key retrieved"
    echo "AZURE_OPENAI_KEY_41=$OPENAI_KEY" >> $ENV_ADDITION_FILE
else
    echo "❌ Failed to get OpenAI key"
fi

# Get Document Intelligence API key
echo "📄 Getting Document Intelligence API key..."
DOC_INTEL_KEY=$(az cognitiveservices account keys list --name $DOC_INTEL_RESOURCE --resource-group $RESOURCE_GROUP --query key1 -o tsv)
if [ ! -z "$DOC_INTEL_KEY" ]; then
    echo "✅ Document Intelligence key retrieved"
    echo "DOCUMENT_INTEL_KEY=$DOC_INTEL_KEY" >> $ENV_ADDITION_FILE
else
    echo "❌ Failed to get Document Intelligence key"
fi

# Get AI Search API key
echo "🔍 Getting AI Search API key..."
SEARCH_KEY=$(az search admin-key show --service-name $SEARCH_RESOURCE --resource-group $RESOURCE_GROUP --query primaryKey -o tsv)
if [ ! -z "$SEARCH_KEY" ]; then
    echo "✅ AI Search key retrieved"
    echo "AZURE_SEARCH_KEY=$SEARCH_KEY" >> $ENV_ADDITION_FILE
else
    echo "❌ Failed to get AI Search key"
fi

echo ""
echo "🎯 API keys retrieved and saved to: $ENV_ADDITION_FILE"
echo ""
echo "📋 Add these lines to your .env file:"
echo "================================================"
cat $ENV_ADDITION_FILE
echo "================================================"
echo ""
echo "🔄 Next steps:"
echo "   1. Copy the above lines to your .env file"
echo "   2. Test the connection with: python3 diagnose_private_endpoints.py"
echo "   3. Once working, set up managed identity with: ./setup_rbac_permissions.sh"
echo "   4. Remove API keys from .env file for better security"
echo ""
echo "⚠️  Security Note: API keys are sensitive. Use managed identity for production."
