# AI Foundry Integration Documentation

## Overview

This application provides integration with **AI Foundry Hubs only**. AI Foundry Accounts are **not supported** due to limitations in Microsoft's public APIs.

## Supported vs. Not Supported

### ✅ **Supported: AI Foundry Hubs**
- **Resource Type**: `Microsoft.MachineLearningServices/workspaces` with `kind=Hub`
- **Full Support**: Discovery, project management, RBAC checking, agent deployment
- **APIs Available**: Azure ML Management API, Azure Resource Manager API
- **Project Operations**: List, create, delete projects programmatically

### ❌ **Not Supported: AI Foundry Accounts**
- **Resource Type**: `Microsoft.CognitiveServices/accounts` with `kind=AIServices`
- **Limited Support**: Discovery only, no project management
- **API Limitations**: No public REST API for project management
- **Manual Workaround**: Use Azure Portal for project operations

## Why AI Foundry Accounts Are Not Supported

After comprehensive testing and debugging (see `AI_FOUNDRY_FINAL_IMPLEMENTATION_SUMMARY.md`), we determined that:

1. **No Public Project API**: Microsoft has not exposed public REST APIs for project management on AI Foundry Accounts
2. **404 Responses**: All tested endpoints return 404 for project operations
3. **Portal-Only Operations**: Project management is only available through the Azure Portal
4. **Regional Limitations**: Some AI Foundry Account types may have regional restrictions

## Debugging Evidence

The following endpoints were tested and **all returned 404**:
- `https://{account}.services.ai.azure.com/api/projects`
- `https://{account}.services.ai.azure.com/projects`
- `https://{account}.cognitiveservices.azure.com/api/projects`
- Multiple API versions: 2025-05-15-preview, 2024-07-01-preview, etc.

## Migration Path

### For Users with AI Foundry Accounts:

1. **Option 1: Use Azure Portal**
   - Create and manage projects manually in Azure AI Foundry Portal
   - Limited to manual operations

2. **Option 2: Migrate to AI Foundry Hubs** (Recommended)
   - Create an AI Foundry Hub (ML workspace with kind=Hub)
   - Gain full programmatic project management capabilities
   - Use this application's full feature set

### Creating an AI Foundry Hub:

```bash
# Using Azure CLI
az ml workspace create \
  --name "my-ai-foundry-hub" \
  --resource-group "my-rg" \
  --location "eastus" \
  --kind "Hub"
```

Or use the Azure Portal:
1. Navigate to Azure Machine Learning
2. Create new workspace
3. Set **Kind** to "Hub"
4. Configure as needed

## Application Architecture Changes

### Service Layer (`services/ai_foundry_service.py`):
- **Removed**: AI Foundry Account project management methods
- **Updated**: Discovery methods to focus on Hubs only
- **Simplified**: Data models to use `AIFoundryHub` instead of generic `AIFoundryResource`

### UI Layer (`app/tabs/enhanced_ai_foundry_tab.py`):
- **Updated**: Tab name to "AI Foundry Hub Management"
- **Added**: Clear notices about Hub-only support
- **Simplified**: Discovery UI to show Hubs only
- **Improved**: Error messages for users with Accounts

### Data Models:
- **New**: `AIFoundryHub` dataclass for Hub-specific properties
- **Removed**: Generic `AIFoundryResource` with resource_type discrimination
- **Updated**: `AIFoundryProject` to reference parent Hub instead of generic resource

## API Endpoints Used

### For AI Foundry Hubs (Working):
- **Discovery**: `https://management.azure.com/subscriptions/{sub}/providers/Microsoft.MachineLearningServices/workspaces`
- **Projects**: `https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.MachineLearningServices/workspaces`
- **Project Creation**: `PUT` to above endpoint with Hub reference

### For AI Foundry Accounts (Not Working):
- **Projects API**: All project-related endpoints return 404
- **Discovery**: Account discovery works via Azure Resource Manager
- **Limitation**: No programmatic project management available

## Code Examples

### Hub Discovery:
```python
from services.ai_foundry_service import AIFoundryService

service = AIFoundryService()
hubs, errors = service.discover_ai_foundry_hubs()

for hub in hubs:
    print(f"Hub: {hub.name} in {hub.location}")
```

### Project Management:
```python
# List projects for a hub
projects, errors = service.get_projects_for_hub(hub)

# Create a new project
success, message, project = service.create_project(
    hub, "my-project", "Project description"
)
```

## Future Considerations

1. **Monitor Microsoft Updates**: Watch for new AI Foundry Account APIs
2. **Hub Migration Tools**: Consider building tools to help users migrate from Accounts to Hubs
3. **Hybrid Support**: If Account APIs become available, add them back with feature flags

## Error Handling

The application now provides clear error messages for users with AI Foundry Accounts:

- **Discovery**: Shows accounts but explains limitations
- **Project Operations**: Directs users to Azure Portal or Hub migration
- **Documentation**: Links to this documentation for guidance

## Testing

Comprehensive testing was performed with:
- **9 AI Foundry Accounts**: All confirmed to lack project management APIs
- **2 AI Foundry Hubs**: All project operations working correctly
- **Multiple API versions**: None supported for Account project management
- **Different authentication scopes**: All tested and documented

## Conclusion

This architecture provides:
- ✅ **Full support** for AI Foundry Hubs with complete project lifecycle management
- ✅ **Clear communication** to users about limitations
- ✅ **Migration guidance** for users wanting full programmatic access
- ✅ **Future-ready** structure for when Account APIs become available

The decision to focus on Hubs only ensures a reliable, well-tested experience rather than partially working functionality.
