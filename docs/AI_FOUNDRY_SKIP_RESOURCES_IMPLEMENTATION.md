# AI Foundry Hub Deployment - Skip Resource Feature Implementation

## Summary of Changes

This implementation adds the ability for users to completely skip the deployment of AI Search, Storage Account, and Cosmos DB resources when deploying an AI Foundry Hub. When skipped, no Azure resources are deployed for these services.

## Changes Made

### 1. Bicep Template Updates (`main.bicep`)

**New Parameters Added:**
```bicep
@description('Skip AI Search deployment entirely. When true, no AI Search will be created or used.')
param skipAiSearchDeployment bool = false

@description('Skip Storage Account deployment entirely. When true, no Storage Account will be created or used.')
param skipStorageAccountDeployment bool = false
```

**Logic Updates:**
- Updated resource existence checks to include skip flags
- Made all resource references conditional based on skip flags
- Made role assignments conditional
- Made capability host connections conditional

### 2. Dependent Resources Module (`standard-dependent-resources.bicep`)

**New Parameters Added:**
```bicep
@description('Skip AI Search deployment entirely. When true, no AI Search will be created.')
param skipAiSearchDeployment bool = false

@description('Skip Storage Account deployment entirely. When true, no Storage Account will be created.')
param skipStorageAccountDeployment bool = false
```

**Resource Creation Updates:**
- AI Search creation: `resource aiSearch = if(!aiSearchExists && !skipAiSearchDeployment)`
- Storage Account creation: `resource storage = if(!azureStorageExists && !skipStorageAccountDeployment)`

**Output Updates:**
- All outputs now return empty string when resource is skipped
- Example: `output aiSearchName string = skipAiSearchDeployment ? '' : (aiSearchExists ? existingSearchService.name : aiSearch.name)`

### 3. Private Endpoint Module (`private-endpoint-and-dns.bicep`)

**New Parameters Added:**
```bicep
@description('Skip AI Search deployment entirely (set to true if no AI Search needed)')
param skipAiSearch bool = false

@description('Skip Storage Account deployment entirely (set to true if no Storage needed)')
param skipStorage bool = false
```

**Resource Updates:**
- Made all resource references conditional: `resource aiSearch = if (!skipAiSearch)`
- Made private endpoint creation conditional
- Made DNS zone group creation conditional

### 4. Service Layer (`ai_foundry_hub_deployment.py`)

**Parameter Generation Updates:**
- Added skip parameter generation for AI Search and Storage Account
- Updated auto-detection logic to respect skip flags
- Example:
```python
# AI Search
if config.ai_search.skip_deployment:
    params["aiSearchResourceId"] = {"value": ""}
    params["skipAiSearchDeployment"] = {"value": True}
```

**Validation Updates:**
- Updated validation to only check resource IDs when not skipped
- Example: `if not config.ai_search.skip_deployment and not config.ai_search.create_new:`

### 5. UI Layer (`ai_foundry_hub_deployment_ui.py`)

**UI Updates:**
- Extended skip deployment option to all resources (AI Search, Storage Account, Cosmos DB)
- Unified resource configuration interface
- Added skip deployment radio button option for all resources

**New UI Flow:**
```python
deployment_option = st.radio(
    f"{title} Deployment",
    ["Create New", "Use Existing", "Skip Deployment"],
    # ...
)
resource.skip_deployment = deployment_option == "Skip Deployment"
```

## Usage

### In the UI:
1. Navigate to AI Foundry Hub → Deploy New Account
2. In the Resource Configuration section, each resource (AI Search, Storage Account, Cosmos DB) now has three options:
   - **Create New**: Deploy a new resource
   - **Use Existing**: Use an existing resource
   - **Skip Deployment**: Skip this resource entirely

### When a resource is skipped:
- No Azure resource is deployed for that service
- No private endpoints are created for that service
- No role assignments are created for that service
- No capability host connections are created for that service
- The deployment will be faster and cheaper

## Benefits

1. **Cost Optimization**: Skip unnecessary resources to reduce costs
2. **Faster Deployment**: Reduced deployment time when resources are skipped
3. **Flexible Architecture**: Deploy only what you need
4. **Later Configuration**: Resources can be added later if needed

## Backward Compatibility

- All existing configurations continue to work
- Default behavior unchanged (resources are created by default)
- Skip flags default to `false` for all resources

## Example Scenarios

1. **Minimal AI Foundry Hub**: Skip all dependent resources for a basic AI Services-only deployment
2. **Custom Storage**: Skip Storage Account to use your own storage solution
3. **External Search**: Skip AI Search to use an external search service
4. **Simple Setup**: Skip Cosmos DB if conversation history is not needed

## Next Steps

The implementation is complete and ready for testing. Users can now:
1. Skip individual resources during deployment
2. Deploy faster, cheaper AI Foundry Hub configurations
3. Add resources later through the Azure portal if needed
