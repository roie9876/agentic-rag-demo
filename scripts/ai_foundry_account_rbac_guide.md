# RBAC Permissions for AI Foundry Account Access

## 🎯 AI Foundry Account vs Hub

Your setup uses an **AI Foundry Account** (not a hub), which has different permission requirements and API structures.

### AI Foundry Account Structure:
- **Account**: `aiagenticservicesfgtt` (your foundry account)
- **Project**: `agentic-rag` (project within the account)
- **Endpoint**: `https://aiagenticservicesfgtt.services.ai.azure.com/api/projects/agentic-rag`

## 🔑 Required RBAC Permissions for AI Foundry Account

### 1. **Azure AI Developer Role** (Recommended)
- **Role**: `Azure AI Developer`
- **Scope**: At the AI Foundry account level
- **Permissions**: 
  - Read/write access to AI projects
  - Create and manage agents
  - Access to models and deployments
  - Manage project resources

### 2. **Alternative: Cognitive Services Contributor**
- **Role**: `Cognitive Services Contributor`
- **Scope**: At the resource group or subscription level
- **Permissions**:
  - Full access to AI services
  - Create and manage resources

### 3. **Minimum Required Permissions (Custom Role)**
If you need to create a custom role, include these permissions:

```json
{
  "permissions": [
    {
      "actions": [
        "Microsoft.CognitiveServices/accounts/read",
        "Microsoft.CognitiveServices/accounts/write",
        "Microsoft.CognitiveServices/accounts/*/read",
        "Microsoft.CognitiveServices/accounts/*/write",
        "Microsoft.MachineLearningServices/workspaces/read",
        "Microsoft.MachineLearningServices/workspaces/write",
        "Microsoft.MachineLearningServices/workspaces/*/read",
        "Microsoft.MachineLearningServices/workspaces/*/write"
      ],
      "notActions": [],
      "dataActions": [
        "Microsoft.CognitiveServices/accounts/*/action",
        "Microsoft.CognitiveServices/accounts/*/read",
        "Microsoft.CognitiveServices/accounts/*/write"
      ],
      "notDataActions": []
    }
  ]
}
```

## 🔧 How to Assign Permissions

### Option 1: Using Azure Portal
1. Go to Azure Portal → AI Foundry Account resource
2. Click **Access control (IAM)**
3. Click **+ Add** → **Add role assignment**
4. Select **Azure AI Developer** role
5. Assign to your user or managed identity

### Option 2: Using Azure CLI
```bash
# Get your user principal ID
USER_ID=$(az ad signed-in-user show --query id -o tsv)

# Get the AI Foundry account resource ID
FOUNDRY_RESOURCE_ID="/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RG/providers/Microsoft.CognitiveServices/accounts/aiagenticservicesfgtt"

# Assign Azure AI Developer role
az role assignment create \
  --assignee $USER_ID \
  --role "Azure AI Developer" \
  --scope $FOUNDRY_RESOURCE_ID
```

### Option 3: Using PowerShell
```powershell
# Get your user object ID
$userId = (Get-AzADUser -UserPrincipalName "your-email@domain.com").Id

# Assign the role
New-AzRoleAssignment `
  -ObjectId $userId `
  -RoleDefinitionName "Azure AI Developer" `
  -Scope "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RG/providers/Microsoft.CognitiveServices/accounts/aiagenticservicesfgtt"
```

## 🔍 For Managed Identity (if using Azure resources)

If your script runs on an Azure VM or App Service, you'll need to assign permissions to the managed identity:

```bash
# Get the managed identity principal ID
MANAGED_IDENTITY_ID=$(az vm identity show --name YOUR_VM_NAME --resource-group YOUR_RG --query principalId -o tsv)

# Assign the role to managed identity
az role assignment create \
  --assignee $MANAGED_IDENTITY_ID \
  --role "Azure AI Developer" \
  --scope $FOUNDRY_RESOURCE_ID
```

## 🎯 Token Scope for AI Foundry Accounts

The script should use this token scope for AI Foundry accounts:
- **Scope**: `https://cognitiveservices.azure.com/.default`
- **Alternative**: `https://ml.azure.com/.default` (for some AI services)

## 🚨 Common Issues and Solutions

### Issue 1: 403 Forbidden
- **Cause**: Insufficient permissions
- **Solution**: Ensure you have `Azure AI Developer` role at the account level

### Issue 2: 404 Not Found  
- **Cause**: Incorrect project name or endpoint
- **Solution**: Verify the project exists in the AI Foundry account

### Issue 3: Token Issues
- **Cause**: Wrong token scope
- **Solution**: Use `https://cognitiveservices.azure.com/.default`

### Issue 4: Private Endpoint Access
- **Cause**: Network restrictions
- **Solution**: Ensure your client has access to the private endpoint network

## 📋 Quick Permission Check Commands

```bash
# Check your current role assignments
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --all

# Check if you can access the AI Foundry account
az cognitiveservices account show --name aiagenticservicesfgtt --resource-group YOUR_RG

# Test token acquisition
az account get-access-token --scope https://cognitiveservices.azure.com/.default
```

## 🔗 Related Documentation
- [Azure AI Developer role](https://docs.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#azure-ai-developer)
- [AI Foundry authentication](https://docs.microsoft.com/en-us/azure/ai-services/authentication)
- [Managed Identity setup](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
