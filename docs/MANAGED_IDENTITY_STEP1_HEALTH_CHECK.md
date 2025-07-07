# Managed Identity Migration - Step 1: Health Check

## Overview
Enhanced the Health Check module to support managed identity authentication alongside existing key-based authentication.

## Changes Made

### 1. Updated `health_check/health_checker.py`
- **Document Intelligence Support**: Made API key optional for Document Intelligence service
- **Backward Compatibility**: Maintained support for both key-based and managed identity authentication
- **Error Handling**: Updated error messages to reflect that only endpoint is required

### 2. Enhanced `health_check/health_check_ui.py`
- **Azure CLI Integration**: Added login/logout functionality with user status display
- **Role Configuration**: Added RBAC role assignment capabilities for all services
- **Authentication Status**: Added visual indicators for current authentication methods
- **Service Detection**: Automatic detection of Azure resources for role assignment

## New Features

### Azure CLI Authentication
- Login/logout buttons with status display
- User information and subscription details
- Tenant ID display for multi-tenant scenarios

### Managed Identity Role Configuration
- **Azure AI Search**: Assigns "Search Index Data Contributor" and "Search Service Contributor" roles
- **Azure OpenAI**: Assigns "Cognitive Services OpenAI User" and "Cognitive Services User" roles  
- **Document Intelligence**: Assigns "Cognitive Services User" role
- **Automatic Detection**: Finds resource names from endpoint URLs
- **Error Handling**: Graceful handling of existing role assignments

### Authentication Status Dashboard
- Visual indicators for current authentication method (Key vs Managed Identity)
- Migration tips and guidance
- Per-service authentication status

## Migration Path

### For Existing Key-Based Setups
1. **Current State**: Services use API keys (AZURE_SEARCH_KEY, AZURE_OPENAI_KEY, etc.)
2. **Test Managed Identity**: Keep keys but test managed identity functionality
3. **Configure Roles**: Use the role configuration buttons to assign RBAC permissions
4. **Validate**: Run health checks to ensure managed identity works
5. **Switch**: Remove API key environment variables when ready

### For New Managed Identity Setups
1. **Login**: Use Azure CLI login functionality
2. **Configure Roles**: Assign required RBAC roles using the UI
3. **Set Endpoints**: Only endpoint environment variables needed
4. **Validate**: Run health checks to confirm functionality

## Required Environment Variables

### Minimal (Managed Identity)
```bash
# Required for all scenarios
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com  # or _41/_4o variants
DOCUMENT_INTEL_ENDPOINT=https://your-docint.cognitiveservices.azure.com

# Required for managed identity
AZURE_TENANT_ID=your-tenant-id
```

### With API Keys (Current Setup)
```bash
# All the above plus:
AZURE_SEARCH_KEY=your-search-key
AZURE_OPENAI_KEY=your-openai-key
DOCUMENT_INTEL_KEY=your-docint-key
```

## Testing

### Health Check Validation
1. Navigate to "Login & Health Check" tab
2. Login using Azure CLI if using managed identity
3. Click "Check All Services" 
4. Verify all services show green checkmarks
5. Review authentication status in the role configuration section

### Role Assignment Testing
1. Ensure Azure CLI is logged in
2. Click role configuration buttons for each service
3. Verify roles are assigned successfully
4. Re-run health check to confirm functionality

## Next Steps

This completes Step 1 of the managed identity migration. The health check now supports:
- ✅ Mixed authentication (some services with keys, others with managed identity)
- ✅ Full managed identity authentication
- ✅ Role configuration and management
- ✅ Authentication status monitoring

**Ready for Step 2: Create Index tab migration**
