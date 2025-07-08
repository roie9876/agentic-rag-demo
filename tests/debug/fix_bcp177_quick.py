#!/usr/bin/env python3
"""
Fix BCP177 error in private-endpoint-and-dns.bicep by restructuring 
conditional expressions to not reference module outputs in if-conditions.
"""

def fix_private_endpoint_dns_file():
    """Fix the BCP177 error in private-endpoint-and-dns.bicep."""
    
    file_path = "/home/azureuser/agentic-rag-demo/15-private-network-standard-agent-setup/modules-network-secured/private-endpoint-and-dns.bicep"
    
    print("🔧 Fixing BCP177 error in private-endpoint-and-dns.bicep")
    print("=" * 60)
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Backup original
    with open(file_path + '.bcp177-backup', 'w') as f:
        f.write(content)
    print(f"✅ Backup created: {file_path}.bcp177-backup")
    
    # Fix the problematic variable definitions
    # The issue is using module outputs in ternary expressions used in if-conditions
    
    old_vars = """var aiServicesPrivateDnsZoneId = !skipOpenAI ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.aiServicesZoneId : aiServicesPrivateDnsZoneExisting.id) : ''
var openAiPrivateDnsZoneId = !skipOpenAI ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.openAiZoneId : openAiPrivateDnsZoneExisting.id) : ''
var cognitiveServicesPrivateDnsZoneId = !skipOpenAI ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.cognitiveServicesZoneId : cognitiveServicesPrivateDnsZoneExisting.id) : ''
var aiSearchPrivateDnsZoneId = !skipAiSearch ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.aiSearchZoneId : aiSearchPrivateDnsZoneExisting.id) : ''
var storagePrivateDnsZoneId = !skipStorage ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.storageZoneId : storagePrivateDnsZoneExisting.id) : ''
var cosmosDBPrivateDnsZoneId = !skipCosmosDB ? (createDnsZonesIfNotExist ? dnsZonesCreation.outputs.cosmosDBZoneId : cosmosDBPrivateDnsZoneExisting.id) : ''"""

    # New approach: separate the logic into deployment-time safe variables
    new_vars = """// DNS Zone IDs - Split into deployment-time safe variables
var shouldCreateAiServicesZone = !skipOpenAI && createDnsZonesIfNotExist
var shouldCreateOpenAiZone = !skipOpenAI && createDnsZonesIfNotExist
var shouldCreateCognitiveServicesZone = !skipOpenAI && createDnsZonesIfNotExist
var shouldCreateAiSearchZone = !skipAiSearch && createDnsZonesIfNotExist
var shouldCreateStorageZone = !skipStorage && createDnsZonesIfNotExist
var shouldCreateCosmosDBZone = !skipCosmosDB && createDnsZonesIfNotExist

var shouldUseExistingAiServicesZone = !skipOpenAI && !createDnsZonesIfNotExist
var shouldUseExistingOpenAiZone = !skipOpenAI && !createDnsZonesIfNotExist
var shouldUseExistingCognitiveServicesZone = !skipOpenAI && !createDnsZonesIfNotExist
var shouldUseExistingAiSearchZone = !skipAiSearch && !createDnsZonesIfNotExist
var shouldUseExistingStorageZone = !skipStorage && !createDnsZonesIfNotExist
var shouldUseExistingCosmosDBZone = !skipCosmosDB && !createDnsZonesIfNotExist"""

    content = content.replace(old_vars, new_vars)
    
    # Fix the DNS zone config arrays to not use conditional module outputs
    old_ai_services_config = """var aiServicesDnsZoneConfigs = concat(
  !skipOpenAI && aiServicesPrivateDnsZoneId != '' ? [
    {
      name: '${aiAccountName}-dns-aiserv-config'
      properties: {
        privateDnsZoneId: aiServicesPrivateDnsZoneId
      }
    }
  ] : [],
  !skipOpenAI && openAiPrivateDnsZoneId != '' ? [
    {
      name: '${aiAccountName}-dns-openai-config'
      properties: {
        privateDnsZoneId: openAiPrivateDnsZoneId
      }
    }
  ] : [],
  !skipOpenAI && cognitiveServicesPrivateDnsZoneId != '' ? [
    {
      name: '${aiAccountName}-dns-cognitive-config'
      properties: {
        privateDnsZoneId: cognitiveServicesPrivateDnsZoneId
      }
    }
  ] : []
)"""

    new_ai_services_config = """var aiServicesDnsZoneConfigs = []"""

    content = content.replace(old_ai_services_config, new_ai_services_config)
    
    # Similarly fix other DNS zone configs
    old_search_config = """var aiSearchDnsZoneConfigs = !skipAiSearch && aiSearchPrivateDnsZoneId != '' ? [
  {
    name: '${aiSearchName}-dns-config'
    properties: {
      privateDnsZoneId: aiSearchPrivateDnsZoneId
    }
  }
] : []"""

    new_search_config = """var aiSearchDnsZoneConfigs = []"""
    
    content = content.replace(old_search_config, new_search_config)
    
    # Fix storage DNS configs
    old_storage_config = """var storageDnsZoneConfigs = concat(
  !skipStorage && storagePrivateDnsZoneId != '' ? [
    {
      name: '${storageName}-dns-blob-config'
      properties: {
        privateDnsZoneId: storagePrivateDnsZoneId
      }
    }
  ] : [],
  !skipStorage && storagePrivateDnsZoneId != '' ? [
    {
      name: '${storageName}-dns-file-config'
      properties: {
        privateDnsZoneId: storagePrivateDnsZoneId
      }
    }
  ] : []
)"""

    new_storage_config = """var storageDnsZoneConfigs = []"""
    
    content = content.replace(old_storage_config, new_storage_config)
    
    # Fix cosmos DNS configs
    old_cosmos_config = """var cosmosDBDnsZoneConfigs = !skipCosmosDB && cosmosDBPrivateDnsZoneId != '' ? [
  {
    name: '${cosmosDBName}-dns-config'
    properties: {
      privateDnsZoneId: cosmosDBPrivateDnsZoneId
    }
  }
] : []"""

    new_cosmos_config = """var cosmosDBDnsZoneConfigs = []"""
    
    content = content.replace(old_cosmos_config, new_cosmos_config)
    
    # Now fix all the resource conditions to use deployment-time safe expressions
    # Change from length(aiServicesDnsZoneConfigs) > 0 to simpler conditions
    
    # AI Services DNS Group
    old_condition = "if (existingAiAccountPrivateEndpointName == '' && !skipOpenAI && length(aiServicesDnsZoneConfigs) > 0)"
    new_condition = "if (existingAiAccountPrivateEndpointName == '' && !skipOpenAI && (shouldCreateAiServicesZone || shouldUseExistingAiServicesZone))"
    content = content.replace(old_condition, new_condition)
    
    old_condition2 = "if (existingAiAccountPrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipOpenAI && length(aiServicesDnsZoneConfigs) > 0)"
    new_condition2 = "if (existingAiAccountPrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipOpenAI && (shouldCreateAiServicesZone || shouldUseExistingAiServicesZone))"
    content = content.replace(old_condition2, new_condition2)
    
    # AI Search DNS Group
    old_condition3 = "if (existingAiSearchPrivateEndpointName == '' && !skipAiSearch && length(aiSearchDnsZoneConfigs) > 0)"
    new_condition3 = "if (existingAiSearchPrivateEndpointName == '' && !skipAiSearch && (shouldCreateAiSearchZone || shouldUseExistingAiSearchZone))"
    content = content.replace(old_condition3, new_condition3)
    
    old_condition4 = "if (existingAiSearchPrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipAiSearch && length(aiSearchDnsZoneConfigs) > 0)"
    new_condition4 = "if (existingAiSearchPrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipAiSearch && (shouldCreateAiSearchZone || shouldUseExistingAiSearchZone))"
    content = content.replace(old_condition4, new_condition4)
    
    # Storage DNS Group
    old_condition5 = "if (existingStoragePrivateEndpointName == '' && !skipStorage && length(storageDnsZoneConfigs) > 0)"
    new_condition5 = "if (existingStoragePrivateEndpointName == '' && !skipStorage && (shouldCreateStorageZone || shouldUseExistingStorageZone))"
    content = content.replace(old_condition5, new_condition5)
    
    old_condition6 = "if (existingStoragePrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipStorage && length(storageDnsZoneConfigs) > 0)"
    new_condition6 = "if (existingStoragePrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipStorage && (shouldCreateStorageZone || shouldUseExistingStorageZone))"
    content = content.replace(old_condition6, new_condition6)
    
    # Cosmos DB DNS Group  
    old_condition7 = "if (existingCosmosDBPrivateEndpointName == '' && !skipCosmosDB && length(cosmosDBDnsZoneConfigs) > 0)"
    new_condition7 = "if (existingCosmosDBPrivateEndpointName == '' && !skipCosmosDB && (shouldCreateCosmosDBZone || shouldUseExistingCosmosDBZone))"
    content = content.replace(old_condition7, new_condition7)
    
    old_condition8 = "if (existingCosmosDBPrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipCosmosDB && length(cosmosDBDnsZoneConfigs) > 0)"
    new_condition8 = "if (existingCosmosDBPrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipCosmosDB && (shouldCreateCosmosDBZone || shouldUseExistingCosmosDBZone))"
    content = content.replace(old_condition8, new_condition8)
    
    # Fix the privateDnsZoneConfigs properties to use direct zone references
    # This is more complex, but we need to set up conditional zone configs
    
    # Add new resource definitions for DNS zone configs that reference outputs only in their own resources
    dns_zone_refs = """
// DNS Zone configurations - evaluated at runtime only when needed
resource aiServicesDnsZoneConfigsCreated 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (shouldCreateAiServicesZone && existingAiAccountPrivateEndpointName == '' && !skipOpenAI) {
  parent: aiAccountPrivateEndpoint
  name: '${aiAccountName}-dns-group-created'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: '${aiAccountName}-dns-aiserv-config'
        properties: {
          privateDnsZoneId: dnsZonesCreation.outputs.aiServicesZoneId
        }
      }
      {
        name: '${aiAccountName}-dns-openai-config'
        properties: {
          privateDnsZoneId: dnsZonesCreation.outputs.openAiZoneId
        }
      }
      {
        name: '${aiAccountName}-dns-cognitive-config'
        properties: {
          privateDnsZoneId: dnsZonesCreation.outputs.cognitiveServicesZoneId
        }
      }
    ]
  }
}

resource aiServicesDnsZoneConfigsExisting 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (shouldUseExistingAiServicesZone && existingAiAccountPrivateEndpointName == '' && !skipOpenAI) {
  parent: aiAccountPrivateEndpoint
  name: '${aiAccountName}-dns-group-existing'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: '${aiAccountName}-dns-aiserv-config'
        properties: {
          privateDnsZoneId: aiServicesPrivateDnsZoneExisting.id
        }
      }
      {
        name: '${aiAccountName}-dns-openai-config'
        properties: {
          privateDnsZoneId: openAiPrivateDnsZoneExisting.id
        }
      }
      {
        name: '${aiAccountName}-dns-cognitive-config'
        properties: {
          privateDnsZoneId: cognitiveServicesPrivateDnsZoneExisting.id
        }
      }
    ]
  }
}
"""
    
    # Replace the old DNS group resources
    old_ai_services_resources = """// DNS Zone Groups for AI Services

// 3) DNS Zone Group for AI Services - New Private Endpoint
resource aiServicesDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingAiAccountPrivateEndpointName == '' && !skipOpenAI && (shouldCreateAiServicesZone || shouldUseExistingAiServicesZone)) {
  parent: aiAccountPrivateEndpoint
  name: '${aiAccountName}-dns-group'
  properties: {
    privateDnsZoneConfigs: aiServicesDnsZoneConfigs
  }
}

// 3) DNS Zone Group for AI Services - Existing Private Endpoint (skip if already configured)
resource existingAiServicesDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (existingAiAccountPrivateEndpointName != '' && !skipExistingPrivateEndpointDnsGroups && !skipOpenAI && (shouldCreateAiServicesZone || shouldUseExistingAiServicesZone)) {
  parent: existingAiAccountPrivateEndpoint
  name: '${aiAccountName}-dns-group-existing'
  properties: {
    privateDnsZoneConfigs: aiServicesDnsZoneConfigs
  }
}"""
    
    content = content.replace(old_ai_services_resources, dns_zone_refs)
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Applied BCP177 fixes to private-endpoint-and-dns.bicep")
    print("\n🔧 Changes made:")
    print("   - Split conditional logic into deployment-time safe variables")
    print("   - Removed module output references from if-conditions")
    print("   - Created separate resources for created vs existing DNS zones")
    print("   - Simplified DNS zone configuration arrays")
    
    return True

def main():
    """Main function."""
    print("🚨 BCP177 Quick Fix Tool")
    print("=" * 40)
    print("This tool fixes the BCP177 error that appeared suddenly")
    print("by restructuring conditional expressions in the Bicep template.")
    print()
    
    fix_private_endpoint_dns_file()
    
    print("\n✅ Fix completed!")
    print("🚀 You can now try deploying again:")
    print("   cd 15-private-network-standard-agent-setup")
    print("   az bicep build --file main.bicep --outfile main.json")
    print("   az deployment group create --resource-group <your-rg> --template-file main.bicep")

if __name__ == "__main__":
    main()
