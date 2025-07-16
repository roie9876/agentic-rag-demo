# AI Foundry Subnet Delegation Validation

## Overview
This document validates that the AI Foundry deployment templates properly implement subnet delegation for `Microsoft.App/environments` when using existing VNets.

## ✅ **Current Implementation Status**

### **1. New VNet Creation** ✅ CORRECT
- **File**: `modules-network-secured/vnet.bicep`
- **Status**: ✅ Properly implements delegation
- **Code**:
```bicep
delegations: [
  {
    name: 'Microsoft.app/environments'
    properties: {
      serviceName: 'Microsoft.App/environments'
    }
  }
]
```

### **2. Existing VNet + New Subnets** ✅ CORRECT
- **File**: `modules-network-secured/existing-vnet-new-subnets.bicep`
- **Status**: ✅ Properly implements delegation
- **Code**:
```bicep
delegations: [
  {
    name: 'Microsoft.app/environments'
    properties: {
      serviceName: 'Microsoft.App/environments'
    }
  }
]
```

### **3. Existing VNet + Existing Subnets** ⚠️ VALIDATION NEEDED
- **File**: `modules-network-secured/existing-vnet.bicep`
- **Status**: ⚠️ Assumes delegation exists but doesn't validate
- **Issue**: No validation that existing agent subnet has required delegation

## 🔧 **Enhancement Added**

### **Validation Script** 
Created `tests/diagnostics/validate_subnet_delegation.sh`:
```bash
./tests/diagnostics/validate_subnet_delegation.sh \
  --vnet-name my-vnet \
  --vnet-rg my-rg \
  --subnet-name agent-subnet
```

### **Validation Bicep Module**
Created `tests/diagnostics/validate_subnet_delegation.bicep` for deployment-time validation.

### **Enhanced Existing VNet Module**
Added validation to `existing-vnet.bicep` to fail deployment if delegation is missing.

## 📋 **Deployment Scenarios**

| Scenario | VNet | Subnets | Delegation | Status |
|----------|------|---------|------------|--------|
| 1 | New | New | ✅ Auto-created | Works |
| 2 | Existing | New | ✅ Auto-created | Works |
| 3 | Existing | Existing | ⚠️ Manual required | **Needs validation** |

## 🎯 **Recommendations**

### **For Users (Existing VNet + Existing Subnets)**
1. **Before deployment**, validate your agent subnet has delegation:
```bash
az network vnet subnet show \
  --vnet-name YOUR_VNET \
  --resource-group YOUR_RG \
  --name YOUR_AGENT_SUBNET \
  --query "delegations[].serviceName"
```

2. **If missing**, add delegation:
```bash
az network vnet subnet update \
  --vnet-name YOUR_VNET \
  --resource-group YOUR_RG \
  --name YOUR_AGENT_SUBNET \
  --delegations Microsoft.App/environments
```

3. **Use the validation script**:
```bash
./tests/diagnostics/validate_subnet_delegation.sh \
  --vnet-name YOUR_VNET \
  --vnet-rg YOUR_RG \
  --subnet-name YOUR_AGENT_SUBNET
```

### **For Developers**
- Consider integrating validation into the main deployment template
- Add pre-deployment checks in deployment scripts
- Update documentation to emphasize delegation requirements

## 📚 **Documentation References**

From `15-private-network-standard-agent-setup/README.md`:
> **Note:** If you bring your own VNET for this template, ensure the subnet for Agents has the correct subnet delegation to `Microsoft.App/environments`. If you have not specified the delegated subnet, the template will complete this for you.

## ✅ **Conclusion**

The AI Foundry deployment code **DOES** properly implement subnet delegation for Microsoft.App/environments in most scenarios. The only gap is validation when using existing VNets with existing subnets, which has been addressed with the new validation tools.

**Action Required**: Users deploying with existing VNets and existing subnets should validate delegation manually before deployment.
