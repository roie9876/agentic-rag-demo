/*
VNet Links Module
----------------
This module creates VNet links for private DNS zones deployed in a different resource group.
It's called from the main private-endpoint-and-dns.bicep module when createDnsZonesIfNotExist is true.
*/

@description('Suffix for unique resource names')
param suffix string

@description('Virtual Network Resource ID')
param vnetId string

@description('Create AI Services VNet link')
param createAiServicesLink bool = false

@description('Create OpenAI VNet link')
param createOpenAiLink bool = false

@description('Create Cognitive Services VNet link')
param createCognitiveServicesLink bool = false

@description('Create AI Search VNet link')
param createAiSearchLink bool = false

@description('Create Storage VNet link')
param createStorageLink bool = false

@description('Create Cosmos DB VNet link')
param createCosmosDBLink bool = false

// AI Services VNet Link
resource aiServicesVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createAiServicesLink) {
  name: 'privatelink.services.ai.azure.com/aiServices-${suffix}-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

// OpenAI VNet Link
resource openAiVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createOpenAiLink) {
  name: 'privatelink.openai.azure.com/openAi-${suffix}-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

// Cognitive Services VNet Link
resource cognitiveServicesVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createCognitiveServicesLink) {
  name: 'privatelink.cognitiveservices.azure.com/cognitiveServices-${suffix}-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

// AI Search VNet Link
resource aiSearchVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createAiSearchLink) {
  name: 'privatelink.search.windows.net/aiSearch-${suffix}-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

// Storage VNet Link
resource storageVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createStorageLink) {
  name: 'privatelink.blob.core.windows.net/storage-${suffix}-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}

// Cosmos DB VNet Link
resource cosmosDBVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (createCosmosDBLink) {
  name: 'privatelink.documents.azure.com/cosmosDB-${suffix}-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}
