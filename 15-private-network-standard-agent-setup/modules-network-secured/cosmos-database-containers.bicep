// Creates the enterprise_memory database and required containers for AI Foundry Agent
// This module fills the missing gap between CosmosDB account creation and role assignments

@description('Name of the Cosmos DB account')
param cosmosAccountName string

@description('Project workspace ID for container naming')
param projectWorkspaceId string

// Reference the existing Cosmos DB account
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' existing = {
  name: cosmosAccountName
}

// Create the enterprise_memory database
resource enterpriseMemoryDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' = {
  parent: cosmosAccount
  name: 'enterprise_memory'
  properties: {
    resource: {
      id: 'enterprise_memory'
    }
    options: {
      throughput: 400 // Minimum provisioned throughput
    }
  }
}

// Container names based on project workspace ID
var userThreadName = '${projectWorkspaceId}-thread-message-store'
var systemThreadName = '${projectWorkspaceId}-system-thread-message-store'
var entityStoreName = '${projectWorkspaceId}-agent-entity-store'

// Create user thread message store container
resource userThreadContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = {
  parent: enterpriseMemoryDatabase
  name: userThreadName
  properties: {
    resource: {
      id: userThreadName
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
    options: {
      throughput: 400
    }
  }
}

// Create system thread message store container
resource systemThreadContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = {
  parent: enterpriseMemoryDatabase
  name: systemThreadName
  properties: {
    resource: {
      id: systemThreadName
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
    options: {
      throughput: 400
    }
  }
}

// Create agent entity store container
resource entityStoreContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = {
  parent: enterpriseMemoryDatabase
  name: entityStoreName
  properties: {
    resource: {
      id: entityStoreName
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
    options: {
      throughput: 400
    }
  }
}

// Outputs for other modules to reference
output databaseName string = enterpriseMemoryDatabase.name
output databaseId string = enterpriseMemoryDatabase.id

output userThreadContainerName string = userThreadContainer.name
output userThreadContainerId string = userThreadContainer.id

output systemThreadContainerName string = systemThreadContainer.name
output systemThreadContainerId string = systemThreadContainer.id

output entityStoreContainerName string = entityStoreContainer.name
output entityStoreContainerId string = entityStoreContainer.id

// Container resource references for role assignments
output userThreadContainerReference object = {
  id: userThreadContainer.id
  name: userThreadContainer.name
}

output systemThreadContainerReference object = {
  id: systemThreadContainer.id
  name: systemThreadContainer.name
}

output entityStoreContainerReference object = {
  id: entityStoreContainer.id
  name: entityStoreContainer.name
}
