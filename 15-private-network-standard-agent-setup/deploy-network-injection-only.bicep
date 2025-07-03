/*
Deploy only AI Foundry Account with Network Injection
This template creates a new AI Foundry account with network injection enabled.
Network injection allows agents to be deployed into a delegated subnet.
*/

@description('Location for all resources.')
@allowed([
    'australiaeast'
    'eastus'
    'eastus2'
    'francecentral'
    'japaneast'
    'norwayeast'
    'southindia'
    'swedencentral'
    'uaenorth'
    'uksouth'
    'westus'
    'westus3'
    'westus2'
  ])
param location string = 'eastus2'

@description('Name for your AI Services resource.')
param aiServices string = 'aiservices-netinject'

// Model deployment parameters
@description('The name of the model you want to deploy')
param modelName string = 'gpt-4o'
@description('The provider of your model')
param modelFormat string = 'OpenAI'
@description('The version of your model')
param modelVersion string = '2024-11-20'
@description('The sku of your model deployment')
param modelSkuName string = 'GlobalStandard'
@description('The tokens per minute (TPM) of your model deployment')
param modelCapacity int = 30

// Network parameters for injection
@description('Resource ID of the virtual network where the agent subnet exists')
param vnetResourceId string

@description('Name of the subnet delegated for AI agents (must be delegated to Microsoft.MachineLearningServices/workspaces)')
param agentSubnetName string = 'snet-agent'

// Create a short, unique suffix
param deploymentTimestamp string = utcNow('yyyyMMddHHmmss')
var uniqueSuffix = substring(uniqueString('${resourceGroup().id}-${deploymentTimestamp}'), 0, 4)
var accountName = toLower('${aiServices}${uniqueSuffix}')

// Calculate agent subnet ID
var agentSubnetId = '${vnetResourceId}/subnets/${agentSubnetName}'

// Deploy AI Foundry account with network injection
module aiFoundryAccount 'modules-network-secured/ai-account-identity.bicep' = {
  name: 'ai-foundry-network-injection-${uniqueSuffix}'
  params: {
    accountName: accountName
    location: location
    modelName: modelName
    modelFormat: modelFormat
    modelVersion: modelVersion
    modelSkuName: modelSkuName
    modelCapacity: modelCapacity
    agentSubnetId: agentSubnetId
    networkInjection: 'true'
  }
}

output aiFoundryAccountName string = aiFoundryAccount.outputs.accountName
output aiFoundryAccountId string = aiFoundryAccount.outputs.accountID
output aiFoundryEndpoint string = aiFoundryAccount.outputs.accountTarget
output aiFoundryPrincipalId string = aiFoundryAccount.outputs.accountPrincipalId
output agentSubnetUsed string = agentSubnetId
