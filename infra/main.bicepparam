using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'bedmgmt')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')
param modelName = 'gpt-5.2'
param modelVersion = '2025-12-11'
param modelCapacity = 100
