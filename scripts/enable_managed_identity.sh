#!/bin/bash
"""
Auto-Configure Managed Identity for Private Endpoint Resources
This script automatically enables managed identity and assigns required RBAC roles.
"""

echo "🚀 Auto-Configuring Managed Identity for Private Endpoint Resources"
echo "=================================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run command and check result
run_command() {
    local cmd="$1"
    local description="$2"
    
    echo -e "\n🔧 ${description}..."
    echo "   Command: $cmd"
    
    if eval "$cmd"; then
        echo -e "   ${GREEN}✅ Success${NC}"
    else
        echo -e "   ${RED}❌ Failed${NC}"
        return 1
    fi
}

echo -e "\n📋 Step 1: Enabling Managed Identity on Resources"
echo "================================================="

# Enable managed identity on OpenAI
run_command \
    "az cognitiveservices account update --name private-openai-agentic --resource-group private-rg --assign-identity" \
    "Enabling managed identity on Azure OpenAI"

# Enable managed identity on Document Intelligence
run_command \
    "az cognitiveservices account update --name private-doc-int --resource-group private-rg --assign-identity" \
    "Enabling managed identity on Document Intelligence"

# Enable managed identity on AI Search
run_command \
    "az search service update --name private-ai-search --resource-group private-rg --identity-type SystemAssigned" \
    "Enabling managed identity on AI Search"

echo -e "\n📋 Step 2: Assigning RBAC Roles"
echo "==============================="

USER_OBJECT_ID="2acfdf14-ad32-4735-85eb-097c89d073b6"

# Assign OpenAI role
run_command \
    "az role assignment create --assignee $USER_OBJECT_ID --role \"Cognitive Services OpenAI User\" --scope /subscriptions/7aa77d2e-cbec-48b4-8518-9802543b25af/resourceGroups/private-rg/providers/Microsoft.CognitiveServices/accounts/private-openai-agentic" \
    "Assigning Cognitive Services OpenAI User role"

# Assign Document Intelligence role
run_command \
    "az role assignment create --assignee $USER_OBJECT_ID --role \"Cognitive Services User\" --scope /subscriptions/7aa77d2e-cbec-48b4-8518-9802543b25af/resourceGroups/private-rg/providers/Microsoft.CognitiveServices/accounts/private-doc-int" \
    "Assigning Cognitive Services User role"

# Assign Search roles
run_command \
    "az role assignment create --assignee $USER_OBJECT_ID --role \"Search Index Data Contributor\" --scope /subscriptions/7aa77d2e-cbec-48b4-8518-9802543b25af/resourceGroups/private-rg/providers/Microsoft.Search/searchServices/private-ai-search" \
    "Assigning Search Index Data Contributor role"

run_command \
    "az role assignment create --assignee $USER_OBJECT_ID --role \"Search Service Contributor\" --scope /subscriptions/7aa77d2e-cbec-48b4-8518-9802543b25af/resourceGroups/private-rg/providers/Microsoft.Search/searchServices/private-ai-search" \
    "Assigning Search Service Contributor role"

echo -e "\n📋 Step 3: Verification"
echo "======================"

echo "⏳ Waiting 30 seconds for role assignments to propagate..."
sleep 30

# Verify configurations
echo -e "\n🔍 Verifying OpenAI managed identity..."
az cognitiveservices account show --name private-openai-agentic --resource-group private-rg --query identity

echo -e "\n🔍 Verifying Document Intelligence managed identity..."  
az cognitiveservices account show --name private-doc-int --resource-group private-rg --query identity

echo -e "\n🔍 Verifying AI Search managed identity..."
az search service show --name private-ai-search --resource-group private-rg --query identity

echo -e "\n🎉 Managed Identity Configuration Complete!"
echo "=========================================="

echo -e "\n📋 Next Steps:"
echo "1. Your .env file should have NO API keys (remove any AZURE_OPENAI_KEY, etc.)"  
echo "2. Test the configuration with: python3 health_check/private_endpoint_health_checker.py"
echo "3. Run your Streamlit app: streamlit run agentic-rag-demo.py"

echo -e "\n⚠️  Important Note:"
echo "It may take a few minutes for all role assignments to fully propagate."
echo "If you still get authentication errors, wait 5-10 minutes and try again."
