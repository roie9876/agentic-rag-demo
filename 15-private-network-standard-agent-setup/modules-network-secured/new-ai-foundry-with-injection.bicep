/*
New AI Foundry Account with Network Injection
--------------------------------------------
This template creates a new AI Foundry account with network injection enabled,
reusing existing VNet, subnets, storage, AI Search, and other infrastructure.

Network injection allows agent workloads to execute in your controlled subnet.
This can only be configured when the AI Foundry account is first created.
*/

@description('Location for the new AI Foundry account')
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
param location string = 'swedencentral'

@description('Name for the new AI Foundry account')
param aiFoundryAccountName string = 'ai-foundry-with-injection'

// Model deployment parameters
@description('The name of the model to deploy')
param modelName string = 'gpt-4o'

@description('The format/provider of the model')
param modelFormat string = 'OpenAI'

@description('The version of the model')
param modelVersion string = '2024-11-20'

@description('The SKU name for the model deployment')
param modelSkuName string = 'GlobalStandard'

@description('The capacity (TPM) for the model deployment')
param modelCapacity int = 30

// Existing resource parameters
@description('Name of existing VNet')
param existingVnetName string = 'private-main-vnet'

@description('Name of existing agent subnet (must be delegated for network injection)')
param existingAgentSubnetName string = 'AgentSubnet'

@description('Name of existing private endpoint subnet')
param existingPrivateEndpointSubnetName string = 'PrivateEndpointSubnet'

@description('Name of existing storage account to use')
param existingStorageAccountName string = 'aiservicesjlbbstorage'

@description('Name of existing AI Search service to use')
param existingAiSearchName string = 'aiservicesjlbbsearch'

@description('Name of existing Cosmos DB account to use (optional)')
param existingCosmosDbName string = 'aiservicesjlbbcosmosdb'

@description('Resource group name where existing resources are located')
param existingResourceGroupName string = resourceGroup().name

@description('Enable network injection for agent execution')
param enableNetworkInjection bool = true

@description('Deployment timestamp for unique resource naming')
param deploymentTimestamp string = utcNow('yyyyMMddHHmmss')

// Create unique suffix for the new AI Foundry account
var uniqueSuffix = substring(uniqueString('${resourceGroup().id}-${deploymentTimestamp}'), 0, 4)
var accountName = toLower('${aiFoundryAccountName}${uniqueSuffix}')

// Reference existing network resources
resource existingVnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: existingVnetName
  scope: resourceGroup(existingResourceGroupName)
}

resource existingAgentSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: existingVnet
  name: existingAgentSubnetName
}

resource existingPrivateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: existingVnet
  name: existingPrivateEndpointSubnetName
}

// Reference existing services
// Note: These are commented out as they're not used in this minimal template
// Uncomment if you need to reference them for project configuration later

// resource existingStorageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
//   name: existingStorageAccountName
//   scope: resourceGroup(existingResourceGroupName)
// }

// resource existingAiSearch 'Microsoft.Search/searchServices@2023-11-01' existing = {
//   name: existingAiSearchName
//   scope: resourceGroup(existingResourceGroupName)
// }

// resource existingCosmosDb 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = if (existingCosmosDbName != '') {
//   name: existingCosmosDbName
//   scope: resourceGroup(existingResourceGroupName)
// }

// Create new AI Foundry account with network injection
#disable-next-line BCP036
resource aiFoundryAccount 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: accountName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Disabled'
    // Network injection configuration - can only be set at creation time
    networkInjections: ((enableNetworkInjection) ? [
      {
        scenario: 'agent'
        subnetArmId: existingAgentSubnet.id
        useMicrosoftManagedNetwork: false
      }
    ] : null)
    disableLocalAuth: false
  }
}

// Deploy the model to the new AI Foundry account
#disable-next-line BCP081
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: aiFoundryAccount
  name: modelName
  sku: {
    capacity: modelCapacity
    name: modelSkuName
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
      version: modelVersion
    }
  }
}

// Create private endpoint for the new AI Foundry account
resource aiFoundryPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: '${accountName}-private-endpoint'
  location: location
  properties: {
    subnet: {
      id: existingPrivateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: '${accountName}-private-link-connection'
        properties: {
          privateLinkServiceId: aiFoundryAccount.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

// Reference existing DNS zones
resource aiServicesPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: 'privatelink.services.ai.azure.com'
  scope: resourceGroup(existingResourceGroupName)
}

resource openAiPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: 'privatelink.openai.azure.com'
  scope: resourceGroup(existingResourceGroupName)
}

resource cognitiveServicesPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: 'privatelink.cognitiveservices.azure.com'
  scope: resourceGroup(existingResourceGroupName)
}

// Configure DNS for the new private endpoint
resource aiFoundryDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: aiFoundryPrivateEndpoint
  name: '${accountName}-dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: '${accountName}-aiservices-dns-config'
        properties: {
          privateDnsZoneId: aiServicesPrivateDnsZone.id
        }
      }
      {
        name: '${accountName}-openai-dns-config'
        properties: {
          privateDnsZoneId: openAiPrivateDnsZone.id
        }
      }
      {
        name: '${accountName}-cogservices-dns-config'
        properties: {
          privateDnsZoneId: cognitiveServicesPrivateDnsZone.id
        }
      }
    ]
  }
}

// Outputs
output aiFoundryAccountName string = aiFoundryAccount.name
output aiFoundryAccountId string = aiFoundryAccount.id
output aiFoundryEndpoint string = aiFoundryAccount.properties.endpoint
output privateEndpointName string = aiFoundryPrivateEndpoint.name
output networkInjectionEnabled bool = enableNetworkInjection
output agentSubnetId string = existingAgentSubnet.id
