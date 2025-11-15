// Service Bus Module
// Purpose: Message queue for agent logs and execution requests

@description('Service Bus namespace name')
param namespaceName string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('Service Bus SKU')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param sku string = 'Standard'

@description('Topic name for agent logs')
param topicName string = 'agent-logs'

@description('Queue name for execution requests')
param queueName string = 'execution-requests'

// Service Bus Namespace
resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: namespaceName
  location: location
  tags: tags
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    zoneRedundant: sku == 'Premium' ? true : false
  }
}

// Topic for agent logs
resource agentLogsTopic 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: topicName
  properties: {
    defaultMessageTimeToLive: 'P7D'
    maxSizeInMegabytes: 1024
    requiresDuplicateDetection: false
    enableBatchedOperations: true
    supportOrdering: true
    status: 'Active'
  }
}

// Subscription for log processing
resource logProcessingSubscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  parent: agentLogsTopic
  name: 'log-processor'
  properties: {
    defaultMessageTimeToLive: 'P7D'
    maxDeliveryCount: 10
    lockDuration: 'PT5M'
    requiresSession: false
    deadLetteringOnMessageExpiration: true
    enableBatchedOperations: true
  }
}

// Queue for execution requests
resource executionRequestsQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: queueName
  properties: {
    defaultMessageTimeToLive: 'P1D'
    maxSizeInMegabytes: 1024
    requiresDuplicateDetection: false
    requiresSession: false
    lockDuration: 'PT5M'
    maxDeliveryCount: 10
    deadLetteringOnMessageExpiration: true
    enableBatchedOperations: true
  }
}

// Outputs
output namespaceId string = serviceBusNamespace.id
output namespaceName string = serviceBusNamespace.name
output topicName string = agentLogsTopic.name
output queueName string = executionRequestsQueue.name
output endpoint string = serviceBusNamespace.properties.serviceBusEndpoint
output connectionString string = listKeys('${serviceBusNamespace.id}/AuthorizationRules/RootManageSharedAccessKey', serviceBusNamespace.apiVersion).primaryConnectionString
