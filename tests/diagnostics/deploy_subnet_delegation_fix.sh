#!/bin/bash

# AI Foundry Subnet Delegation Auto-Fix Deployment Script
# Uses Bicep to automatically add Microsoft.App/environments delegation to existing subnets

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
VNET_NAME=""
VNET_RESOURCE_GROUP=""
AGENT_SUBNET_NAME="agent-subnet"
SUBSCRIPTION_ID=""
DEPLOYMENT_NAME="subnet-delegation-fix-$(date +%s)"
AUTO_ADD_DELEGATION=true

# Help function
show_help() {
    echo "Usage: $0 --vnet-name VNET_NAME --vnet-rg RESOURCE_GROUP [OPTIONS]"
    echo ""
    echo "Parameters:"
    echo "  --vnet-name       Name of the existing virtual network"
    echo "  --vnet-rg         Resource group containing the virtual network"
    echo "  --subnet-name     Name of the agent subnet (default: agent-subnet)"
    echo "  --subscription    Azure subscription ID (default: current subscription)"
    echo "  --no-auto-fix     Disable automatic delegation addition (validation only)"
    echo "  --deployment-name Custom deployment name (default: auto-generated)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Auto-fix delegation (default behavior)"
    echo "  $0 --vnet-name my-vnet --vnet-rg my-rg --subnet-name my-agent-subnet"
    echo ""
    echo "  # Validation only (no changes)"
    echo "  $0 --vnet-name my-vnet --vnet-rg my-rg --no-auto-fix"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --vnet-name)
            VNET_NAME="$2"
            shift 2
            ;;
        --vnet-rg)
            VNET_RESOURCE_GROUP="$2"
            shift 2
            ;;
        --subnet-name)
            AGENT_SUBNET_NAME="$2"
            shift 2
            ;;
        --subscription)
            SUBSCRIPTION_ID="$2"
            shift 2
            ;;
        --no-auto-fix)
            AUTO_ADD_DELEGATION=false
            shift 1
            ;;
        --deployment-name)
            DEPLOYMENT_NAME="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown parameter $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$VNET_NAME" || -z "$VNET_RESOURCE_GROUP" ]]; then
    echo -e "${RED}Error: --vnet-name and --vnet-rg are required parameters${NC}"
    show_help
    exit 1
fi

# Set subscription if provided
if [[ -n "$SUBSCRIPTION_ID" ]]; then
    echo -e "${BLUE}Setting subscription to: $SUBSCRIPTION_ID${NC}"
    az account set --subscription "$SUBSCRIPTION_ID"
fi

# Get current subscription
CURRENT_SUBSCRIPTION=$(az account show --query id -o tsv)
echo -e "${BLUE}Using subscription: $CURRENT_SUBSCRIPTION${NC}"

echo -e "${PURPLE}🚀 AI Foundry Subnet Delegation Auto-Fix using Bicep${NC}"
echo "VNet: $VNET_NAME"
echo "Resource Group: $VNET_RESOURCE_GROUP"
echo "Agent Subnet: $AGENT_SUBNET_NAME"
echo "Auto-fix: $AUTO_ADD_DELEGATION"
echo "Deployment: $DEPLOYMENT_NAME"
echo ""

# Check if required files exist
BICEP_FILE="./tests/diagnostics/validate_subnet_delegation.bicep"
if [[ ! -f "$BICEP_FILE" ]]; then
    echo -e "${RED}❌ ERROR: Bicep template not found: $BICEP_FILE${NC}"
    echo -e "${YELLOW}💡 Make sure you're running this from the project root directory${NC}"
    exit 1
fi

echo -e "${BLUE}🔍 Deploying Bicep template for subnet validation and auto-fix...${NC}"

# Create deployment
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$VNET_RESOURCE_GROUP" \
    --name "$DEPLOYMENT_NAME" \
    --template-file "$BICEP_FILE" \
    --parameters \
        vnetName="$VNET_NAME" \
        vnetResourceGroupName="$VNET_RESOURCE_GROUP" \
        agentSubnetName="$AGENT_SUBNET_NAME" \
        autoAddDelegation="$AUTO_ADD_DELEGATION" \
    --query '{
        provisioningState: properties.provisioningState,
        isValid: properties.outputs.isValid.value,
        hasCorrectDelegation: properties.outputs.hasCorrectDelegation.value,
        wasUpdated: properties.outputs.wasUpdated.value,
        validationMessage: properties.outputs.validationMessage.value,
        finalDelegations: properties.outputs.finalDelegations.value
    }' \
    --output json)

if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ ERROR: Bicep deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Bicep deployment completed successfully${NC}"
echo ""

# Parse deployment output
PROVISIONING_STATE=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.provisioningState')
IS_VALID=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.isValid')
HAS_CORRECT_DELEGATION=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.hasCorrectDelegation')
WAS_UPDATED=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.wasUpdated')
VALIDATION_MESSAGE=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.validationMessage')
FINAL_DELEGATIONS=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.finalDelegations')

echo -e "${BLUE}📋 Deployment Results:${NC}"
echo "Provisioning State: $PROVISIONING_STATE"
echo "Validation Result: $VALIDATION_MESSAGE"
echo "Final Delegations: $FINAL_DELEGATIONS"
echo ""

if [[ "$WAS_UPDATED" == "true" ]]; then
    echo -e "${GREEN}🎯 SUCCESS: Microsoft.App/environments delegation was automatically added!${NC}"
    echo -e "${GREEN}✅ AI Foundry deployment can now proceed with this subnet${NC}"
elif [[ "$HAS_CORRECT_DELEGATION" == "true" ]]; then
    echo -e "${GREEN}✅ SUCCESS: Subnet already has the correct delegation${NC}"
    echo -e "${GREEN}🎯 AI Foundry deployment can proceed with this subnet${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: Subnet delegation was not updated${NC}"
    if [[ "$AUTO_ADD_DELEGATION" == "false" ]]; then
        echo -e "${BLUE}💡 Auto-fix was disabled. Run with --auto-fix to automatically add delegation${NC}"
    else
        echo -e "${RED}❌ Auto-fix failed. Check the deployment logs for details${NC}"
    fi
fi

echo ""
echo -e "${BLUE}🔍 To verify the current state, run:${NC}"
echo "az network vnet subnet show \\"
echo "  --vnet-name '$VNET_NAME' \\"
echo "  --resource-group '$VNET_RESOURCE_GROUP' \\"
echo "  --name '$AGENT_SUBNET_NAME' \\"
echo "  --query 'delegations[].serviceName'"
