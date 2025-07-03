/*
Virtual Network Module for Existing VNets and Subnets
This module works with existing virtual networks and existing subnets.
It assumes that both the VNet and required subnets already exist.
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

@description('Address prefix for the agent subnet (not used, for compatibility)')
param agentSubnetPrefix string = ''

@description('Address prefix for the private endpoint subnet (not used, for compatibility)')
param peSubnetPrefix string = ''

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

// Output variables
output peSubnetName string = peSubnetName
output agentSubnetName string = agentSubnetName
output agentSubnetId string = existingAgentSubnet.id
output peSubnetId string = existingPeSubnet.id
output virtualNetworkName string = existingVNet.name
output virtualNetworkId string = existingVNet.id
output virtualNetworkResourceGroup string = vnetResourceGroupName
output virtualNetworkSubscriptionId string = vnetSubscriptionId
