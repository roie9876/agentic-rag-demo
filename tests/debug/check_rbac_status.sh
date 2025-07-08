#!/bin/bash
echo "🔍 Checking RBAC Role Assignments for Private Endpoint Resources"
echo "================================================================"

# Get current user information
echo "📋 Current User Information:"
CURRENT_USER_INFO=$(az account show --query "{name: name, user: user.name, type: user.type}" -o json)
echo "$CURRENT_USER_INFO" | jq .

# Get current user object ID
USER_OBJECT_ID=$(az account show --query user.name -o tsv)
echo "User Object ID: $USER_OBJECT_ID"

echo -e "\n🔍 Checking Role Assignments..."

# Check OpenAI resource
echo -e "\n--- Azure OpenAI (private-openai-agentic) ---"
OPENAI_RESOURCE_ID="/subscriptions/7aa77d2e-cbec-48b4-8518-9802543b25af/resourceGroups/private-rg/providers/Microsoft.CognitiveServices/accounts/private-openai-agentic"
az role assignment list --scope "$OPENAI_RESOURCE_ID" --query "[].{principalName: principalName, roleDefinitionName: roleDefinitionName, principalType: principalType}" -o table

# Check Document Intelligence resource  
echo -e "\n--- Document Intelligence (private-doc-int) ---"
DOC_INTEL_RESOURCE_ID="/subscriptions/7aa77d2e-cbec-48b4-8518-9802543b25af/resourceGroups/private-rg/providers/Microsoft.CognitiveServices/accounts/private-doc-int"
az role assignment list --scope "$DOC_INTEL_RESOURCE_ID" --query "[].{principalName: principalName, roleDefinitionName: roleDefinitionName, principalType: principalType}" -o table

# Check AI Search resource
echo -e "\n--- AI Search (private-ai-search) ---"
SEARCH_RESOURCE_ID="/subscriptions/7aa77d2e-cbec-48b4-8518-9802543b25af/resourceGroups/private-rg/providers/Microsoft.Search/searchServices/private-ai-search"
az role assignment list --scope "$SEARCH_RESOURCE_ID" --query "[].{principalName: principalName, roleDefinitionName: roleDefinitionName, principalType: principalType}" -o table

echo -e "\n🔍 Checking System-Assigned Managed Identity Status..."

# Check managed identity on resources
echo -e "\n--- OpenAI Managed Identity ---"
az cognitiveservices account show --name private-openai-agentic --resource-group private-rg --query "identity" -o json

echo -e "\n--- Document Intelligence Managed Identity ---"
az cognitiveservices account show --name private-doc-int --resource-group private-rg --query "identity" -o json

echo -e "\n--- AI Search Managed Identity ---"
az search service show --name private-ai-search --resource-group private-rg --query "identity" -o json

echo -e "\n💡 Summary:"
echo "1. If you see your user account in the role assignments above, managed identity should work"
echo "2. If some roles are missing, run the setup script again"
echo "3. Remember: Role assignments can take 5-10 minutes to propagate"
echo "4. For AI Search: the 403 error on empty services is sometimes expected"
