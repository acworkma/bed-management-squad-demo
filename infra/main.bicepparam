using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'bedmgmt')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')
param modelName = 'gpt-4o'
param modelVersion = '2024-08-06'
param modelCapacity = 10
