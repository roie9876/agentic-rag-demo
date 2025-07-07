# Delete Deployment Tab Documentation

## Overview
The **Delete Deployment** tab provides a comprehensive solution for deleting Azure AI Foundry deployments and handling complex scenarios like VNets with delegated subnets.

## Features

### 🗑️ **Smart Deletion Strategy**
- **Handles Delegations**: Automatically removes subnet delegations (like AI agent delegations)
- **Service Association Links**: Cleans up service association links that prevent subnet deletion
- **Dependencies**: Manages deletion order to avoid dependency conflicts
- **Error Recovery**: Provides detailed error messages and troubleshooting guidance

### 📋 **Deletion Modes**

#### 1. **Smart Delete (Recommended)**
- Analyzes resources and dependencies
- Removes delegations and service links first
- Deletes AI Foundry resources in correct order
- Cleans up private endpoints and DNS zones
- Finally deletes resource group

#### 2. **Force Delete Resource Group** 
- Attempts direct resource group deletion
- May fail if dependencies exist
- Useful for simple scenarios without complex networking

#### 3. **Preview Only (Dry Run)**
- Shows what would be deleted without actual deletion
- Identifies potential issues before actual deletion
- Displays deletion order and strategy

### 🔧 **Technical Implementation**

#### **Delegation Handling**
The tab specifically addresses the error:
```
Failed to delete subnet 'agent-subnet'. Error: Subnet agent-subnet is in use by 
/subscriptions/.../serviceAssociationLinks/legionservicelink and cannot be deleted.
```

**Solution Process:**
1. **Identify Delegations**: Scans all subnets for delegations and service association links
2. **Remove Delegations**: Uses `az network vnet subnet update --remove delegations`
3. **Delete Associated Resources**: Removes AI Foundry capability hosts and projects
4. **Clean Service Links**: Deletes resources that create service association links
5. **Final Cleanup**: Removes remaining resources and resource group

#### **Azure CLI Commands Used**
```bash
# Get resource groups
az group list --query "[].name" --output json

# Get resources in resource group
az resource list --resource-group <rg-name> --output json

# Get VNet subnets with delegations
az network vnet subnet list --resource-group <rg> --vnet-name <vnet> --output json

# Remove subnet delegations
az network vnet subnet update --resource-group <rg> --vnet-name <vnet> --name <subnet> --remove delegations

# Delete AI Services accounts
az cognitiveservices account delete --name <account> --resource-group <rg> --yes

# Delete private endpoints
az network private-endpoint delete --name <pe-name> --resource-group <rg> --yes

# Delete resource group
az group delete --name <rg> --yes --no-wait
```

### 🚨 **Safety Features**

#### **Confirmation Requirements**
- Checkbox confirmation for understanding permanent deletion
- Text input requiring exact resource group name
- Different confirmation levels for different deletion modes

#### **Progress Tracking**
- Real-time progress updates during deletion
- Detailed logging of all commands executed
- Success/error status for each step
- Expandable detailed logs

#### **Error Handling**
- Graceful handling of deletion failures
- Detailed error messages with potential solutions
- Continues with remaining deletions even if some fail
- Provides troubleshooting guidance

### 📊 **User Interface**

#### **Resource Group Selection**
- Dropdown list of available resource groups
- Resource analysis and display by type
- Resource count and details for each group

#### **Deletion Configuration**
- Radio button selection for deletion strategy
- Safety confirmations and text verification
- Preview mode for safe testing

#### **Progress Display**
- Color-coded progress messages (success/error/warning/info)
- Expandable detailed command logs
- Real-time status updates

### 🔍 **Common Use Cases**

#### **1. Clean Up Failed Deployments**
```
Scenario: AI Foundry deployment failed, leaving partial resources
Solution: Use Smart Delete to clean up all created resources
```

#### **2. Remove AI Agent Delegations**
```
Scenario: Cannot delete VNet due to AI agent subnet delegations
Solution: Smart Delete removes delegations before VNet deletion
```

#### **3. Complete Environment Cleanup**
```
Scenario: Need to delete entire test environment
Solution: Force Delete Resource Group for complete cleanup
```

#### **4. Preview Deletion Impact**
```
Scenario: Understand what will be deleted before proceeding
Solution: Use Preview Only mode to see deletion plan
```

### ⚠️ **Important Notes**

#### **Irreversible Action**
- All deletion operations are **permanent**
- No recovery possible after resource group deletion
- Always use Preview mode first in production

#### **Network Dependencies**
- Private endpoints may take time to fully disconnect
- DNS zone records may persist after resource deletion
- Some network resources may require manual cleanup

#### **AI Foundry Specific**
- Capability hosts must be deleted before projects
- Projects must be deleted before AI Services accounts
- Network injections (agent delegations) must be removed first

#### **Best Practices**
1. **Always Preview First**: Use dry run mode to understand impact
2. **Check Dependencies**: Review all resources in the resource group
3. **Backup Important Data**: Export any important configurations
4. **Use Smart Delete**: Recommended for AI Foundry deployments
5. **Monitor Progress**: Watch the progress logs for any issues

### 🐛 **Troubleshooting**

#### **Common Issues**

##### **"Subnet is in use" Error**
```
Error: Subnet agent-subnet is in use by serviceAssociationLinks
Solution: Use Smart Delete mode - it automatically handles this
```

##### **"Resource has dependencies" Error**
```
Error: Cannot delete resource due to existing dependencies
Solution: Smart Delete handles dependency order automatically
```

##### **"Permission denied" Error**
```
Error: Insufficient permissions to delete resources
Solution: Ensure you have Contributor role on the resource group
```

##### **"Resource not found" Error**
```
Error: Some resources already deleted or moved
Solution: Continue with deletion - this is usually harmless
```

### 📝 **Integration Notes**

The Delete Deployment tab is integrated into the AI Foundry Hub deployment interface as the 5th tab:

1. ⚙️ Configuration
2. 👀 Preview  
3. 🚀 Deploy
4. 📊 Status
5. **🗑️ Delete Deployment** ← New Tab

This provides a complete lifecycle management experience for AI Foundry deployments.
