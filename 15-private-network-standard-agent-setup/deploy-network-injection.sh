#!/bin/bash

# Deploy AI Foundry Account with Network Injection
# This script deploys only the AI Foundry account with network injection enabled

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/deploy-network-injection-only.bicep"
PARAMETERS_FILE="$SCRIPT_DIR/deploy-network-injection-only.parameters.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AI Foundry Network Injection Deployment ===${NC}"
echo

# Check if user is logged in to Azure
echo -e "${YELLOW}Checking Azure CLI authentication...${NC}"
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: You are not logged in to Azure CLI${NC}"
    echo "Please run: az login"
    exit 1
fi

# Get current subscription info
SUBSCRIPTION_ID=$(az account show --query id --output tsv)
SUBSCRIPTION_NAME=$(az account show --query name --output tsv)
echo -e "${GREEN}✓ Authenticated to subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)${NC}"

# Prompt for resource group
echo
read -p "Enter the resource group name where you want to deploy the AI Foundry account: " RESOURCE_GROUP

# Check if resource group exists
echo -e "${YELLOW}Checking if resource group exists...${NC}"
if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    echo -e "${RED}Error: Resource group '$RESOURCE_GROUP' does not exist${NC}"
    echo "Please create it first or use an existing resource group."
    exit 1
fi

echo -e "${GREEN}✓ Resource group '$RESOURCE_GROUP' exists${NC}"

# Prompt for VNet information
echo
echo -e "${YELLOW}Network Configuration:${NC}"
read -p "Enter your VNet resource group name: " VNET_RG
read -p "Enter your VNet name: " VNET_NAME
read -p "Enter the agent subnet name (default: snet-agent): " SUBNET_NAME
SUBNET_NAME=${SUBNET_NAME:-snet-agent}

# Construct VNet resource ID
VNET_RESOURCE_ID="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$VNET_RG/providers/Microsoft.Network/virtualNetworks/$VNET_NAME"

# Verify VNet exists
echo -e "${YELLOW}Verifying VNet and subnet...${NC}"
if ! az network vnet show --resource-group "$VNET_RG" --name "$VNET_NAME" &>/dev/null; then
    echo -e "${RED}Error: VNet '$VNET_NAME' not found in resource group '$VNET_RG'${NC}"
    exit 1
fi

if ! az network vnet subnet show --resource-group "$VNET_RG" --vnet-name "$VNET_NAME" --name "$SUBNET_NAME" &>/dev/null; then
    echo -e "${RED}Error: Subnet '$SUBNET_NAME' not found in VNet '$VNET_NAME'${NC}"
    echo "Please ensure the subnet exists and is delegated to 'Microsoft.MachineLearningServices/workspaces'"
    exit 1
fi

echo -e "${GREEN}✓ VNet and subnet verified${NC}"

# Check subnet delegation
DELEGATION=$(az network vnet subnet show --resource-group "$VNET_RG" --vnet-name "$VNET_NAME" --name "$SUBNET_NAME" --query "delegations[0].serviceName" --output tsv)
if [[ "$DELEGATION" != "Microsoft.MachineLearningServices/workspaces" ]]; then
    echo -e "${YELLOW}Warning: Subnet '$SUBNET_NAME' is not delegated to 'Microsoft.MachineLearningServices/workspaces'${NC}"
    echo "Network injection may not work properly. Please delegate the subnet first."
    read -p "Do you want to continue anyway? (y/N): " continue_anyway
    if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
else
    echo -e "${GREEN}✓ Subnet is properly delegated for AI agents${NC}"
fi

# Create temporary parameters file with actual values
TEMP_PARAMS_FILE=$(mktemp)
jq --arg vnetId "$VNET_RESOURCE_ID" \
   --arg subnetName "$SUBNET_NAME" \
   '.parameters.vnetResourceId.value = $vnetId | .parameters.agentSubnetName.value = $subnetName' \
   "$PARAMETERS_FILE" > "$TEMP_PARAMS_FILE"

echo
echo -e "${BLUE}Deployment Configuration:${NC}"
echo "Template: $TEMPLATE_FILE"
echo "Resource Group: $RESOURCE_GROUP"
echo "VNet: $VNET_NAME"
echo "Agent Subnet: $SUBNET_NAME"
echo "Network Injection: Enabled"

# Validate the deployment
echo
echo -e "${YELLOW}Validating Bicep template...${NC}"
VALIDATION_RESULT=$(az deployment group validate \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$TEMPLATE_FILE" \
    --parameters "@$TEMP_PARAMS_FILE" \
    --query "error" --output tsv 2>/dev/null || echo "validation_failed")

if [[ "$VALIDATION_RESULT" != "null" && "$VALIDATION_RESULT" != "" ]]; then
    echo -e "${RED}Template validation failed:${NC}"
    az deployment group validate \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$TEMPLATE_FILE" \
        --parameters "@$TEMP_PARAMS_FILE"
    rm -f "$TEMP_PARAMS_FILE"
    exit 1
fi

echo -e "${GREEN}✓ Template validation passed${NC}"

# Confirm deployment
echo
read -p "Do you want to proceed with the deployment? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    rm -f "$TEMP_PARAMS_FILE"
    exit 0
fi

# Deploy
echo
echo -e "${YELLOW}Starting deployment...${NC}"
DEPLOYMENT_NAME="ai-foundry-netinject-$(date +%Y%m%d-%H%M%S)"

az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$TEMPLATE_FILE" \
    --parameters "@$TEMP_PARAMS_FILE" \
    --name "$DEPLOYMENT_NAME" \
    --verbose

if [[ $? -eq 0 ]]; then
    echo
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo
    echo -e "${BLUE}Deployment outputs:${NC}"
    az deployment group show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --query properties.outputs \
        --output table
    
    echo
    echo -e "${GREEN}🎉 Your AI Foundry account is now deployed with network injection enabled!${NC}"
    echo -e "${YELLOW}Agents deployed in this account will use the subnet: $SUBNET_NAME${NC}"
else
    echo -e "${RED}❌ Deployment failed${NC}"
    rm -f "$TEMP_PARAMS_FILE"
    exit 1
fi

# Cleanup
rm -f "$TEMP_PARAMS_FILE"
