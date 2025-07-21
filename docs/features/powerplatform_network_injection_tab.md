# PowerPlatform Network Injection Tab

## Overview

The **PowerPlatform Network** tab provides a user-friendly interface to configure PowerPlatform subnet injection for connecting to Azure private endpoints. This feature allows PowerPlatform environments to access private Azure resources like blob storage through secure network connections.

## Location

The tab is available as **"⚡ (9) PowerPlatform Network"** in the main Streamlit application at:
- Module: `app/tabs/studio_subnet_delegation_tab.py`
- Integration: Tab (9) in `agentic-rag-demo.py`

## Features

### 🔐 Dynamic Azure Subscription Management
- **Auto-detect current login**: Shows current Azure CLI login status
- **Interactive login**: One-click Azure CLI login from the UI
- **Multi-subscription support**: List and switch between subscriptions
- **Subscription persistence**: Remembers selected subscription during session

### 🌐 Dynamic Network Configuration
- **Resource Group Discovery**: Load all resource groups in subscription
- **VNet Discovery**: Load virtual networks within selected resource group
- **Subnet Discovery**: Load subnets within selected virtual network
- **Dual VNet Support**: Select primary and secondary VNets for redundancy
- **Real-time Validation**: Ensures all network components exist

### ⚡ PowerPlatform Configuration
- **Environment ID Input**: User provides PowerPlatform environment ID
- **Policy Configuration**: Customizable policy names and resource groups
- **Default Values**: Sensible defaults for enterprise policy settings

### 🚀 Script Operations (3 Operations)

#### 1. ✅ Apply Injection
- **Purpose**: Configure PowerPlatform subnet injection
- **Script**: `working_apply_powerplatform_injection.sh`
- **Actions**:
  - Creates enterprise policy
  - Removes NSGs from PowerPlatform subnets
  - Configures subnet delegations  
  - Links environment to policy
  - Verifies configuration

#### 2. 🗑️ Remove Injection
- **Purpose**: Remove PowerPlatform subnet injection
- **Script**: `working_remove_powerplatform_injection.sh`
- **Actions**:
  - Unlinks environment from policy
  - Removes subnet delegations
  - Deletes enterprise policy
  - Restores original subnet configuration

#### 3. 🔍 Verify Status
- **Purpose**: Check current injection configuration
- **Script**: `working_verify_powerplatform_injection.sh`
- **Actions**:
  - Validates policy existence
  - Checks subnet delegations
  - Verifies environment linkage
  - Reports overall status

## User Workflow

### Step 1: Azure Subscription
1. The tab auto-detects your Azure CLI login status
2. If not logged in, click **"🔄 Login to Azure"** 
3. For multiple subscriptions, click **"📋 List Subscriptions"** and select the target subscription

### Step 2: Network Configuration
1. Click **"🔄 Load Resource Groups"** to populate available resource groups
2. Select the resource group containing your VNets
3. Click **"🔄 Load VNets"** to load virtual networks
4. Select **Primary VNet** and **Secondary VNet**
5. Click **"🔄 Load Subnets"** to load available subnets
6. Select the **Subnet Name** (same subnet will be used for both VNets)

### Step 3: PowerPlatform Configuration
1. Enter your **Environment ID** (copy from PowerPlatform admin center)
2. Optionally modify **Policy Resource Group** (default: `powerplatform-enterprise-policies`)
3. Optionally modify **Policy Name** (default: `PowerPlatformSubnetInjectionPolicy-Europe`)

### Step 4: Execute Operations
Choose from three tabs based on your needs:

#### Apply Injection Tab
- Review the **Configuration Summary**
- Click **"🚀 Apply Injection"** to execute
- Monitor real-time script output
- Wait for success confirmation

#### Remove Injection Tab  
- Click **"🗑️ Remove Injection"** to execute
- Monitor real-time script output
- Wait for completion confirmation

#### Verify Status Tab
- Click **"🔍 Verify Status"** to check current state
- Review verification output
- Confirm configuration status

## Technical Features

### 🔧 Dynamic Parameter Injection
The tab dynamically modifies the original scripts by replacing hardcoded values with user inputs:

```bash
# Original hardcoded values
RESOURCE_GROUP="private-rg"
VNET_PRIMARY="PowerPlatform-Primary-vNET"
VNET_SECONDARY="PowerPlatform-Secondart-vNET"
SUBNET_NAME="default"
ENV_ID="b98e9fde-ed33-e9cb-b7c7-b79e43946c48"
POLICY_RESOURCE_GROUP="powerplatform-enterprise-policies"
POLICY_NAME="PowerPlatformSubnetInjectionPolicy-Europe"

# Dynamically replaced with user selections
RESOURCE_GROUP="{user_selected_resource_group}"
VNET_PRIMARY="{user_selected_primary_vnet}"
VNET_SECONDARY="{user_selected_secondary_vnet}"
SUBNET_NAME="{user_selected_subnet}"
ENV_ID="{user_entered_env_id}"
POLICY_RESOURCE_GROUP="{user_configured_policy_rg}"
POLICY_NAME="{user_configured_policy_name}"
```

### 📊 Real-time Output Streaming
- Scripts run asynchronously with live output display
- Output is streamed in real-time to the UI
- Full output is stored in session state
- Error handling with return codes

### 💾 Session State Management
- Caches Azure resources to avoid repeated API calls
- Remembers user selections during session
- Stores script output for reference
- Tracks last operation timestamp

### 🛡️ Security & Safety
- Temporary script files are automatically cleaned up
- Scripts run with user's current Azure CLI authentication
- No hardcoded credentials or sensitive data
- Proper error handling and validation

## Prerequisites

### Azure CLI Setup
```bash
# Install Azure CLI (if not already installed)
curl -sL https://aka.ms/InstallAzureCLIMacOS | bash

# Login to Azure
az login

# Verify login
az account show
```

### PowerPlatform Environment ID
To get your PowerPlatform Environment ID:
1. Go to [PowerPlatform Admin Center](https://admin.powerplatform.microsoft.com/)
2. Navigate to **Environments**
3. Select your environment
4. Copy the **Environment ID** from the URL or settings

### Network Prerequisites
- Azure VNets must exist in the target resource group
- Subnets must be available for delegation
- User must have sufficient permissions for:
  - Creating enterprise policies
  - Modifying subnet delegations
  - Managing network resources

## Troubleshooting

### Common Issues

#### "Not logged in to Azure CLI"
- **Solution**: Click the "🔄 Login to Azure" button
- **Alternative**: Run `az login` in terminal before using the app

#### "Failed to load resource groups"
- **Cause**: Insufficient permissions or network connectivity
- **Solution**: Verify Azure CLI login and permissions

#### "No VNets found"
- **Cause**: Selected resource group has no virtual networks
- **Solution**: Verify resource group selection or create VNets

#### "Script execution failed"
- **Cause**: Multiple possible causes (permissions, network, etc.)
- **Solution**: Review the script output for specific error messages

### Debugging
- All script output is displayed in real-time
- Session state stores full output for reference
- Check Azure portal for resource creation status
- Verify PowerPlatform environment ID is correct

## Architecture Compliance

This implementation follows the project's modular architecture guidelines:

### ✅ Follows Architecture Standards
- **Separate module**: Located in `app/tabs/` as per guidelines
- **Clean imports**: Main file only imports and calls the renderer
- **Type hints**: Full type annotations throughout
- **Documentation**: Comprehensive module documentation
- **Error handling**: Robust error handling and user feedback
- **Session state**: Proper session state management

### ✅ Integration Pattern
```python
# In agentic-rag-demo.py - minimal integration
with tab_studio_subnet:
    from app.tabs.studio_subnet_delegation_tab import render_studio_subnet_delegation_tab
    render_studio_subnet_delegation_tab(
        session_state=st.session_state
    )
```

### ✅ No Main File Bloat  
- All logic is contained within the module
- Main file only handles tab orchestration
- Follows the established pattern of other tabs

## Future Enhancements

- **Configuration Templates**: Save/load common configurations
- **Batch Operations**: Apply to multiple environments
- **Advanced Monitoring**: Real-time status monitoring
- **Integration Validation**: Test connectivity after configuration
- **Audit Logging**: Track all configuration changes
