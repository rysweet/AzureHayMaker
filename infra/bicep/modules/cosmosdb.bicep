// Cosmos DB Module
// Purpose: NoSQL database for execution metrics and telemetry

@description('Cosmos DB account name (globally unique)')
@minLength(3)
@maxLength(44)
param accountName string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('Database name')
param databaseName string = 'haymaker'

@description('Container name for metrics')
param metricsContainerName string = 'metrics'

@description('Container name for runs')
param runsContainerName string = 'runs'

@description('Throughput (RU/s) - set to 0 for serverless')
@minValue(0)
@maxValue(1000000)
param throughput int = 400

// Cosmos DB Account
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: throughput == 0 ? [
      {
        name: 'EnableServerless'
      }
    ] : []
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    publicNetworkAccess: 'Enabled'
    enableFreeTier: false
  }
}

// Database
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
    options: throughput == 0 ? {} : {
      throughput: throughput
    }
  }
}

// Metrics Container
resource metricsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: database
  name: metricsContainerName
  properties: {
    resource: {
      id: metricsContainerName
      partitionKey: {
        paths: [
          '/scenario_name'
        ]
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
      defaultTtl: 2592000 // 30 days
    }
  }
}

// Runs Container
resource runsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: database
  name: runsContainerName
  properties: {
    resource: {
      id: runsContainerName
      partitionKey: {
        paths: [
          '/run_id'
        ]
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
      }
      defaultTtl: 7776000 // 90 days
    }
  }
}

// Outputs
output accountId string = cosmosAccount.id
output accountName string = cosmosAccount.name
output endpoint string = cosmosAccount.properties.documentEndpoint
output databaseName string = database.name
output metricsContainerName string = metricsContainer.name
output runsContainerName string = runsContainer.name
output primaryKey string = cosmosAccount.listKeys().primaryMasterKey
output connectionString string = 'AccountEndpoint=${cosmosAccount.properties.documentEndpoint};AccountKey=${cosmosAccount.listKeys().primaryMasterKey};'
