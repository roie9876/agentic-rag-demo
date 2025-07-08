#!/usr/bin/env python3
"""
Diagnostic script to compare current Bicep deployment files with working commit
to identify the source of BCP177 error.

This script compares main.bicep and main.json from current state vs working commit
f28fb1d1a7dc67c1a04a558ac5184751e5a2e066
"""

import os
import sys
import difflib
import requests
from typing import Dict, List, Tuple, Optional

# Working commit files content (from previous fetch)
WORKING_MAIN_BICEP = """/*
Standard Setup Network Secured Steps for main.bicep
-----------------------------------
*/
@description('Location for all resources.')
@allowed([
    'australiaeast'
    'eastus'
    'eastus2'
    'francecentral'
    'japaneast'
    'norwayeast'
    'southindia'
    'swedencentral'
    'uaenorth'
    'uksouth'
    'westus'
    'westus3'
    'westus2'
  ])
param location string = 'eastus2'

@description('Name for your AI Services resource.')
param aiServices string = 'aiservices'

// Model deployment parameters - FIXED CONFIGURATION (Do not modify)
// This template deploys only gpt-4o model with version 2024-08-06, GlobalStandard SKU, and 30 TPM
@description('The name of the model to deploy - FIXED: gpt-4o')
param modelName string = 'gpt-4o'
@description('The provider of your model - FIXED: OpenAI')
param modelFormat string = 'OpenAI'
@description('The version of your model - FIXED: 2024-08-06')
param modelVersion string = '2024-08-06'
@description('The sku of your model deployment - FIXED: GlobalStandard')
param modelSkuName string = 'GlobalStandard'
@description('The tokens per minute (TPM) of your model deployment - FIXED: 30')
param modelCapacity int = 30

// Create a short, unique suffix, that will be unique to each resource group
param deploymentTimestamp string = utcNow('yyyyMMddHHmmss')
var uniqueSuffix = substring(uniqueString('${resourceGroup().id}-${deploymentTimestamp}'), 0, 4)
var accountName = toLower('${aiServices}${uniqueSuffix}')

@description('Name for your project resource.')
param firstProjectName string = 'project'

@description('This project will be a sub-resource of your account')
param projectDescription string = 'A project for the AI Foundry account with network secured deployed Agent'

@description('The display name of the project')
param displayName string = 'network secured agent project'

// Existing Virtual Network parameters
@description('Virtual Network name for the Agent to create new or existing virtual network')
param vnetName string = 'agent-vnet-test'

@description('The name of Agents Subnet to create new or existing subnet for agents')
param agentSubnetName string = 'agent-subnet'

@description('The name of Private Endpoint subnet to create new or existing subnet for private endpoints')
param peSubnetName string = 'pe-subnet'

//Existing standard Agent required resources
@description('Existing Virtual Network name Resource ID')
param existingVnetResourceId string = ''

@description('Address space for the VNet (only used for new VNet)')
param vnetAddressPrefix string = ''

@description('Address prefix for the agent subnet. The default value is 192.168.0.0/24 but you can choose any size /26 or any class like 10.0.0.0 or 172.168.0.0')
param agentSubnetPrefix string = ''

@description('Address prefix for the private endpoint subnet')
param peSubnetPrefix string = ''

@description('Create new subnets in existing VNet (true) or use existing subnets (false). Only relevant when using existing VNet.')
param createSubnetsInExistingVnet bool = true

@description('Create agent subnet (true) or use existing (false). Only relevant when using existing VNet.')
param createAgentSubnet bool = true

@description('Create private endpoint subnet (true) or use existing (false). Only relevant when using existing VNet.')
param createPeSubnet bool = true

@description('The AI Search Service full ARM Resource ID. This is an optional field, and if not provided, the resource will be created.')
param aiSearchResourceId string = ''
@description('The AI Storage Account full ARM Resource ID. This is an optional field, and if not provided, the resource will be created.')
param azureStorageAccountResourceId string = ''
@description('The Cosmos DB Account full ARM Resource ID. This is an optional field, and if not provided, the resource will be created.')
param azureCosmosDBAccountResourceId string = ''
@description('Skip Cosmos DB deployment entirely. When true, no Cosmos DB will be created or used.')
param skipCosmosDBDeployment bool = false

@description('Skip AI Search deployment entirely. When true, no AI Search will be created or used.')
param skipAiSearchDeployment bool = false

@description('Skip Storage Account deployment entirely. When true, no Storage Account will be created or used.')
param skipStorageAccountDeployment bool = false

@description('Skip OpenAI model deployment. When true, no OpenAI model will be deployed.')
param skipOpenAIDeployment bool = true

// Existing private endpoint names (if they already exist)
@description('Name of existing AI Search private endpoint (optional - if exists, will be used instead of creating new)')
param existingAiSearchPrivateEndpointName string = ''

@description('Name of existing Storage Account private endpoint (optional - if exists, will be used instead of creating new)')
param existingStoragePrivateEndpointName string = ''

@description('Name of existing Cosmos DB private endpoint (optional - if exists, will be used instead of creating new)')
param existingCosmosDBPrivateEndpointName string = ''

@description('Name of existing AI Services private endpoint (optional - if exists, will be used instead of creating new)')
param existingAiServicesPrivateEndpointName string = ''

// DNS Zone Location Parameters
@description('Subscription ID where private DNS zones are located')
param dnsZoneSubscriptionId string = subscription().subscriptionId

@description('Resource group name where private DNS zones are located')
param dnsZoneResourceGroupName string = resourceGroup().name

@description('Create new private DNS zones if they do not exist in the specified location')
param createDnsZonesIfNotExist bool = false

var projectName = toLower('${firstProjectName}${uniqueSuffix}')
var cosmosDBName = toLower('${aiServices}${uniqueSuffix}cosmosdb')
var aiSearchName = toLower('${aiServices}${uniqueSuffix}search')
var azureStorageName = toLower('${aiServices}${uniqueSuffix}storage')

// Check if existing resources have been passed in or should be skipped
var storagePassedIn = azureStorageAccountResourceId != '' && !skipStorageAccountDeployment
var searchPassedIn = aiSearchResourceId != '' && !skipAiSearchDeployment
var cosmosPassedIn = azureCosmosDBAccountResourceId != '' && !skipCosmosDBDeployment
var existingVnetPassedIn = existingVnetResourceId != ''


var acsParts = split(aiSearchResourceId, '/')
var aiSearchServiceSubscriptionId = searchPassedIn ? acsParts[2] : subscription().subscriptionId
var aiSearchServiceResourceGroupName = searchPassedIn ? acsParts[4] : resourceGroup().name

var cosmosParts = split(azureCosmosDBAccountResourceId, '/')
var cosmosDBSubscriptionId = cosmosPassedIn ? cosmosParts[2] : subscription().subscriptionId
var cosmosDBResourceGroupName = cosmosPassedIn ? cosmosParts[4] : resourceGroup().name

var storageParts = split(azureStorageAccountResourceId, '/')
var azureStorageSubscriptionId = storagePassedIn ? storageParts[2] : subscription().subscriptionId
var azureStorageResourceGroupName = storagePassedIn ? storageParts[4] : resourceGroup().name

var vnetParts = split(existingVnetResourceId, '/')
var vnetSubscriptionId = existingVnetPassedIn ? vnetParts[2] : subscription().subscriptionId
var vnetResourceGroupName = existingVnetPassedIn ? vnetParts[4] : resourceGroup().name
var existingVnetName = existingVnetPassedIn ? last(vnetParts) : vnetName
var trimVnetName = trim(existingVnetName)

@description('The name of the project capability host to be created')
param projectCapHost string = 'caphostproj'

// Create Virtual Network and Subnets
module vnet 'modules-network-secured/network-agent-vnet.bicep' = {
  name: 'vnet-${trimVnetName}-${uniqueSuffix}-deployment'
  params: {
    location: location
    vnetName: trimVnetName
    useExistingVnet: existingVnetPassedIn
    createSubnetsInExistingVnet: createSubnetsInExistingVnet
    createAgentSubnet: createAgentSubnet
    createPeSubnet: createPeSubnet
    existingVnetResourceGroupName: vnetResourceGroupName
    agentSubnetName: agentSubnetName
    peSubnetName: peSubnetName
    vnetAddressPrefix: vnetAddressPrefix
    agentSubnetPrefix: agentSubnetPrefix
    peSubnetPrefix: peSubnetPrefix
    existingVnetSubscriptionId: vnetSubscriptionId
  }
}

/*
  Create the AI Services account and gpt-4o model deployment (conditional)
*/
module aiAccount 'modules-network-secured/ai-account-identity.bicep' = if (!skipOpenAIDeployment) {
  name: 'ai-${accountName}-${uniqueSuffix}-deployment'
  params: {
    // workspace organization
    accountName: accountName
    location: location
    modelName: modelName
    modelFormat: modelFormat
    modelVersion: modelVersion
    modelSkuName: modelSkuName
    modelCapacity: modelCapacity
    agentSubnetId: vnet.outputs.agentSubnetId
  }
}
/*
  Validate existing resources
  This module will check if the AI Search Service, Storage Account, and Cosmos DB Account already exist.
  If they do, it will set the corresponding output to true. If they do not exist, it will set the output to false.
*/
module validateExistingResources 'modules-network-secured/validate-existing-resources.bicep' = {
  name: 'validate-existing-resources-${uniqueSuffix}-deployment'
  params: {
    aiSearchResourceId: aiSearchResourceId
    azureStorageAccountResourceId: azureStorageAccountResourceId
    azureCosmosDBAccountResourceId: azureCosmosDBAccountResourceId
  }
}

// This module will create new agent dependent resources
// A Cosmos DB account, an AI Search Service, and a Storage Account are created if they do not already exist
module aiDependencies 'modules-network-secured/standard-dependent-resources.bicep' = {
  name: 'dependencies-${accountName}-${uniqueSuffix}-deployment'
  params: {
    location: location
    azureStorageName: azureStorageName
    aiSearchName: aiSearchName
    cosmosDBName: cosmosDBName

    // AI Search Service parameters
    aiSearchResourceId: aiSearchResourceId
    aiSearchExists: validateExistingResources.outputs.aiSearchExists
    skipAiSearchDeployment: skipAiSearchDeployment

    // Storage Account
    azureStorageAccountResourceId: azureStorageAccountResourceId
    azureStorageExists: validateExistingResources.outputs.azureStorageExists
    skipStorageAccountDeployment: skipStorageAccountDeployment

    // Cosmos DB Account
    cosmosDBResourceId: azureCosmosDBAccountResourceId
    cosmosDBExists: validateExistingResources.outputs.cosmosDBExists
    skipCosmosDBDeployment: skipCosmosDBDeployment
    }
}

resource storage 'Microsoft.Storage/storageAccounts@2022-05-01' existing = if (!skipStorageAccountDeployment) {
  name: aiDependencies.outputs.azureStorageName
  scope: resourceGroup(azureStorageSubscriptionId, azureStorageResourceGroupName)
}


resource aiSearch 'Microsoft.Search/searchServices@2023-11-01' existing = if (!skipAiSearchDeployment) {
  name: aiDependencies.outputs.aiSearchName
  scope: resourceGroup(aiDependencies.outputs.aiSearchServiceSubscriptionId, aiDependencies.outputs.aiSearchServiceResourceGroupName)
}

resource cosmosDB 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = if (!skipCosmosDBDeployment) {
  name: aiDependencies.outputs.cosmosDBName
  scope: resourceGroup(cosmosDBSubscriptionId, cosmosDBResourceGroupName)
}

// Private Endpoint and DNS Configuration
// This module sets up private network access for all Azure services:
// 1. Creates private endpoints in the specified subnet
// 2. Sets up private DNS zones for each service
// 3. Links private DNS zones to the VNet for name resolution
// 4. Configures network policies to restrict access to private endpoints only
module privateEndpointAndDNS 'modules-network-secured/private-endpoint-and-dns.bicep' = {
    name: '${uniqueSuffix}-private-endpoint'
    params: {
      aiAccountName: skipOpenAIDeployment ? '' : aiAccount.outputs.accountName    // AI Services to secure (empty if skipped)
      aiSearchName: skipAiSearchDeployment ? '' : aiDependencies.outputs.aiSearchName       // AI Search to secure (empty if skipped)
      storageName: skipStorageAccountDeployment ? '' : aiDependencies.outputs.azureStorageName        // Storage to secure (empty if skipped)
      cosmosDBName: skipCosmosDBDeployment ? '' : aiDependencies.outputs.cosmosDBName
      vnetName: vnet.outputs.virtualNetworkName    // VNet containing subnets
      peSubnetName: vnet.outputs.peSubnetName        // Subnet for private endpoints
      suffix: uniqueSuffix                                    // Unique identifier
      vnetResourceGroupName: vnet.outputs.virtualNetworkResourceGroup
      vnetSubscriptionId: vnet.outputs.virtualNetworkSubscriptionId // Subscription ID for the VNet
      cosmosDBSubscriptionId: cosmosDBSubscriptionId // Subscription ID for Cosmos DB
      cosmosDBResourceGroupName: cosmosDBResourceGroupName // Resource Group for Cosmos DB
      aiSearchSubscriptionId: aiSearchServiceSubscriptionId // Subscription ID for AI Search Service
      aiSearchResourceGroupName: aiSearchServiceResourceGroupName // Resource Group for AI Search Service
      storageAccountResourceGroupName: azureStorageResourceGroupName // Resource Group for Storage Account
      storageAccountSubscriptionId: azureStorageSubscriptionId // Subscription ID for Storage Account
      // Pass existing private endpoint names
      existingAiAccountPrivateEndpointName: existingAiServicesPrivateEndpointName
      existingAiSearchPrivateEndpointName: existingAiSearchPrivateEndpointName
      existingStoragePrivateEndpointName: existingStoragePrivateEndpointName
      existingCosmosDBPrivateEndpointName: existingCosmosDBPrivateEndpointName
      skipCosmosDB: skipCosmosDBDeployment
      skipAiSearch: skipAiSearchDeployment
      skipStorage: skipStorageAccountDeployment
      skipOpenAI: skipOpenAIDeployment
      // DNS Zone Location Parameters
      dnsZoneSubscriptionId: dnsZoneSubscriptionId
      dnsZoneResourceGroupName: dnsZoneResourceGroupName
      createDnsZonesIfNotExist: createDnsZonesIfNotExist
    }
    dependsOn: [
    // Dependencies are automatically handled through conditional resource references in the module
  ]
  }

/*
  Creates a new project (sub-resource of the AI Services account) - only if OpenAI is not skipped
*/
module aiProject 'modules-network-secured/ai-project-identity.bicep' = if (!skipOpenAIDeployment) {
  name: 'ai-${projectName}-${uniqueSuffix}-deployment'
  params: {
    // workspace organization
    projectName: projectName
    projectDescription: projectDescription
    displayName: displayName
    location: location

    aiSearchName: aiDependencies.outputs.aiSearchName
    aiSearchServiceResourceGroupName: aiDependencies.outputs.aiSearchServiceResourceGroupName
    aiSearchServiceSubscriptionId: aiDependencies.outputs.aiSearchServiceSubscriptionId

    cosmosDBName: aiDependencies.outputs.cosmosDBName
    cosmosDBSubscriptionId: aiDependencies.outputs.cosmosDBSubscriptionId
    cosmosDBResourceGroupName: aiDependencies.outputs.cosmosDBResourceGroupName

    azureStorageName: aiDependencies.outputs.azureStorageName
    azureStorageSubscriptionId: aiDependencies.outputs.azureStorageSubscriptionId
    azureStorageResourceGroupName: aiDependencies.outputs.azureStorageResourceGroupName
    // dependent resources
    accountName: skipOpenAIDeployment ? '' : aiAccount.outputs.accountName
  }
  dependsOn: [
     privateEndpointAndDNS
     // Dependencies on services are handled through conditional resource references in the dependencies module
  ]
}

module formatProjectWorkspaceId 'modules-network-secured/format-project-workspace-id.bicep' = if (!skipOpenAIDeployment) {
  name: 'format-project-workspace-id-${uniqueSuffix}-deployment'
  params: {
    projectWorkspaceId: aiProject.outputs.projectWorkspaceId
  }
}

/*
  Assigns the project SMI the storage blob data contributor role on the storage account
*/
module storageAccountRoleAssignment 'modules-network-secured/azure-storage-account-role-assignment.bicep' = if (!skipOpenAIDeployment && !skipStorageAccountDeployment) {
  name: 'storage-${azureStorageName}-${uniqueSuffix}-deployment'
  scope: resourceGroup(azureStorageSubscriptionId, azureStorageResourceGroupName)
  params: {
    azureStorageName: aiDependencies.outputs.azureStorageName
    projectPrincipalId: aiProject.outputs.projectPrincipalId
  }
  dependsOn: [
   storage
   privateEndpointAndDNS
  ]
}

// The Comos DB Operator role must be assigned before the caphost is created
module cosmosAccountRoleAssignments 'modules-network-secured/cosmosdb-account-role-assignment.bicep' = if (!skipCosmosDBDeployment && !skipOpenAIDeployment) {
  name: 'cosmos-account-ra-${projectName}-${uniqueSuffix}-deployment'
  scope: resourceGroup(cosmosDBSubscriptionId, cosmosDBResourceGroupName)
  params: {
    cosmosDBName: aiDependencies.outputs.cosmosDBName
    projectPrincipalId: aiProject.outputs.projectPrincipalId
  }
  dependsOn: [
    cosmosDB
    privateEndpointAndDNS
  ]
}

// This role can be assigned before or after the caphost is created
module aiSearchRoleAssignments 'modules-network-secured/ai-search-role-assignments.bicep' = if (!skipAiSearchDeployment && !skipOpenAIDeployment) {
  name: 'ai-search-ra-${projectName}-${uniqueSuffix}-deployment'
  scope: resourceGroup(aiSearchServiceSubscriptionId, aiSearchServiceResourceGroupName)
  params: {
    aiSearchName: aiDependencies.outputs.aiSearchName
    projectPrincipalId: aiProject.outputs.projectPrincipalId
  }
  dependsOn: [
    aiSearch
    privateEndpointAndDNS
  ]
}

// This module creates the capability host for the project and account
module addProjectCapabilityHost 'modules-network-secured/add-project-capability-host.bicep' = if (!skipOpenAIDeployment && (!skipCosmosDBDeployment || !skipAiSearchDeployment || !skipStorageAccountDeployment)) {
  name: 'capabilityHost-configuration-${uniqueSuffix}-deployment'
  params: {
    accountName: aiAccount.outputs.accountName
    projectName: aiProject.outputs.projectName
    cosmosDBConnection: skipCosmosDBDeployment ? '' : aiProject.outputs.cosmosDBConnection
    azureStorageConnection: skipStorageAccountDeployment ? '' : aiProject.outputs.azureStorageConnection
    aiSearchConnection: skipAiSearchDeployment ? '' : aiProject.outputs.aiSearchConnection
    projectCapHost: projectCapHost
  }
  dependsOn: [
     // Only depend on resources that are actually being created
     privateEndpointAndDNS
     // Conditional dependencies on role assignments only if the services exist
  ]
}

// The Storage Blob Data Owner role must be assigned after the caphost is created
module storageContainersRoleAssignment 'modules-network-secured/blob-storage-container-role-assignments.bicep' = if (!skipOpenAIDeployment && !skipStorageAccountDeployment) {
  name: 'storage-containers-${uniqueSuffix}-deployment'
  scope: resourceGroup(azureStorageSubscriptionId, azureStorageResourceGroupName)
  params: {
    aiProjectPrincipalId: aiProject.outputs.projectPrincipalId
    storageName: aiDependencies.outputs.azureStorageName
    workspaceId: formatProjectWorkspaceId.outputs.projectWorkspaceIdGuid
  }
  dependsOn: [
    // Storage container role assignment can proceed without explicit dependency on capability host
    // since it's only deployed when storage is available
  ]
}

// The Cosmos Built-In Data Contributor role must be assigned after the caphost is created
module cosmosContainerRoleAssignments 'modules-network-secured/cosmos-container-role-assignments.bicep' = if (!skipOpenAIDeployment && !skipCosmosDBDeployment) {
  name: 'cosmos-ra-${uniqueSuffix}-deployment'
  scope: resourceGroup(cosmosDBSubscriptionId, cosmosDBResourceGroupName)
  params: {
    cosmosAccountName: aiDependencies.outputs.cosmosDBName
    projectWorkspaceId: formatProjectWorkspaceId.outputs.projectWorkspaceIdGuid
    projectPrincipalId: aiProject.outputs.projectPrincipalId

  }
dependsOn: [
  // Cosmos container role assignment can proceed without explicit dependency on capability host
  // since it's only deployed when cosmos is available  
  storageContainersRoleAssignment
  ]
}

// Output the AI Services connection information for easier testing
output aiServicesConnectionInfo object = skipOpenAIDeployment ? {} : {
  accountName: aiAccount.outputs.accountName
  endpoint: aiAccount.outputs.endpoint
  modelDeploymentName: aiAccount.outputs.modelDeploymentName
}

output aiProjectInfo object = skipOpenAIDeployment ? {} : {
  projectName: aiProject.outputs.projectName
  projectWorkspaceId: aiProject.outputs.projectWorkspaceId
  projectPrincipalId: aiProject.outputs.projectPrincipalId
}

output networkInfo object = {
  virtualNetworkName: vnet.outputs.virtualNetworkName
  agentSubnetName: vnet.outputs.agentSubnetName
  peSubnetName: vnet.outputs.peSubnetName
  virtualNetworkResourceGroup: vnet.outputs.virtualNetworkResourceGroup
  agentSubnetId: vnet.outputs.agentSubnetId
  peSubnetId: vnet.outputs.peSubnetId
}

output dependentResourcesInfo object = {
  aiSearchName: skipAiSearchDeployment ? '' : aiDependencies.outputs.aiSearchName
  azureStorageName: skipStorageAccountDeployment ? '' : aiDependencies.outputs.azureStorageName
  cosmosDBName: skipCosmosDBDeployment ? '' : aiDependencies.outputs.cosmosDBName
}
"""

def read_file_content(file_path: str) -> str:
    """Read content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""

def generate_diff_html(file1_content: str, file2_content: str, file1_name: str, file2_name: str) -> str:
    """Generate HTML diff between two file contents."""
    diff = difflib.unified_diff(
        file1_content.splitlines(keepends=True),
        file2_content.splitlines(keepends=True),
        fromfile=file1_name,
        tofile=file2_name,
        lineterm=''
    )
    return ''.join(diff)

def analyze_bicep_variables(content: str) -> Dict[str, List[str]]:
    """Analyze Bicep file for variable dependencies."""
    lines = content.split('\n')
    variables = {}
    current_var = None
    
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Variable declaration
        if stripped.startswith('var ') and '=' in stripped:
            var_name = stripped.split()[1].split('=')[0].strip()
            var_value = stripped.split('=', 1)[1].strip()
            variables[var_name] = {
                'line': line_num,
                'definition': var_value,
                'dependencies': []
            }
            
            # Look for dependencies in variable definition
            for other_var in variables.keys():
                if other_var in var_value and other_var != var_name:
                    variables[var_name]['dependencies'].append(other_var)
    
    return variables

def find_bcp177_issues(current_content: str, working_content: str) -> List[Dict]:
    """Find potential BCP177 issues by comparing variable dependencies."""
    current_vars = analyze_bicep_variables(current_content)
    working_vars = analyze_bicep_variables(working_content)
    
    issues = []
    
    # Check for new variables that might have dependency issues
    for var_name, var_info in current_vars.items():
        if var_name not in working_vars:
            issues.append({
                'type': 'new_variable',
                'variable': var_name,
                'line': var_info['line'],
                'definition': var_info['definition'],
                'dependencies': var_info['dependencies']
            })
        elif var_info['definition'] != working_vars[var_name]['definition']:
            issues.append({
                'type': 'changed_variable',
                'variable': var_name,
                'line': var_info['line'],
                'current_definition': var_info['definition'],
                'working_definition': working_vars[var_name]['definition'],
                'current_dependencies': var_info['dependencies'],
                'working_dependencies': working_vars[var_name]['dependencies']
            })
    
    return issues

def main():
    """Main diagnostic function."""
    print("🔍 Diagnosing Bicep Deployment BCP177 Error")
    print("=" * 60)
    
    # File paths
    current_bicep_path = "/home/azureuser/agentic-rag-demo/15-private-network-standard-agent-setup/main.bicep"
    current_json_path = "/home/azureuser/agentic-rag-demo/15-private-network-standard-agent-setup/main.json"
    
    # Read current files
    print("📖 Reading current files...")
    current_bicep = read_file_content(current_bicep_path)
    current_json = read_file_content(current_json_path)
    
    if not current_bicep or not current_json:
        print("❌ Failed to read current files")
        return
    
    # Compare with working versions
    print("🔄 Comparing with working commit...")
    
    # Generate diff for main.bicep
    print("\n📋 MAIN.BICEP DIFFERENCES:")
    print("-" * 40)
    bicep_diff = generate_diff_html(WORKING_MAIN_BICEP, current_bicep, 
                                   "working_main.bicep", "current_main.bicep")
    
    if bicep_diff:
        print(bicep_diff)
    else:
        print("✅ No differences found in main.bicep")
    
    # Analyze potential BCP177 issues
    print("\n🚨 POTENTIAL BCP177 ISSUES:")
    print("-" * 40)
    
    issues = find_bcp177_issues(current_bicep, WORKING_MAIN_BICEP)
    
    if issues:
        for issue in issues:
            print(f"\n⚠️  {issue['type'].upper()}: {issue['variable']}")
            print(f"   Line: {issue['line']}")
            
            if issue['type'] == 'new_variable':
                print(f"   Definition: {issue['definition']}")
                print(f"   Dependencies: {issue['dependencies']}")
            elif issue['type'] == 'changed_variable':
                print(f"   Current: {issue['current_definition']}")
                print(f"   Working: {issue['working_definition']}")
                print(f"   Dependency changes: {set(issue['current_dependencies']) - set(issue['working_dependencies'])}")
    else:
        print("✅ No obvious variable dependency issues found")
    
    # Look for specific patterns that could cause BCP177
    print("\n🔍 CHECKING FOR BCP177 PATTERNS:")
    print("-" * 40)
    
    bcp177_patterns = [
        "utcNow(",
        "resourceGroup().id",
        "subscription().subscriptionId",
        "uniqueString(",
        "deploymentTimestamp"
    ]
    
    lines = current_bicep.split('\n')
    for line_num, line in enumerate(lines, 1):
        for pattern in bcp177_patterns:
            if pattern in line and 'var ' in line:
                print(f"⚠️  Line {line_num}: {line.strip()}")
                print(f"   Contains pattern: {pattern}")
    
    # Key differences summary
    print("\n📊 SUMMARY OF KEY DIFFERENCES:")
    print("-" * 40)
    
    # Check model differences
    if 'gpt-4.1' in current_bicep and 'gpt-4o' in WORKING_MAIN_BICEP:
        print("🔄 Model changed: gpt-4o → gpt-4.1")
        print("🔄 Version changed: 2024-08-06 → 2025-04-14")
        print("⚠️  This could affect template validation")
    
    # Check for missing outputs
    working_has_outputs = 'output ' in WORKING_MAIN_BICEP
    current_has_outputs = 'output ' in current_bicep
    
    if working_has_outputs != current_has_outputs:
        if working_has_outputs and not current_has_outputs:
            print("❌ Current version missing outputs that were in working version")
        elif not working_has_outputs and current_has_outputs:
            print("➕ Current version has new outputs not in working version")
    
    print("\n🎯 RECOMMENDATIONS:")
    print("-" * 40)
    print("1. Check if gpt-4.1 model is available in the target region")
    print("2. Verify model version 2025-04-14 exists and is accessible")
    print("3. Consider reverting model parameters to working values:")
    print("   - modelName: 'gpt-4o'")
    print("   - modelVersion: '2024-08-06'")
    print("4. Test deployment with working model configuration first")

if __name__ == "__main__":
    main()
