# AI Foundry Hub Deployment - Network Scenarios Implementation

## Overview

The AI Foundry Hub deployment system now supports **three complete network scenarios** for deploying into Azure with flexible VNet and subnet configuration.

## Supported Network Scenarios

### 1. 🆕 **New VNet Scenario**
- **Description**: Creates a brand new VNet with new subnets
- **Use Case**: Fresh deployments in isolated environments
- **Parameters**:
  - `existingVnetResourceId`: `""` (empty)
  - `createSubnetsInExistingVnet`: `false`
  - `vnetAddressPrefix`: Required (e.g., `"10.0.0.0/16"`)
  - `agentSubnetPrefix`: Required (e.g., `"10.0.0.0/24"`)
  - `peSubnetPrefix`: Required (e.g., `"10.0.1.0/24"`)

### 2. 🔄 **Existing VNet + Existing Subnets Scenario**
- **Description**: Uses an existing VNet with existing subnets
- **Use Case**: Integrating into established network infrastructure
- **Parameters**:
  - `existingVnetResourceId`: Full resource ID of existing VNet
  - `createSubnetsInExistingVnet`: `false`
  - `agentSubnetName`: Name of existing agent subnet
  - `peSubnetName`: Name of existing PE subnet
  - No address prefixes needed (subnets already exist)

### 3. ⚡ **Existing VNet + New Subnets Scenario** *(NEW!)*
- **Description**: Uses an existing VNet but creates new subnets within it
- **Use Case**: Adding AI Foundry to existing VNet without existing suitable subnets
- **Parameters**:
  - `existingVnetResourceId`: Full resource ID of existing VNet
  - `createSubnetsInExistingVnet`: `true`
  - `agentSubnetName`: Name for new agent subnet
  - `peSubnetName`: Name for new PE subnet  
  - `agentSubnetPrefix`: Address prefix for new agent subnet
  - `peSubnetPrefix`: Address prefix for new PE subnet

## Implementation Components

### 1. Bicep Templates

#### Main Template (`main.bicep`)
- Accepts `existingVnetResourceId` parameter (full resource ID)
- Calculates `existingVnetPassedIn = existingVnetResourceId != ''`
- Extracts VNet details using `split()` function
- Passes `createSubnetsInExistingVnet` parameter to network module

#### Network Module (`network-agent-vnet.bicep`)
- Orchestrates three sub-modules based on parameters
- Routes to appropriate bicep module:
  - `vnet.bicep` for new VNet
  - `existing-vnet.bicep` for existing VNet + existing subnets
  - `existing-vnet-new-subnets.bicep` for existing VNet + new subnets

#### New Subnet Module (`existing-vnet-new-subnets.bicep`)
- References existing VNet using `resource ... existing`
- Creates new subnets with `Microsoft.Network/virtualNetworks/subnets`
- Configures agent subnet with Container Apps delegation
- Provides unified outputs matching other modules

### 2. Backend Service (`ai_foundry_hub_deployment.py`)

#### Parameter Generation Logic
```python
def generate_bicep_parameters(self, config: AIFoundryHubDeploymentConfig):
    if config.network_config.create_new_vnet:
        # Scenario 1: New VNet
        params["existingVnetResourceId"] = {"value": ""}
        params["createSubnetsInExistingVnet"] = {"value": False}
        # Include VNet and subnet address prefixes
    else:
        # Scenarios 2 & 3: Existing VNet
        params["existingVnetResourceId"] = {"value": vnet_resource_id}
        
        # Detect if using existing or new subnets
        has_existing_subnets = (existing_agent_subnet_id or existing_pe_subnet_id)
        params["createSubnetsInExistingVnet"] = {"value": not has_existing_subnets}
        
        # Only include address prefixes for new subnets
        if not has_existing_subnets:
            params["agentSubnetPrefix"] = {"value": ...}
            params["peSubnetPrefix"] = {"value": ...}
```

### 3. UI Components (`ai_foundry_hub_deployment_ui.py`)

#### Enhanced Subnet Configuration
- **VNet Selection**: Dropdown with existing VNets from subscription
- **Subnet Choice**: Radio buttons for "Use existing" vs "Create new"
- **Dynamic Fields**: Shows subnet dropdowns or address prefix inputs based on choice
- **Real-time Validation**: Displays selected subnet details and address ranges

#### User Experience Flow
1. Select network configuration type (New VNet vs Existing VNet)
2. If existing VNet:
   - Choose VNet from dropdown
   - Choose subnet strategy (existing vs new)
   - Configure subnets based on choice
3. Configure other resources and deploy

## Validation & Testing

### Test Coverage (`test_ai_foundry_parameter_generation.py`)
- ✅ **Scenario 1**: New VNet parameter validation
- ✅ **Scenario 2**: Existing VNet + existing subnets parameter validation  
- ✅ **Scenario 3**: Existing VNet + new subnets parameter validation
- ✅ **Parameter Differences**: Verifies correct parameters for each scenario

### Test Results
```
📊 Parameter generation summary:
   Scenario 1 (New VNet): 25 parameters
   Scenario 2 (Existing VNet + Existing Subnets): 22 parameters  
   Scenario 3 (Existing VNet + New Subnets): 24 parameters

🔍 Key parameter differences:
   existingVnetResourceId: '' | '/subscriptions/...' | '/subscriptions/...'
   createSubnetsInExistingVnet: False | False | True
   Has agentSubnetPrefix: True | False | True
   Has vnetAddressPrefix: True | False | False
```

## Key Technical Details

### Resource ID Handling
- The bicep template automatically extracts VNet name, subscription ID, and resource group from the full resource ID
- Backend passes the full resource ID, not extracted components
- UI validates resource ID format and fetches subnets automatically

### Subnet Delegation
- Agent subnets automatically get `Microsoft.App/environments` delegation for Container Apps
- Private endpoint subnets have no delegation requirements
- Existing subnets maintain their current delegation settings

### Error Handling
- Subnet address overlap detection (future enhancement)
- VNet access permission validation
- Graceful fallback when subnet enumeration fails

## Benefits

### For Users
- ✅ **Flexibility**: Choose the deployment scenario that fits your environment
- ✅ **Integration**: Seamlessly integrate with existing network infrastructure  
- ✅ **Isolation**: Create dedicated subnets without creating new VNets
- ✅ **Validation**: Real-time feedback on subnet selection and configuration

### For Operations
- ✅ **Consistency**: Unified bicep templates handle all scenarios
- ✅ **Maintainability**: Clear separation of concerns between modules
- ✅ **Testability**: Comprehensive test coverage for parameter generation
- ✅ **Flexibility**: Easy to extend with additional network scenarios

## Future Enhancements

### Potential Improvements
- [ ] **Address Space Validation**: Detect overlapping subnet ranges
- [ ] **Subnet Recommendations**: Suggest optimal subnet sizes based on deployment scale
- [ ] **Network Security Groups**: Optional NSG creation and configuration
- [ ] **Multi-Region Support**: Cross-region VNet peering scenarios
- [ ] **Hybrid Connectivity**: Integration with ExpressRoute/VPN gateways

### Configuration Management
- [ ] **Save/Load Configurations**: Persist deployment configurations
- [ ] **Template Validation**: Pre-deployment bicep template validation
- [ ] **Deployment Previews**: Show resource changes before deployment

## Status: ✅ COMPLETE

The "Existing VNet + New Subnets" scenario is fully implemented and tested. All three network scenarios are now supported with comprehensive UI, backend, and bicep template integration.
