@description('Prefix used when generating resource names')
param namePrefix string

@description('Azure region for all resources')
param location string

@description('Unique token for resource name generation')
param resourceToken string

@description('Name of the AI model to deploy')
param modelName string

@description('Version of the AI model to deploy')
param modelVersion string

@description('Capacity (in thousands of tokens per minute) for the model deployment')
param modelCapacity int

@description('Tags to apply to all resources')
param tags object

@description('Resource ID of Log Analytics Workspace for diagnostics')
param logAnalyticsWorkspaceId string

var aiServicesName = 'aif-${namePrefix}-${resourceToken}'
var aiProjectName = 'proj-${namePrefix}-${resourceToken}'
var modelDeploymentName = modelName

// --- Azure AI Services account (this IS the Foundry resource) ---
resource aiServices 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiServicesName
  location: location
  tags: tags
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// --- Model Deployment (GPT-4o on the AI Services account) ---
resource modelDeploy 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aiServices
  name: modelDeploymentName
  sku: {
    name: 'Standard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
  }
}

// --- Foundry Project (child of the AI Services account) ---
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: aiServices
  name: aiProjectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
  dependsOn: [
    modelDeploy
  ]
}

// --- Diagnostic Settings for AI Services ---
resource aiServicesDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: '${aiServicesName}-diag'
  scope: aiServices
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// --- Outputs ---
@description('Project endpoint for the AI Foundry SDK v2')
output projectEndpoint string = aiProject.properties.endpoints['AI Foundry API']

@description('Endpoint of the AI Services account')
output aiServicesEndpoint string = aiServices.properties.endpoint

@description('Name of the model deployment')
output modelDeploymentName string = modelDeploy.name

@description('Resource ID of the AI Services account (for RBAC)')
output aiServicesId string = aiServices.id

@description('Connection string for AIProjectClient')
output projectConnectionString string = '${aiServicesName}.services.ai.azure.com;${subscription().subscriptionId};${resourceGroup().name};${aiProjectName}'
