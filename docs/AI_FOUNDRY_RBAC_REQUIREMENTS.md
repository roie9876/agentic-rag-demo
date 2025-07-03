# AI Foundry RBAC Requirements

## Overview
This document outlines the required Role-Based Access Control (RBAC) permissions needed to run the `check_ai_foundry_project.py` script and interact with Azure AI Foundry projects.

## Required Azure RBAC Roles

### 1. Azure AI Developer (Recommended)
**Role Name**: `Azure AI Developer`
**Scope**: AI Foundry Hub resource or Resource Group
**Description**: This is the primary role for working with Azure AI Foundry projects.

```bash
# Assign Azure AI Developer role
az role assignment create \
  --assignee <user-principal-id-or-email> \
  --role "Azure AI Developer" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.MachineLearningServices/workspaces/<foundry-hub-name>"
```

### 2. Alternative: Cognitive Services User
**Role Name**: `Cognitive Services User`
**Scope**: AI Foundry Hub resource
**Description**: Minimum permissions for API access

```bash
# Assign Cognitive Services User role
az role assignment create \
  --assignee <user-principal-id-or-email> \
  --role "Cognitive Services User" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.MachineLearningServices/workspaces/<foundry-hub-name>"
```

### 3. For Full Management: Azure AI Administrator
**Role Name**: `Azure AI Administrator`
**Scope**: Resource Group or Subscription
**Description**: Full management permissions (use sparingly)

```bash
# Assign Azure AI Administrator role (careful - high privileges)
az role assignment create \
  --assignee <user-principal-id-or-email> \
  --role "Azure AI Administrator" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>"
```

## Resource-Specific Permissions

### AI Foundry Hub Permissions
The user needs access to the **AI Foundry Hub** resource (not just the project). The hub is the parent resource that contains multiple projects.

#### Finding Your Hub Resource
```bash
# List AI Foundry hubs in your subscription
az ml workspace list --resource-group <resource-group-name>

# Get specific hub details
az ml workspace show --name <hub-name> --resource-group <resource-group-name>
```

### Project-Level Permissions
Projects inherit permissions from the hub, but you can also assign project-specific roles:

```bash
# Assign role at project level (if supported)
az role assignment create \
  --assignee <user-principal-id-or-email> \
  --role "Azure AI Developer" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.MachineLearningServices/workspaces/<hub-name>/projects/<project-name>"
```

## Custom Role Definition (Optional)

If you need fine-grained permissions, create a custom role:

```json
{
  "Name": "AI Foundry Project Reader",
  "IsCustom": true,
  "Description": "Can read AI Foundry projects and agents",
  "Actions": [
    "Microsoft.MachineLearningServices/workspaces/read",
    "Microsoft.MachineLearningServices/workspaces/projects/read",
    "Microsoft.MachineLearningServices/workspaces/projects/*/read",
    "Microsoft.CognitiveServices/accounts/read"
  ],
  "NotActions": [],
  "DataActions": [
    "Microsoft.CognitiveServices/accounts/*/read"
  ],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/<subscription-id>"
  ]
}
```

## Troubleshooting Permission Issues

### Common Error Messages and Solutions

#### Error: "403 Forbidden"
**Solution**: User lacks basic read permissions
```bash
# Grant minimum required role
az role assignment create \
  --assignee <user-email> \
  --role "Azure AI Developer" \
  --scope "<foundry-hub-resource-id>"
```

#### Error: "404 Not Found" for existing project
**Solution**: User can't see the hub or project
```bash
# Check current role assignments
az role assignment list --assignee <user-email> --scope "<hub-resource-id>"

# Grant hub-level access
az role assignment create \
  --assignee <user-email> \
  --role "Cognitive Services User" \
  --scope "<hub-resource-id>"
```

#### Error: "Invalid token" or "Authentication failed"
**Solution**: Token scope issue
- Ensure the token is requested for scope: `https://ml.azure.com/.default`
- Check that the user has Azure AD authentication

### Finding Resource IDs

```bash
# Get subscription ID
az account show --query id -o tsv

# Get resource group
az group list --query "[?contains(name, 'agentic')].{Name:name, Id:id}" -o table

# Get AI Foundry hub resource ID
az ml workspace list --query "[].{Name:name, Id:id, ResourceGroup:resourceGroup}" -o table

# Get full resource ID for a hub
az ml workspace show \
  --name <hub-name> \
  --resource-group <resource-group> \
  --query id -o tsv
```

## Managed Identity Considerations

If running on Azure VM or App Service with Managed Identity:

### System-Assigned Managed Identity
```bash
# Get the VM's managed identity principal ID
VM_PRINCIPAL_ID=$(az vm identity show --resource-group <rg> --name <vm-name> --query principalId -o tsv)

# Assign role to the managed identity
az role assignment create \
  --assignee $VM_PRINCIPAL_ID \
  --role "Azure AI Developer" \
  --scope "<foundry-hub-resource-id>"
```

### User-Assigned Managed Identity
```bash
# Get the user-assigned identity principal ID
IDENTITY_PRINCIPAL_ID=$(az identity show --resource-group <rg> --name <identity-name> --query principalId -o tsv)

# Assign role
az role assignment create \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --role "Azure AI Developer" \
  --scope "<foundry-hub-resource-id>"
```

## Verification Script

Use this script to verify permissions:

```bash
#!/bin/bash
# verify_ai_foundry_permissions.sh

SUBSCRIPTION_ID="<your-subscription-id>"
RESOURCE_GROUP="<your-resource-group>"
HUB_NAME="<your-foundry-hub-name>"
USER_EMAIL="<user-email-or-principal-id>"

echo "🔍 Checking AI Foundry permissions for: $USER_EMAIL"
echo "📍 Hub: $HUB_NAME in Resource Group: $RESOURCE_GROUP"
echo

# Get hub resource ID
HUB_RESOURCE_ID="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.MachineLearningServices/workspaces/$HUB_NAME"

echo "🔸 Hub Resource ID: $HUB_RESOURCE_ID"
echo

# Check role assignments
echo "🔸 Current role assignments:"
az role assignment list \
  --assignee "$USER_EMAIL" \
  --scope "$HUB_RESOURCE_ID" \
  --query "[].{Role:roleDefinitionName, Scope:scope}" \
  -o table

echo
echo "🔸 Resource Group level assignments:"
az role assignment list \
  --assignee "$USER_EMAIL" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
  --query "[].{Role:roleDefinitionName, Scope:scope}" \
  -o table
```

## Best Practices

1. **Principle of Least Privilege**: Start with `Cognitive Services User` and escalate only if needed
2. **Resource Scope**: Assign roles at the most specific scope (project > hub > resource group > subscription)
3. **Regular Audits**: Review and remove unnecessary permissions periodically
4. **Use Built-in Roles**: Prefer Azure built-in roles over custom roles when possible
5. **Documentation**: Document who has what access and why

## Quick Setup for Your Environment

Based on your configuration, here's what you likely need:

```bash
# Replace these with your actual values
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
RESOURCE_GROUP="<your-resource-group>"  # Usually contains 'agentic' or similar
USER_EMAIL="<your-email-or-principal-id>"

# Find your AI Foundry hub
az ml workspace list --resource-group $RESOURCE_GROUP

# Get the hub name from the output above
HUB_NAME="<your-foundry-hub-name>"  # e.g., "aiagenticservicesfgtt"

# Assign the required role
az role assignment create \
  --assignee "$USER_EMAIL" \
  --role "Azure AI Developer" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.MachineLearningServices/workspaces/$HUB_NAME"
```

## Additional Resources

- [Azure AI Studio RBAC documentation](https://docs.microsoft.com/en-us/azure/ai-studio/concepts/rbac-ai-studio)
- [Azure built-in roles for AI services](https://docs.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#ai--machine-learning)
- [Troubleshooting Azure AI authentication](https://docs.microsoft.com/en-us/azure/ai-studio/how-to/troubleshoot-authentication)
