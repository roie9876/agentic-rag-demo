@description('Azure region for the deployment')
param location string

@description('The name of the virtual network')
param vnetName string

@description('Indicates if an existing VNet should be used')
param useExistingVnet bool = false

@description('Indicates if subnets should be created in existing VNet (false = use existing subnets)')
param createSubnetsInExistingVnet bool = false

@description('Create agent subnet (true) or use existing (false). Only relevant when using existing VNet.')
param createAgentSubnet bool = true

@description('Create private endpoint subnet (true) or use existing (false). Only relevant when using existing VNet.')
param createPeSubnet bool = true

@description('Subscription ID of the existing VNet (if different from current subscription)')
param existingVnetSubscriptionId string = subscription().subscriptionId

@description('Resource Group name of the existing VNet (if different from current resource group)')
param existingVnetResourceGroupName string = resourceGroup().name

@description('The name of Agents Subnet')
param agentSubnetName string = 'agent-subnet'

@description('The name of Private Endpoint subnet')
param peSubnetName string = 'pe-subnet'

@description('Address space for the VNet (only used for new VNet)')
param vnetAddressPrefix string = ''

@description('Address prefix for the agent subnet')
param agentSubnetPrefix string = ''

@description('Address prefix for the private endpoint subnet')
param peSubnetPrefix string = ''

// Create new VNet if needed
module newVNet 'vnet.bicep' = if (!useExistingVnet) {
  name: 'vnet-deployment'
  params: {
    location: location
    vnetName: vnetName
    agentSubnetName: agentSubnetName
    peSubnetName: peSubnetName
    vnetAddressPrefix: vnetAddressPrefix
    agentSubnetPrefix: agentSubnetPrefix
    peSubnetPrefix: peSubnetPrefix
  }
}

// Use existing VNet with existing subnets
module existingVNet 'existing-vnet.bicep' = if (useExistingVnet && !createSubnetsInExistingVnet) {
  name: 'existing-vnet-deployment'
  params: {
    vnetName: vnetName
    vnetResourceGroupName: existingVnetResourceGroupName
    vnetSubscriptionId: existingVnetSubscriptionId
    agentSubnetName: agentSubnetName
    peSubnetName: peSubnetName
  }
}

// Use existing VNet but create new subnets (YOUR SCENARIO)
module existingVNetNewSubnets 'existing-vnet-new-subnets.bicep' = if (useExistingVnet && createSubnetsInExistingVnet) {
  name: 'existing-vnet-new-subnets-deployment'
  params: {
    vnetName: vnetName
    vnetResourceGroupName: existingVnetResourceGroupName
    vnetSubscriptionId: existingVnetSubscriptionId
    agentSubnetName: agentSubnetName
    peSubnetName: peSubnetName
    agentSubnetPrefix: agentSubnetPrefix
    peSubnetPrefix: peSubnetPrefix
    createAgentSubnet: createAgentSubnet
    createPeSubnet: createPeSubnet
  }
}

// Provide unified outputs regardless of which module was used
output virtualNetworkName string = useExistingVnet ? (createSubnetsInExistingVnet ? existingVNetNewSubnets.outputs.virtualNetworkName : existingVNet.outputs.virtualNetworkName) : newVNet.outputs.virtualNetworkName
output virtualNetworkId string = useExistingVnet ? (createSubnetsInExistingVnet ? existingVNetNewSubnets.outputs.virtualNetworkId : existingVNet.outputs.virtualNetworkId) : newVNet.outputs.virtualNetworkId
output virtualNetworkSubscriptionId string = useExistingVnet ? (createSubnetsInExistingVnet ? existingVNetNewSubnets.outputs.virtualNetworkSubscriptionId : existingVNet.outputs.virtualNetworkSubscriptionId) : newVNet.outputs.virtualNetworkSubscriptionId
output virtualNetworkResourceGroup string = useExistingVnet ? (createSubnetsInExistingVnet ? existingVNetNewSubnets.outputs.virtualNetworkResourceGroup : existingVNet.outputs.virtualNetworkResourceGroup) : newVNet.outputs.virtualNetworkResourceGroup
output agentSubnetName string = agentSubnetName
output peSubnetName string = peSubnetName
output agentSubnetId string = useExistingVnet ? (createSubnetsInExistingVnet ? existingVNetNewSubnets.outputs.agentSubnetId : existingVNet.outputs.agentSubnetId) : newVNet.outputs.agentSubnetId
output peSubnetId string = useExistingVnet ? (createSubnetsInExistingVnet ? existingVNetNewSubnets.outputs.peSubnetId : existingVNet.outputs.peSubnetId) : newVNet.outputs.peSubnetId
