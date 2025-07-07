/*
Private Endpoint and DNS Configuration Module
------------------------------------------
This module configures private network access for Azure services using:

1. Private Endpoints:
   - Creates network interfaces in the specified subnet
   - Establishes private connections to Azure services
   - Enables secure access without public internet exposure

2. Private DNS Zones:
   - Enables custom DNS resolution for private endpoints

3. DNS Zone Links:
   - Links private DNS zones to the VNet
   - Enables name resolution for resources in the VNet
   - Prevents DNS resolution conflicts

Security Benefits:
- Eliminates public internet exposure
- Enables secure access from within VNet
- Prevents data exfiltration through network
*/

// Resource names and identifiers
@description('Name of the AI Foundry account')
param aiAccountName string
@description('Name of the AI Search service')
param aiSearchName string
@description('Name of the storage account')
param storageName string
@description('Name of the Cosmos DB account')
param cosmosDBName string
@description('Name of the Vnet')
param vnetName string
@description('Name of the Customer subnet')
param peSubnetName string
@description('Suffix for unique resource names')
param suffix string

// Optional existing private endpoint names - if provided, will reference existing instead of creating new
@description('Name of existing AI Foundry private endpoint (optional)')
param existingAiAccountPrivateEndpointName string = ''

@description('Name of existing AI Search private endpoint (optional)')
param existingAiSearchPrivateEndpointName string = ''

@description('Name of existing Storage private endpoint (optional)')
param existingStoragePrivateEndpointName string = ''

@description('Name of existing Cosmos DB private endpoint (optional)')
param existingCosmosDBPrivateEndpointName string = ''

@description('Skip Cosmos DB deployment entirely (set to true if no Cosmos DB needed)')
param skipCosmosDB bool = false

@description('Skip AI Search deployment entirely (set to true if no AI Search needed)')
param skipAiSearch bool = false

@description('Skip Storage Account deployment entirely (set to true if no Storage needed)')
param skipStorage bool = false

@description('Skip OpenAI deployment entirely (set to true if no OpenAI/AI Services needed)')
param skipOpenAI bool = true

@description('Skip DNS zone group creation for existing private endpoints that already have them configured')
param skipExistingPrivateEndpointDnsGroups bool = true

@description('Resource Group name for existing Virtual Network (if different from current resource group)')
param vnetResourceGroupName string = resourceGroup().name

@description('Subscription ID for Virtual Network')
param vnetSubscriptionId string = subscription().subscriptionId

@description('Resource Group name for Storage Account')
param storageAccountResourceGroupName string = resourceGroup().name

@description('Subscription ID for Storage account')
param storageAccountSubscriptionId string = subscription().subscriptionId

@description('Subscription ID for AI Search service')
param aiSearchSubscriptionId string = subscription().subscriptionId

@description('Resource Group name for AI Search service')
param aiSearchResourceGroupName string = resourceGroup().name

@description('Subscription ID for Cosmos DB account')
param cosmosDBSubscriptionId string = subscription().subscriptionId

@description('Resource group name for Cosmos DB account')
param cosmosDBResourceGroupName string = resourceGroup().name

// DNS Zone Location Parameters
@description('Subscription ID where private DNS zones are located')
param dnsZoneSubscriptionId string = subscription().subscriptionId

@description('Resource group name where private DNS zones are located')
param dnsZoneResourceGroupName string = resourceGroup().name

@description('Create new private DNS zones if they do not exist in the specified location')
param createDnsZonesIfNotExist bool = false
// Reference existing services that need private endpoints
resource aiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = if (!skipOpenAI) {
  name: aiAccountName
  scope: resourceGroup()
}

resource aiSearch 'Microsoft.Search/searchServices@2023-11-01' existing = if (!skipAiSearch) {
  name: aiSearchName
  scope: resourceGroup(aiSearchSubscriptionId, aiSearchResourceGroupName)
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = if (!skipStorage) {
  name: storageName
  scope: resourceGroup(storageAccountSubscriptionId, storageAccountResourceGroupName)
}

resource cosmosDBAccount 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = if (existingCosmosDBPrivateEndpointName != '' && !skipCosmosDB) {
  name: cosmosDBName
  scope: resourceGroup(cosmosDBSubscriptionId, cosmosDBResourceGroupName)
}

// Reference existing network resources
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
  scope: resourceGroup(vnetSubscriptionId, vnetResourceGroupName)
}

resource peSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: vnet
  name: peSubnetName
}

// Reference existing private endpoints if they exist
resource existingAiAccountPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' existing = if (existingAiAccountPrivateEndpointName != '' && !skipOpenAI) {
  name: existingAiAccountPrivateEndpointName
}

resource existingAiSearchPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' existing = if (existingAiSearchPrivateEndpointName != '') {
  name: existingAiSearchPrivateEndpointName
}

resource existingStoragePrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' existing = if (existingStoragePrivateEndpointName != '') {
  name: existingStoragePrivateEndpointName
}

resource existingCosmosDBPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' existing = if (existingCosmosDBPrivateEndpointName != '') {
  name: existingCosmosDBPrivateEndpointName
}

/* -------------------------------------------- AI Foundry Account Private Endpoint -------------------------------------------- */

// Private endpoint for AI Services account (only create if not provided as existing)
// - Creates network interface in customer hub subnet
// - Establishes private connection to AI Services account
resource aiAccountPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (existingAiAccountPrivateEndpointName == '' && !skipOpenAI) {
  name: '${aiAccountName}-private-endpoint'
  location: resourceGroup().location
  properties: {
    subnet: {
      id: peSubnet.id                    // Deploy in customer hub subnet
    }
    privateLinkServiceConnections: [
      {
        name: '${aiAccountName}-private-link-service-connection'
        properties: {
          privateLinkServiceId: aiAccount.id
          groupIds: [
            'account'                     // Target AI Services account
          ]
        }
      }
    ]
  }
}

/* -------------------------------------------- AI Search Private Endpoint -------------------------------------------- */

// Private endpoint for AI Search (only create if not provided as existing)
// - Creates network interface in customer hub subnet
// - Establishes private connection to AI Search service
resource aiSearchPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (existingAiSearchPrivateEndpointName == '' && !skipAiSearch) {
  name: '${aiSearchName}-private-endpoint'
  location: resourceGroup().location
  properties: {
    subnet: {
      id: peSubnet.id                    // Deploy in customer hub subnet
    }
    privateLinkServiceConnections: [
      {
        name: '${aiSearchName}-private-link-service-connection'
        properties: {
          privateLinkServiceId: aiSearch.id
          groupIds: [
            'searchService'               // Target search service
          ]
        }
      }
    ]
  }
}

/* -------------------------------------------- Storage Private Endpoint -------------------------------------------- */

// Private endpoint for Storage Account (only create if not provided as existing)
// - Creates network interface in customer hub subnet
// - Establishes private connection to blob storage
resource storagePrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (existingStoragePrivateEndpointName == '' && !skipStorage) {
  name: '${storageName}-private-endpoint'
  location: resourceGroup().location
  properties: {
    subnet: {
      id: peSubnet.id                    // Deploy in customer hub subnet
    }
    privateLinkServiceConnections: [
      {
        name: '${storageName}-private-link-service-connection'
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'blob'                        // Target blob storage
          ]
        }
      }
    ]
  }
}

/*--------------------------------------------- Cosmos DB Private Endpoint -------------------------------------*/

// Private endpoint for Cosmos DB (only create if not provided as existing and not skipped)
resource cosmosDBPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (existingCosmosDBPrivateEndpointName == '' && !skipCosmosDB) {
  name: '${cosmosDBName}-private-endpoint'
  location: resourceGroup().location
  properties: {
    subnet: {
      id: peSubnet.id                    // Deploy in customer hub subnet
    }
    privateLinkServiceConnections: [
      {
        name: '${cosmosDBName}-private-link-service-connection'
        properties: {
          privateLinkServiceId: cosmosDBAccount.id
          groupIds: [
            'Sql'                        // Target Cosmos DB account
          ]
        }
      }
    ]
  }
}

/* -------------------------------------------- Private DNS Zones -------------------------------------------- */

// Create DNS zones in the specified resource group (only if createDnsZonesIfNotExist is true)
module dnsZonesCreation 'dns-zones.bicep' = if (createDnsZonesIfNotExist) {
  name: 'dns-zones-creation'
  scope: resourceGroup(dnsZoneSubscriptionId, dnsZoneResourceGroupName)
  params: {
    createAiServicesZone: !skipOpenAI
    createOpenAiZone: !skipOpenAI
    createCognitiveServicesZone: !skipOpenAI
    createAiSearchZone: !skipAiSearch
    createStorageZone: !skipStorage
    createCosmosDBZone: !skipCosmosDB
    vnetId: vnet.id
    suffix: suffix
  }
}

// Reference existing DNS zones with proper scope
resource aiServicesPrivateDnsZoneExisting 'Microsoft.Network/privateDnsZones@2020-06-01' existing = if (!createDnsZonesIfNotExist && !skipOpenAI) {
  name: 'privatelink.services.ai.azure.com'
  scope: resourceGroup(dnsZoneSubscriptionId, dnsZoneResourceGroupName)
}

resource openAiPrivateDnsZoneExisting 'Microsoft.Network/privateDnsZones@2020-06-01' existing = if (!createDnsZonesIfNotExist && !skipOpenAI) {
  name: 'privatelink.openai.azure.com'
  scope: resourceGroup(dnsZoneSubscriptionId, dnsZoneResourceGroupName)
}

resource cognitiveServicesPrivateDnsZoneExisting 'Microsoft.Network/privateDnsZones@2020-06-01' existing = if (!createDnsZonesIfNotExist && !skipOpenAI) {
  name: 'privatelink.cognitiveservices.azure.com'
  scope: resourceGroup(dnsZoneSubscriptionId, dnsZoneResourceGroupName)
}

resource aiSearchPrivateDnsZoneExisting 'Microsoft.Network/privateDnsZones@2020-06-01' existing = if (!createDnsZonesIfNotExist && !skipAiSearch) {
  name: 'privatelink.search.windows.net'
  scope: resourceGroup(dnsZoneSubscriptionId, dnsZoneResourceGroupName)
}

resource storagePrivateDnsZoneExisting 'Microsoft.Network/privateDnsZones@2020-06-01' existing = if (!createDnsZonesIfNotExist && !skipStorage) {
  name: 'privatelink.blob.${environment().suffixes.storage}'
  scope: resourceGroup(dnsZoneSubscriptionId, dnsZoneResourceGroupName)
}

resource cosmosDBPrivateDnsZoneExisting 'Microsoft.Network/privateDnsZones@2020-06-01' existing = if (!skipCosmosDB && !createDnsZonesIfNotExist) {
  name: 'privatelink.documents.azure.com'
  scope: resourceGroup(dnsZoneSubscriptionId, dnsZoneResourceGroupName)
}

// Variables to determine which DNS zone to use
var aiServicesPrivateDnsZoneId = !skipOpenAI ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.aiServicesZoneId : aiServicesPrivateDnsZoneExisting.id) : ''
var openAiPrivateDnsZoneId = !skipOpenAI ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.openAiZoneId : openAiPrivateDnsZoneExisting.id) : ''
var cognitiveServicesPrivateDnsZoneId = !skipOpenAI ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.cognitiveServicesZoneId : cognitiveServicesPrivateDnsZoneExisting.id) : ''
var aiSearchPrivateDnsZoneId = !skipAiSearch ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.aiSearchZoneId : aiSearchPrivateDnsZoneExisting.id) : ''
var storagePrivateDnsZoneId = !skipStorage ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.storageZoneId : storagePrivateDnsZoneExisting.id) : ''
var cosmosDBPrivateDnsZoneId = !skipCosmosDB ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.cosmosDBZoneId : cosmosDBPrivateDnsZoneExisting.id) : ''

// Helper arrays for DNS zone configs (only include zones with valid IDs)
var aiServicesDnsZoneConfigs = concat(
  !skipOpenAI && aiServicesPrivateDnsZoneId != '' ? [
    {
      name: '${aiAccountName}-dns-aiserv-config'
      properties: {
        privateDnsZoneId: aiServicesPrivateDnsZoneId
      }
    }
  ] : [],
  !skipOpenAI && openAiPrivateDnsZoneId != '' ? [
    {
      name: '${aiAccountName}-dns-openai-config'
      properties: {
        privateDnsZoneId: openAiPrivateDnsZoneId
      }
    }
  ] : [],
  !skipOpenAI && cognitiveServicesPrivateDnsZoneId != '' ? [
    {
      name: '${aiAccountName}-dns-cogserv-config'
      properties: {
        privateDnsZoneId: cognitiveServicesPrivateDnsZoneId
      }
    }
  ] : []
)

var aiSearchDnsZoneConfigs = !skipAiSearch && aiSearchPrivateDnsZoneId != '' ? [
  {
    name: '${aiSearchName}-dns-config'
    properties: {
      privateDnsZoneId: aiSearchPrivateDnsZoneId
    }
  }
] : []

var storageDnsZoneConfigs = !skipStorage && storagePrivateDnsZoneId != '' ? [
  {
    name: '${storageName}-dns-config'
    properties: {
      privateDnsZoneId: storagePrivateDnsZoneId
    }
  }
] : []

var cosmosDBDnsZoneConfigs = !skipCosmosDB && cosmosDBPrivateDnsZoneId != '' ? [
  {
    name: '${cosmosDBName}-dns-config'
    properties: {
      privateDnsZoneId: cosmosDBPrivateDnsZoneId
    }
  }
] : []

// DNS Zone Groups for AI Services

// 3) DNS Zone Group for AI Services - New Private Endpoint
resource aiServicesDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingAiAccountPrivateEndpointName == '' && !skipOpenAI && length(aiServicesDnsZoneConfigs) > 0) {
  parent: aiAccountPrivateEndpoint
  name: '${aiAccountName}-dns-group'
  properties: {
    privateDnsZoneConfigs: aiServicesDnsZoneConfigs
  }
}

// 3) DNS Zone Group for AI Services - Existing Private Endpoint (skip if already configured)
resource existingAiServicesDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingAiAccountPrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipOpenAI && length(aiServicesDnsZoneConfigs) > 0) {
  parent: existingAiAccountPrivateEndpoint
  name: '${aiAccountName}-dns-group-existing'
  properties: {
    privateDnsZoneConfigs: aiServicesDnsZoneConfigs
  }
}

// AI Search DNS Zone Groups using existing DNS zone
// 3) DNS Zone Group for AI Search - New Private Endpoint
resource aiSearchDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingAiSearchPrivateEndpointName == '' && !skipAiSearch && length(aiSearchDnsZoneConfigs) > 0) {
  parent: aiSearchPrivateEndpoint
  name: '${aiSearchName}-dns-group'
  properties: {
    privateDnsZoneConfigs: aiSearchDnsZoneConfigs
  }
}

// 3) DNS Zone Group for AI Search - Existing Private Endpoint
resource existingAiSearchDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingAiSearchPrivateEndpointName != '' && length(aiSearchDnsZoneConfigs) > 0) {
  parent: existingAiSearchPrivateEndpoint
  name: '${aiSearchName}-dns-group-existing'
  properties: {
    privateDnsZoneConfigs: aiSearchDnsZoneConfigs
  }
}

// Storage DNS Zone Groups using existing DNS zone
// 3) DNS Zone Group for Storage - New Private Endpoint
resource storageDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingStoragePrivateEndpointName == '' && !skipStorage && length(storageDnsZoneConfigs) > 0) {
  parent: storagePrivateEndpoint
  name: '${storageName}-dns-group'
  properties: {
    privateDnsZoneConfigs: storageDnsZoneConfigs
  }
}

// 3) DNS Zone Group for Storage - Existing Private Endpoint (skip if already configured)
resource existingStorageDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingStoragePrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && length(storageDnsZoneConfigs) > 0) {
  parent: existingStoragePrivateEndpoint
  name: '${storageName}-dns-group-existing'
  properties: {
    privateDnsZoneConfigs: storageDnsZoneConfigs
  }
}

// Cosmos DB DNS Zone Groups - only if not skipped
// 3) DNS Zone Group for Cosmos DB - New Private Endpoint
resource cosmosDBDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingCosmosDBPrivateEndpointName == '' && !skipCosmosDB && length(cosmosDBDnsZoneConfigs) > 0) {
  parent: cosmosDBPrivateEndpoint
  name: '${cosmosDBName}-dns-group'
  properties: {
    privateDnsZoneConfigs: cosmosDBDnsZoneConfigs
  }
}

// 3) DNS Zone Group for Cosmos DB - Existing Private Endpoint
resource existingCosmosDBDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingCosmosDBPrivateEndpointName != '' && !skipCosmosDB && length(cosmosDBDnsZoneConfigs) > 0) {
  parent: existingCosmosDBPrivateEndpoint
  name: '${cosmosDBName}-dns-group-existing'
  properties: {
    privateDnsZoneConfigs: cosmosDBDnsZoneConfigs
  }
}
