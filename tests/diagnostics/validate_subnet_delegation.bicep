/*
Subnet Delegation Validation and Auto-Fix Module
Validates that existing agent subnets have the required Microsoft.App/environments delegation
If delegation is missing, automatically adds it to the subnet
*/

@description('The name of the existing virtual network')
param vnetName string

@description('Subscription ID of virtual network')
param vnetSubscriptionId string = subscription().subscriptionId

@description('Resource Group name of the existing VNet')
param vnetResourceGroupName string = resourceGroup().name

@description('The name of existing agent subnet to validate and potentially fix')
param agentSubnetName string = 'agent-subnet'

@description('Automatically add Microsoft.App/environments delegation if missing')
param autoAddDelegation bool = true

// Reference the existing virtual network
resource existingVNet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
  scope: resourceGroup(vnetSubscriptionId, vnetResourceGroupName)
}

// Reference existing agent subnet
resource existingAgentSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  name: agentSubnetName
  parent: existingVNet
}

// Validation logic
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

// Update subnet with delegation if needed and autoAddDelegation is true
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

output agentSubnetId string = needsUpdate ? updateAgentSubnet.id : existingAgentSubnet.id
output hasDelegation bool = hasDelegation
output hasCorrectDelegation bool = hasCorrectDelegation
output delegationDetails array = hasDelegation ? existingAgentSubnet.properties.delegations : []
output wasUpdated bool = needsUpdate
output finalDelegations array = needsUpdate ? updatedDelegations : currentDelegations
output validationMessage string = needsUpdate 
  ? 'Agent subnet delegation was automatically added: Microsoft.App/environments'
  : hasCorrectDelegation 
    ? 'Agent subnet has correct Microsoft.App/environments delegation' 
    : hasDelegation 
      ? 'Agent subnet has delegation but NOT Microsoft.App/environments' 
      : 'Agent subnet has NO delegation - Microsoft.App/environments delegation required'
output isValid bool = hasCorrectDelegation || needsUpdate
