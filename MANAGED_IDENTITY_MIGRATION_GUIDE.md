# Managed Identity Migration Guide

## Overview

This guide documents the changes made to migrate your Agentic RAG Demo application from API key authentication to Azure Managed Identity authentication. This improves security by eliminating the need to manage API keys and follows Azure security best practices.

## Changes Made

### 1. Environment Variables (.env)
- Removed or commented out API keys:
  - `AZURE_OPENAI_KEY` and `AZURE_OPENAI_KEY_41`
  - `DOCUMENT_INTEL_KEY`, `AZURE_FORMREC_KEY`
  - `AZURE_SEARCH_KEY` (was already commented)

### 2. Core Application Files

#### agentic-rag-demo.py
- Updated `env()` function to allow optional parameters
- Modified `init_openai()` to use managed identity when API keys are not available
- Updated `create_agentic_rag_index()` to not require API keys for vectorizer and knowledge agent

#### sharepoint_index_manager.py
- Updated OpenAI client creation to fallback to managed identity when API key is not available

#### direct_api_retrieval.py
- Updated OpenAI client creation to support managed identity authentication

#### function/agent.py
- Enhanced Azure Function to support both API key and managed identity authentication
- Added proper fallback logic for OpenAI client creation

#### tools/document_intelligence_client.py
- **Note**: This file needs manual update due to edit conflicts
- Should support both API key and managed identity authentication

## Azure Resource Requirements

For managed identity to work, you need to configure the following Azure resources:

### 1. Azure App Service / Function App
- Enable System-assigned Managed Identity
- Grant appropriate RBAC roles

### 2. Azure OpenAI Service
Required RBAC roles for the managed identity:
- `Cognitive Services OpenAI User` (for inference)
- `Cognitive Services OpenAI Contributor` (if creating models/deployments)

### 3. Azure AI Search
Required RBAC roles for the managed identity:
- `Search Index Data Reader` (for reading data)
- `Search Service Contributor` (for managing indexes)
- `Search Index Data Contributor` (for writing data)

### 4. Azure Document Intelligence
Required RBAC roles for the managed identity:
- `Cognitive Services User` (for document analysis)

## Deployment Steps

### Step 1: Update Azure Resources

1. **Enable Managed Identity on your hosting service**:
   ```bash
   # For App Service
   az webapp identity assign --name <app-name> --resource-group <rg-name>
   
   # For Function App
   az functionapp identity assign --name <function-name> --resource-group <rg-name>
   ```

2. **Grant RBAC permissions for Azure OpenAI**:
   ```bash
   az role assignment create \
     --role "Cognitive Services OpenAI User" \
     --assignee <managed-identity-principal-id> \
     --scope /subscriptions/<subscription-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<openai-account>
   ```

3. **Grant RBAC permissions for Azure AI Search**:
   ```bash
   az role assignment create \
     --role "Search Index Data Reader" \
     --assignee <managed-identity-principal-id> \
     --scope /subscriptions/<subscription-id>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search-service>
   
   az role assignment create \
     --role "Search Service Contributor" \
     --assignee <managed-identity-principal-id> \
     --scope /subscriptions/<subscription-id>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search-service>
   ```

4. **Grant RBAC permissions for Document Intelligence**:
   ```bash
   az role assignment create \
     --role "Cognitive Services User" \
     --assignee <managed-identity-principal-id> \
     --scope /subscriptions/<subscription-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<doc-intel-account>
   ```

### Step 2: Update Application Configuration

1. Update your `.env` file (already done) to remove API keys
2. Deploy the updated code to your Azure service
3. Restart the application to pick up the new configuration

### Step 3: Verify Functionality

1. Run the health check in your application to verify all services are accessible
2. Test document upload and processing
3. Test SharePoint integration
4. Verify Azure Function operations

## Manual Fix Required

The `tools/document_intelligence_client.py` file needs to be manually updated. Replace the content with:

```python
import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

class DocumentIntelligenceClientWrapper:
    """
    Tiny wrapper that resolves endpoint / key from multiple env-var aliases
    so existing code can work with either the new DOCUMENT_INTEL_* names
    or the older AZURE_FORMREC_* / AZURE_FORMRECOGNIZER_* names.
    Now supports both API key and Managed Identity authentication.
    """
    def __init__(self) -> None:
        ep = (
            os.getenv("DOCUMENT_INTEL_ENDPOINT") or
            os.getenv("AZURE_FORMREC_SERVICE") or
            os.getenv("AZURE_FORMRECOGNIZER_ENDPOINT") or
            ""
        ).rstrip("/")

        key = (
            os.getenv("DOCUMENT_INTEL_KEY") or
            os.getenv("AZURE_FORMREC_KEY") or
            os.getenv("AZURE_FORMRECOGNIZER_KEY") or
            ""
        )

        if not ep:
            # Let callers detect "DI not configured"
            self.client = None
            self.docint_40_api = False
            return

        # Create client with appropriate authentication
        if key:
            # Use API key authentication
            self.client = DocumentIntelligenceClient(ep, AzureKeyCredential(key))
        else:
            # Use Managed Identity authentication
            self.client = DocumentIntelligenceClient(ep, DefaultAzureCredential())

        # ... rest of the existing code for API version detection
```

## Benefits of This Migration

1. **Enhanced Security**: No API keys stored in environment variables or code
2. **Simplified Key Management**: No need to rotate or manage API keys
3. **Azure Best Practices**: Follows Microsoft's recommended authentication patterns
4. **Audit Trail**: Better auditing and monitoring capabilities through Azure RBAC
5. **Least Privilege**: Can grant minimal required permissions per resource

## Troubleshooting

### Common Issues

1. **"Authentication failed" errors**: Verify managed identity has proper RBAC roles
2. **"Resource not found" errors**: Check managed identity principal ID and scope
3. **Permission denied**: Ensure correct role assignments and scope

### Useful Commands

```bash
# Get managed identity principal ID
az webapp identity show --name <app-name> --resource-group <rg-name> --query principalId -o tsv

# List role assignments for managed identity
az role assignment list --assignee <principal-id> --all
```

## Rollback Plan

If issues occur, you can temporarily rollback by:
1. Re-adding API keys to environment variables
2. The code maintains backward compatibility and will use API keys if available
3. Redeploy with the original `.env` configuration

## Next Steps

1. Monitor application logs for any authentication issues
2. Set up Azure Monitor alerts for authentication failures
3. Consider implementing the same pattern for other Azure services in your application
4. Document the managed identity approach for your team
