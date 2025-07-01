# Blob Storage Managed Identity Setup

## Problem
Your storage accounts are configured for private endpoints and require managed identity authentication:
```
Key based authentication is not permitted on this storage account
```

## Solution

### 1. Grant Storage Access to Your Application

Find your application's managed identity principal ID:
```bash
# For VM-based deployment
az vm identity show --name <your-vm-name> --resource-group <your-rg> --query principalId -o tsv

# For App Service deployment  
az webapp identity show --name <your-app-name> --resource-group <your-rg> --query principalId -o tsv

# For Container Apps deployment
az containerapp identity show --name <your-app-name> --resource-group <your-rg> --query principalId -o tsv
```

### 2. Assign Storage Roles

Grant the required permissions to your storage accounts:

```bash
# Set variables
PRINCIPAL_ID="<your-managed-identity-principal-id>"
SUBSCRIPTION_ID="<your-subscription-id>"

# For privateblogagenticimages storage account
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<rg-name>/providers/Microsoft.Storage/storageAccounts/privateblogagenticimages"

# For ragimagedescription storage account (if you use the multimodal features)
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<rg-name>/providers/Microsoft.Storage/storageAccounts/ragimagedescription"
```

### 3. Update Configuration

Remove the connection strings and use managed identity:

```properties
# Remove or comment out connection strings
# AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=...

# Use managed identity configuration instead
AZURE_STORAGE_ACCOUNT_NAME=privateblogagenticimages
AZURE_STORAGE_ACCOUNT_URL=https://privateblogagenticimages.blob.core.windows.net
AZURE_STORAGE_CONTAINER=images
```

### 4. Restart Application

After making these changes, restart your application to pick up the new configuration.

## Benefits

- Enhanced security (no API keys)
- Better compliance with security policies
- Centralized access management through Azure RBAC

## Note

The multimodal/image storage features are **optional**. Your main document processing functionality should work fine without them.
