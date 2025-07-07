param accountName string
param location string
param projectName string
param projectDescription string
param displayName string

param aiSearchName string
param aiSearchServiceResourceGroupName string
param aiSearchServiceSubscriptionId string

param cosmosDBName string
param cosmosDBSubscriptionId string
param cosmosDBResourceGroupName string

param azureStorageName string
param azureStorageSubscriptionId string
param azureStorageResourceGroupName string

// Check if services are actually deployed (non-empty names mean they exist)
var hasCosmosDB = cosmosDBName != ''
var hasAiSearch = aiSearchName != ''
var hasStorage = azureStorageName != ''

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' existing = if (hasAiSearch) {
  name: aiSearchName
  scope: resourceGroup(aiSearchServiceSubscriptionId, aiSearchServiceResourceGroupName)
}
resource cosmosDBAccount 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' existing = if (hasCosmosDB) {
  name: cosmosDBName
  scope: resourceGroup(cosmosDBSubscriptionId, cosmosDBResourceGroupName)
}
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = if (hasStorage) {
  name: azureStorageName
  scope: resourceGroup(azureStorageSubscriptionId, azureStorageResourceGroupName)
}

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: accountName
  scope: resourceGroup()
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: account
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: projectDescription
    displayName: displayName
  }
}

// Define connections as separate resources with explicit names - only create if the service exists
resource project_connection_cosmosdb_account 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (hasCosmosDB) {
  name: '${accountName}/${projectName}/${cosmosDBName}'
  properties: {
    category: 'CosmosDB'
    target: cosmosDBAccount.properties.documentEndpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: cosmosDBAccount.id
      location: cosmosDBAccount.location
    }
  }
  dependsOn: [
    project
  ]
}

resource project_connection_azure_storage 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (hasStorage) {
  name: '${accountName}/${projectName}/${azureStorageName}'
  properties: {
    category: 'AzureStorageAccount'
    target: storageAccount.properties.primaryEndpoints.blob
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: storageAccount.id
      location: storageAccount.location
    }
  }
  dependsOn: [
    project
  ]
}

resource project_connection_azureai_search 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (hasAiSearch) {
  name: '${accountName}/${projectName}/${aiSearchName}'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${aiSearchName}.search.windows.net'
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchService.id
      location: searchService.location
    }
  }
  dependsOn: [
    project
  ]
}

output projectName string = project.name
output projectId string = project.id
output projectPrincipalId string = project.identity.principalId

#disable-next-line BCP053
output projectWorkspaceId string = project.properties.internalId

// return the BYO connection names - only return if the service exists
output cosmosDBConnection string = hasCosmosDB ? cosmosDBName : ''
output azureStorageConnection string = hasStorage ? azureStorageName : ''
output aiSearchConnection string = hasAiSearch ? aiSearchName : ''
