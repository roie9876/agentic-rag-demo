param cosmosDBConnection string 
param azureStorageConnection string 
param aiSearchConnection string
param projectName string
param accountName string
param projectCapHost string

// Create arrays only for non-empty connections
var threadConnections = cosmosDBConnection != '' ? [cosmosDBConnection] : []
var storageConnections = azureStorageConnection != '' ? [azureStorageConnection] : []
var vectorStoreConnections = aiSearchConnection != '' ? [aiSearchConnection] : []

// Check if we have any connections at all
var hasAnyConnections = length(threadConnections) > 0 || length(storageConnections) > 0 || length(vectorStoreConnections) > 0


resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
   name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  name: projectName
  parent: account
}

// Only create capability host if we have at least one service connection
// AI Foundry Agent capability hosts require at least one service to be useful
resource projectCapabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = if (hasAnyConnections) {
  name: projectCapHost
  parent: project
  properties: {
    capabilityHostKind: 'Agents'
    vectorStoreConnections: vectorStoreConnections
    storageConnections: storageConnections
    threadStorageConnections: threadConnections
  }
}

output projectCapHost string = hasAnyConnections ? projectCapabilityHost.name : ''
