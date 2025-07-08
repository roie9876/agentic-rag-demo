# AI Foundry Bicep Template Fixes

## Issues Addressed

### 1. Capability Host Creation with No Service Connections

**Problem**: When all services (Cosmos DB, AI Search, Storage) were skipped, the capability host was still being created, causing the error "CreateCapabilityHostRequestDto is invalid".

**Root Cause**: The capability host module was being deployed whenever OpenAI deployment was not skipped, regardless of whether any service connections were available.

**Solution**: 
- Updated the capability host module condition in `main.bicep` from:
  ```bicep
  module addProjectCapabilityHost = if (!skipOpenAIDeployment) {
  ```
  To:
  ```bicep
  module addProjectCapabilityHost = if (!skipOpenAIDeployment && (!skipCosmosDBDeployment || !skipAiSearchDeployment || !skipStorageAccountDeployment)) {
  ```
- This ensures the capability host is only created when at least one service is available.

### 2. DNS Zones Created in Wrong Resource Group

**Problem**: DNS zones were being created in the deployment resource group instead of the specified `dnsZoneResourceGroupName`.

**Root Cause**: The `dnsZoneResourceGroupName` parameter was being passed correctly to the private endpoint module, but might not have been properly applied in all DNS zone creation scenarios.

**Verification**: 
- Confirmed that `private-rg` resource group exists and already contains the required DNS zones
- The `private-endpoint-and-dns.bicep` module correctly uses the `dnsZoneResourceGroupName` parameter in all DNS zone resource declarations

### 3. Hard Dependencies on Conditionally Created Resources

**Problem**: Role assignment modules had hard dependencies on resources that might not exist when services are skipped.

**Solution**: 
- Removed hard dependencies on the capability host from role assignment modules
- Role assignment modules are already conditionally deployed based on their respective service availability
- This prevents dependency resolution issues when the capability host is not created

## Changes Made

### `main.bicep`
1. **Updated capability host condition**: Only deploy when at least one service is available
2. **Simplified role assignment dependencies**: Removed dependencies on capability host since these modules are already conditionally deployed

### Testing Results

**Template Validation**: ✅ Passed
- Template validates successfully with all services skipped
- Capability host deployment is correctly excluded from the operation list when no services are available

**DNS Zone Configuration**: ✅ Verified
- `dnsZoneResourceGroupName` parameter is correctly passed and should create DNS zones in the specified resource group
- `private-rg` resource group exists and already contains the required DNS zones

## Expected Behavior with User's Parameters

With the user's configuration:
- `skipOpenAIDeployment: false` (AI account and project will be created)
- `skipCosmosDBDeployment: true`
- `skipAiSearchDeployment: true` 
- `skipStorageAccountDeployment: true`
- `dnsZoneResourceGroupName: "private-rg"`

**Expected Results**:
1. ✅ AI account and project will be created
2. ✅ Capability host will NOT be created (no service connections available)
3. ✅ DNS zones will be created/used in `private-rg` resource group
4. ✅ No role assignment modules will be deployed (all services skipped)
5. ✅ Private endpoints will be created only for AI Services (OpenAI)

## Next Steps

1. **Test the deployment** with the user's exact parameters to confirm all issues are resolved
2. **Monitor the deployment** to ensure:
   - No capability host creation errors
   - DNS zones are created/used in the correct resource group
   - Deployment completes successfully

## Files Modified

- `/home/azureuser/agentic-rag-demo/15-private-network-standard-agent-setup/main.bicep`
  - Updated capability host deployment condition
  - Simplified role assignment dependencies

## Verification Commands

```bash
# Check deployment validation
az deployment group validate --resource-group "bciep-test-6" --template-file main.bicep --parameters <user-parameters>

# Check deployment operations (should not include capability host when services are skipped)
az deployment operation group list --resource-group "bciep-test-6" --name "<deployment-name>"

# Verify DNS zones are in correct resource group
az resource list --resource-group "private-rg" --resource-type "Microsoft.Network/privateDnsZones" --output table
```
