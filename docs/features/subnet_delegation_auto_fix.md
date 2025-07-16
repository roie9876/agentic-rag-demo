# AI Foundry Subnet Delegation Auto-Fix Feature

## 🎯 Overview
This enhancement automatically adds the required `Microsoft.App/environments` delegation to existing agent subnets when deploying AI Foundry with existing VNets and existing subnets.

## 🚀 New Capabilities

### **1. Auto-Fix Shell Script** ✨
```bash
# Validate and auto-fix delegation
./tests/diagnostics/validate_subnet_delegation.sh \
  --vnet-name my-vnet \
  --vnet-rg my-rg \
  --subnet-name agent-subnet \
  --auto-fix
```

### **2. Bicep Auto-Fix Module** ✨
```bash
# Deploy with Bicep auto-fix
./tests/diagnostics/deploy_subnet_delegation_fix.sh \
  --vnet-name my-vnet \
  --vnet-rg my-rg \
  --subnet-name agent-subnet
```

### **3. Enhanced Main Deployment** ✨
New parameter in `main.bicep`:
```bicep
@description('Automatically add Microsoft.App/environments delegation to existing agent subnet if missing')
param autoAddDelegationToExistingSubnet bool = true
```

## 📋 Usage Scenarios

### **Scenario 1: Shell Script Auto-Fix**
Perfect for pre-deployment validation and fixing:

```bash
# Check if delegation exists (no changes)
./tests/diagnostics/validate_subnet_delegation.sh \
  --vnet-name production-vnet \
  --vnet-rg production-rg \
  --subnet-name ai-agent-subnet

# Auto-fix if delegation is missing
./tests/diagnostics/validate_subnet_delegation.sh \
  --vnet-name production-vnet \
  --vnet-rg production-rg \
  --subnet-name ai-agent-subnet \
  --auto-fix
```

### **Scenario 2: Bicep Deployment Auto-Fix**
Integrated into the deployment process:

```bash
# Deploy auto-fix using Bicep
./tests/diagnostics/deploy_subnet_delegation_fix.sh \
  --vnet-name production-vnet \
  --vnet-rg production-rg \
  --subnet-name ai-agent-subnet
```

### **Scenario 3: Main AI Foundry Deployment**
Automatic delegation handling during AI Foundry deployment:

```bash
az deployment group create \
  --resource-group my-rg \
  --template-file main.bicep \
  --parameters \
    existingVnetResourceId="/subscriptions/.../virtualNetworks/my-vnet" \
    agentSubnetName="agent-subnet" \
    createSubnetsInExistingVnet=false \
    autoAddDelegationToExistingSubnet=true
```

## 🔧 How It Works

### **Detection Logic**
```bicep
var hasDelegation = contains(existingAgentSubnet.properties, 'delegations') && length(existingAgentSubnet.properties.delegations) > 0
var hasCorrectDelegation = hasDelegation && contains(string(existingAgentSubnet.properties.delegations), 'Microsoft.App/environments')
```

### **Auto-Fix Logic**
```bicep
var needsUpdate = autoAddDelegation && !hasCorrectDelegation
var updatedDelegations = needsUpdate ? union(currentDelegations, [requiredDelegation]) : currentDelegations
```

### **Preservation of Existing Properties**
The auto-fix preserves all existing subnet properties:
- Address prefix
- Network Security Group
- Route Table  
- Service Endpoints
- Private Endpoint Policies
- Other delegations (merged with required delegation)

## 📁 New Files Created

### **Validation & Auto-Fix Scripts**
- `tests/diagnostics/validate_subnet_delegation.sh` - Shell script with auto-fix
- `tests/diagnostics/deploy_subnet_delegation_fix.sh` - Bicep deployment script
- `tests/diagnostics/validate_subnet_delegation.bicep` - Standalone validation module

### **Enhanced Bicep Modules**
- `modules-network-secured/existing-vnet-auto-delegate.bicep` - Enhanced existing VNet module
- Updated `modules-network-secured/network-agent-vnet.bicep` - Uses auto-delegate module
- Updated `main.bicep` - Added autoAddDelegationToExistingSubnet parameter

### **Documentation**
- `docs/technical/ai_foundry_subnet_delegation_analysis.md` - Technical analysis
- `docs/features/subnet_delegation_auto_fix.md` - This feature documentation

## ✅ Benefits

### **1. Zero Manual Intervention**
- Automatically detects missing delegation
- Adds delegation without breaking existing configuration
- Preserves all other subnet properties

### **2. Flexible Deployment Options**
- **Shell Script**: Pre-deployment validation and fixing
- **Bicep Module**: Integrated deployment-time fixing  
- **Main Template**: Seamless AI Foundry deployment

### **3. Safety & Validation**
- Non-destructive: preserves existing delegations and properties
- Validation: confirms delegation exists before proceeding
- Rollback-friendly: standard Azure deployment rollback

### **4. Clear Feedback**
- Detailed output showing what was changed
- Validation messages explaining the current state
- Error handling with actionable guidance

## 🎯 Migration Path

### **For Existing Deployments**
1. **Before deployment**: Run validation script
2. **If delegation missing**: Use auto-fix
3. **Deploy AI Foundry**: Proceed with confidence

### **For New Deployments**
1. **Use enhanced template**: Set `autoAddDelegationToExistingSubnet=true`
2. **Deploy normally**: Auto-fix happens automatically
3. **Monitor output**: Check delegation status in deployment results

## 🔍 Validation Commands

### **Check Current State**
```bash
az network vnet subnet show \
  --vnet-name my-vnet \
  --resource-group my-rg \
  --name agent-subnet \
  --query 'delegations[].serviceName'
```

### **Manual Delegation Addition (if needed)**
```bash
az network vnet subnet update \
  --vnet-name my-vnet \
  --resource-group my-rg \
  --name agent-subnet \
  --delegations Microsoft.App/environments
```

## 🚨 Important Notes

### **Permissions Required**
- `Microsoft.Network/virtualNetworks/subnets/write` permission
- Access to the VNet's resource group
- Appropriate Azure RBAC roles (Network Contributor or custom)

### **Compatibility**
- Works with existing VNets in same or different subscriptions
- Preserves existing delegations (additive, not destructive)
- Compatible with Network Security Groups and Route Tables

### **Error Handling**
- Graceful failure if permissions are insufficient
- Clear error messages for troubleshooting
- Retry logic in shell scripts for transient failures

## 🎉 Result
No more manual delegation setup! The AI Foundry deployment now automatically ensures the required `Microsoft.App/environments` delegation exists on agent subnets, making the "existing VNet + existing subnet" scenario as smooth as creating new infrastructure.
