/*
Enhanced Existing VNet Module with Auto-Delegation Support
This module works with existing virtual networks and existing subnets.
It can automatically add Microsoft.App/environments delegation if missing.
*/

@description('The name of the existing virtual network')
param vnetName string

@description('Subscription ID of virtual network (if different from current subscription)')
param vnetSubscriptionId string = subscription().subscriptionId

@description('Resource Group name of the existing VNet (if different from current resource group)')
param vnetResourceGroupName string = resourceGroup().name

@description('The name of existing Agents Subnet')
param agentSubnetName string = 'agent-subnet'

@description('The name of existing Private Endpoint subnet')
param peSubnetName string = 'pe-subnet'

@description('Automatically add Microsoft.App/environments delegation to agent subnet if missing')
param autoAddDelegation bool = true

// Reference the existing virtual network
resource existingVNet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
  scope: resourceGroup(vnetResourceGroupName)
}

// Reference existing agent subnet
resource existingAgentSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  name: agentSubnetName
  parent: existingVNet
}

// Reference existing PE subnet
resource existingPeSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  name: peSubnetName
  parent: existingVNet
}

// Validation logic for delegation
var hasDelegation = contains(existingAgentSubnet.properties, 'delegations') && length(existingAgentSubnet.properties.delegations) > 0
var hasCorrectDelegation = hasDelegation && contains(string(existingAgentSubnet.properties.delegations), 'Microsoft.App/environments')

// Required delegation configuration
var requiredDelegation = {
  name: 'Microsoft.App/environments'
  properties: {
    serviceName: 'Microsoft.App/environments'
  }
}

// Get existing delegations and merge with required delegation if needed
var currentDelegations = hasDelegation ? existingAgentSubnet.properties.delegations : []
var needsUpdate = autoAddDelegation && !hasCorrectDelegation
var updatedDelegations = needsUpdate ? union(currentDelegations, [requiredDelegation]) : currentDelegations

// Update agent subnet with delegation if needed and autoAddDelegation is true
resource updateAgentSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = if (needsUpdate) {
  name: agentSubnetName
  parent: existingVNet
  properties: {
    addressPrefix: existingAgentSubnet.properties.addressPrefix
    delegations: updatedDelegations
    // Preserve other existing properties
    networkSecurityGroup: contains(existingAgentSubnet.properties, 'networkSecurityGroup') ? existingAgentSubnet.properties.networkSecurityGroup : null
    routeTable: contains(existingAgentSubnet.properties, 'routeTable') ? existingAgentSubnet.properties.routeTable : null
    serviceEndpoints: contains(existingAgentSubnet.properties, 'serviceEndpoints') ? existingAgentSubnet.properties.serviceEndpoints : null
    privateEndpointNetworkPolicies: contains(existingAgentSubnet.properties, 'privateEndpointNetworkPolicies') ? existingAgentSubnet.properties.privateEndpointNetworkPolicies : null
    privateLinkServiceNetworkPolicies: contains(existingAgentSubnet.properties, 'privateLinkServiceNetworkPolicies') ? existingAgentSubnet.properties.privateLinkServiceNetworkPolicies : null
  }
}

// Validation: Fail deployment if delegation is missing and auto-add is disabled
var validationMessage = !hasCorrectDelegation && !autoAddDelegation 
  ? error('CRITICAL: Agent subnet "${agentSubnetName}" is missing required delegation to Microsoft.App/environments. Either add the delegation manually or set autoAddDelegation=true.')
  : 'Agent subnet delegation validation passed'

// Output variables
output peSubnetName string = peSubnetName
output agentSubnetName string = agentSubnetName
output agentSubnetId string = needsUpdate ? updateAgentSubnet.id : existingAgentSubnet.id
output peSubnetId string = existingPeSubnet.id
output virtualNetworkName string = existingVNet.name
output virtualNetworkId string = existingVNet.id
output virtualNetworkResourceGroup string = vnetResourceGroupName
output virtualNetworkSubscriptionId string = vnetSubscriptionId

// Delegation status outputs
output hadDelegation bool = hasDelegation
output hasCorrectDelegation bool = hasCorrectDelegation
output wasUpdated bool = needsUpdate
output finalDelegations array = needsUpdate ? updatedDelegations : currentDelegations
output validationResult string = needsUpdate 
  ? 'Agent subnet delegation was automatically added: Microsoft.App/environments'
  : hasCorrectDelegation 
    ? 'Agent subnet has correct Microsoft.App/environments delegation' 
    : 'Agent subnet delegation validation completed'
