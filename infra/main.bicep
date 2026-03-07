@description('Name of the Azure Developer CLI environment')
@minLength(1)
@maxLength(64)
param environmentName string

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Name of the AI model to deploy')
param modelName string = 'gpt-4o'

@description('Version of the AI model to deploy')
param modelVersion string

@description('Capacity (in thousands of tokens per minute) for the model deployment')
param modelCapacity int = 10

var resourceToken = uniqueString(resourceGroup().id)
var tags = {
  environment: environmentName
  project: 'bed-management-demo'
}

// --- Observability ---
module observability 'modules/observability.bicep' = {
  name: 'observability-${resourceToken}'
  params: {
    namePrefix: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
  }
}

// --- AI Foundry ---
module foundry 'modules/foundry.bicep' = {
  name: 'foundry-${resourceToken}'
  params: {
    namePrefix: environmentName
    location: location
    resourceToken: resourceToken
    modelName: modelName
    modelVersion: modelVersion
    modelCapacity: modelCapacity
    tags: tags
    logAnalyticsWorkspaceId: observability.outputs.logAnalyticsWorkspaceId
  }
}

// --- Azure Container Apps ---
module aca 'modules/aca.bicep' = {
  name: 'aca-${resourceToken}'
  params: {
    namePrefix: environmentName
    location: location
    resourceToken: resourceToken
    logAnalyticsWorkspaceId: observability.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: observability.outputs.appInsightsConnectionString
    foundryProjectEndpoint: foundry.outputs.projectEndpoint
    aiServicesId: foundry.outputs.aiServicesId
    modelDeploymentName: foundry.outputs.modelDeploymentName
    tags: tags
  }
}

// --- Outputs ---
@description('The URL of the deployed Container App')
output acaEndpointUrl string = aca.outputs.appUrl

@description('The ACR login server hostname')
output acrLoginServer string = aca.outputs.acrLoginServer

@description('The AI Foundry project endpoint')
output foundryProjectEndpoint string = foundry.outputs.projectEndpoint

@description('The name of the deployed Container App')
output appName string = aca.outputs.appName
