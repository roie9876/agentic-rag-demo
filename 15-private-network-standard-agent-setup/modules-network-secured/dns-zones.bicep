/*
DNS Zones Module
--------------
This module is designed to deploy private DNS zones to a specific resource group.
It's called from the main private-endpoint-and-dns.bicep module when createDnsZonesIfNotExist is true.
*/

@description('Create AI Services private DNS zone')
param createAiServicesZone bool = false

@description('Create OpenAI private DNS zone')
param createOpenAiZone bool = false

@description('Create Cognitive Services private DNS zone')
param createCognitiveServicesZone bool = false

@description('Create AI Search private DNS zone')
param createAiSearchZone bool = false

@description('Create Storage private DNS zone')
param createStorageZone bool = false

@description('Create Cosmos DB private DNS zone')
param createCosmosDBZone bool = false

@description('Virtual Network Resource ID for linking')
param vnetId string

@description('Suffix for unique resource names')
param suffix string

// AI Services DNS Zone
resource aiServicesPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (createAiServicesZone) {
  name: 'privatelink.services.ai.azure.com'
  location: 'global'
}

// OpenAI DNS Zone
resource openAiPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (createOpenAiZone) {
  name: 'privatelink.openai.azure.com'
  location: 'global'
}

// Cognitive Services DNS Zone
resource cognitiveServicesPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (createCognitiveServicesZone) {
  name: 'privatelink.cognitiveservices.azure.com'
  location: 'global'
}

// AI Search DNS Zone
resource aiSearchPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (createAiSearchZone) {
  name: 'privatelink.search.windows.net'
  location: 'global'
}

// Storage DNS Zone
resource storagePrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (createStorageZone) {
  name: 'privatelink.blob.${environment().suffixes.storage}'
  location: 'global'
}

// Cosmos DB DNS Zone
resource cosmosDBPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (createCosmosDBZone) {
  name: 'privatelink.documents.azure.com'
  location: 'global'
}

// VNet Links for newly created DNS zones
resource aiServicesVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createAiServicesZone) {
  parent: aiServicesPrivateDnsZone
  location: 'global'
  name: 'aiServices-${suffix}-link'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

resource openAiVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createOpenAiZone) {
  parent: openAiPrivateDnsZone
  location: 'global'
  name: 'openAi-${suffix}-link'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

resource cognitiveServicesVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createCognitiveServicesZone) {
  parent: cognitiveServicesPrivateDnsZone
  location: 'global'
  name: 'cognitiveServices-${suffix}-link'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

resource aiSearchVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createAiSearchZone) {
  parent: aiSearchPrivateDnsZone
  location: 'global'
  name: 'aiSearch-${suffix}-link'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

resource storageVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createStorageZone) {
  parent: storagePrivateDnsZone
  location: 'global'
  name: 'storage-${suffix}-link'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

resource cosmosDBVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createCosmosDBZone) {
  parent: cosmosDBPrivateDnsZone
  location: 'global'
  name: 'cosmosDB-${suffix}-link'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

// Outputs
output aiServicesZoneId string = createAiServicesZone ? aiServicesPrivateDnsZone.id : ''
output openAiZoneId string = createOpenAiZone ? openAiPrivateDnsZone.id : ''
output cognitiveServicesZoneId string = createCognitiveServicesZone ? cognitiveServicesPrivateDnsZone.id : ''
output aiSearchZoneId string = createAiSearchZone ? aiSearchPrivateDnsZone.id : ''
output storageZoneId string = createStorageZone ? storagePrivateDnsZone.id : ''
output cosmosDBZoneId string = createCosmosDBZone ? cosmosDBPrivateDnsZone.id : ''
