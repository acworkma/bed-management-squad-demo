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

var aiServicesName = 'ai-${namePrefix}-${resourceToken}'
var aiHubName = 'ah-${namePrefix}-${resourceToken}'
var aiProjectName = 'ap-${namePrefix}-${resourceToken}'
var modelDeploymentName = modelName

// --- Azure AI Services account (Foundry backbone) ---
resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
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
    disableLocalAuth: true
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

// --- AI Hub (Machine Learning workspace — Hub kind) ---
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: aiHubName
  location: location
  tags: tags
  kind: 'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    friendlyName: 'Bed Management AI Hub'
    description: 'AI Hub for Patient Flow / Bed Management demo'
    publicNetworkAccess: 'Enabled'
  }

  // Connect AI Services to the Hub
  resource aiServicesConnection 'connections@2024-10-01' = {
    name: '${aiHubName}-ais-connection'
    properties: {
      category: 'AIServices'
      target: aiServices.properties.endpoint
      authType: 'AAD'
      isSharedToAll: true
      metadata: {
        ApiType: 'Azure'
        ResourceId: aiServices.id
      }
    }
  }
}

// --- AI Project (Machine Learning workspace — Project kind) ---
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: aiProjectName
  location: location
  tags: tags
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    friendlyName: 'Bed Management AI Project'
    description: 'AI Project for Patient Flow / Bed Management scenarios'
    hubResourceId: aiHub.id
    publicNetworkAccess: 'Enabled'
  }
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
@description('Endpoint of the AI Project (agents endpoint for SDK v2)')
output projectEndpoint string = 'https://${location}.api.azureml.ms/agents/v1.0/subscriptions/${subscription().subscriptionId}/resourceGroups/${resourceGroup().name}/providers/Microsoft.MachineLearningServices/workspaces/${aiProject.name}'

@description('Endpoint of the AI Services account')
output aiServicesEndpoint string = aiServices.properties.endpoint

@description('Name of the model deployment')
output modelDeploymentName string = modelDeploy.name

@description('Resource ID of the AI Services account (for RBAC)')
output aiServicesId string = aiServices.id

@description('Connection string for AIProjectClient (used by build_agents.py)')
output projectConnectionString string = '${location}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${aiProject.name}'
