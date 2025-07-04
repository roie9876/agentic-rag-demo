/*
Virtual Network Module for Existing VNet with New Subnets
This module works with existing virtual networks but creates new subnets.
Perfect for adding AI Foundry Hub subnets to an existing VNet with other resources.
*/

@description('The name of the existing virtual network')
param vnetName string

@description('Subscription ID of virtual network (if different from current subscription)')
param vnetSubscriptionId string = subscription().subscriptionId

@description('Resource Group name of the existing VNet (if different from current resource group)')
param vnetResourceGroupName string = resourceGroup().name

@description('The name of new Agents Subnet to create')
param agentSubnetName string = 'agent-subnet'

@description('The name of new Private Endpoint subnet to create')
param peSubnetName string = 'pe-subnet'

@description('Address prefix for the new agent subnet')
param agentSubnetPrefix string

@description('Address prefix for the new private endpoint subnet')
param peSubnetPrefix string

// Reference the existing virtual network (no scope when in same RG as deployment)
resource existingVNet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
}

// Create new agent subnet in existing VNet (using parent property for better syntax)
resource newAgentSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  name: agentSubnetName
  parent: existingVNet
  properties: {
    addressPrefix: agentSubnetPrefix
    delegations: [
      {
        name: 'Microsoft.app/environments'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}

// Create new private endpoint subnet in existing VNet (using parent property for better syntax)
resource newPeSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  name: peSubnetName
  parent: existingVNet
  properties: {
    addressPrefix: peSubnetPrefix
  }
}

// Output variables
output peSubnetName string = peSubnetName
output agentSubnetName string = agentSubnetName
output agentSubnetId string = newAgentSubnet.id
output peSubnetId string = newPeSubnet.id
output virtualNetworkName string = existingVNet.name
output virtualNetworkId string = existingVNet.id
output virtualNetworkResourceGroup string = vnetResourceGroupName
output virtualNetworkSubscriptionId string = vnetSubscriptionId
