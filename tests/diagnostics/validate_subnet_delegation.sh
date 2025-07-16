#!/bin/bash

# Subnet Delegation Validation and Auto-Fix Script for AI Foundry
# This script validates that an existing agent subnet has the required Microsoft.App/environments delegation
# If delegation is missing, it can automatically add it

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VNET_NAME=""
VNET_RESOURCE_GROUP=""
AGENT_SUBNET_NAME="agent-subnet"
SUBSCRIPTION_ID=""
AUTO_FIX=false

# Help function
show_help() {
    echo "Usage: $0 --vnet-name VNET_NAME --vnet-rg RESOURCE_GROUP [--subnet-name SUBNET_NAME] [--subscription SUBSCRIPTION_ID] [--auto-fix]"
    echo ""
    echo "Parameters:"
    echo "  --vnet-name       Name of the existing virtual network"
    echo "  --vnet-rg         Resource group containing the virtual network"
    echo "  --subnet-name     Name of the agent subnet (default: agent-subnet)"
    echo "  --subscription    Azure subscription ID (default: current subscription)"
    echo "  --auto-fix        Automatically add Microsoft.App/environments delegation if missing"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Validate only (no changes)"
    echo "  $0 --vnet-name my-vnet --vnet-rg my-rg --subnet-name my-agent-subnet"
    echo ""
    echo "  # Validate and auto-fix if needed"
    echo "  $0 --vnet-name my-vnet --vnet-rg my-rg --subnet-name my-agent-subnet --auto-fix"
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
        --auto-fix)
            AUTO_FIX=true
            shift 1
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

echo -e "${BLUE}🔍 Validating subnet delegation for AI Foundry...${NC}"
echo "VNet: $VNET_NAME"
echo "Resource Group: $VNET_RESOURCE_GROUP"
echo "Agent Subnet: $AGENT_SUBNET_NAME"
echo "Auto-fix: $AUTO_FIX"
echo ""

# Check if VNet exists
echo -e "${BLUE}📋 Checking if VNet exists...${NC}"
if ! az network vnet show --name "$VNET_NAME" --resource-group "$VNET_RESOURCE_GROUP" &>/dev/null; then
    echo -e "${RED}❌ ERROR: VNet '$VNET_NAME' not found in resource group '$VNET_RESOURCE_GROUP'${NC}"
    exit 1
fi
echo -e "${GREEN}✅ VNet exists${NC}"

# Check if agent subnet exists
echo -e "${BLUE}📋 Checking if agent subnet exists...${NC}"
if ! az network vnet subnet show --vnet-name "$VNET_NAME" --resource-group "$VNET_RESOURCE_GROUP" --name "$AGENT_SUBNET_NAME" &>/dev/null; then
    echo -e "${RED}❌ ERROR: Agent subnet '$AGENT_SUBNET_NAME' not found in VNet '$VNET_NAME'${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Agent subnet exists${NC}"

# Get subnet delegation information
echo -e "${BLUE}🔍 Checking subnet delegations...${NC}"
DELEGATIONS=$(az network vnet subnet show \
    --vnet-name "$VNET_NAME" \
    --resource-group "$VNET_RESOURCE_GROUP" \
    --name "$AGENT_SUBNET_NAME" \
    --query "delegations[].serviceName" \
    --output tsv)

if [[ -z "$DELEGATIONS" ]]; then
    echo -e "${RED}❌ CRITICAL: No delegations found on agent subnet '$AGENT_SUBNET_NAME'${NC}"
    echo -e "${YELLOW}📝 Required delegation: Microsoft.App/environments${NC}"
    
    if [[ "$AUTO_FIX" == "true" ]]; then
        echo -e "${BLUE}🔧 Auto-fix enabled. Adding Microsoft.App/environments delegation...${NC}"
        
        if az network vnet subnet update \
            --vnet-name "$VNET_NAME" \
            --resource-group "$VNET_RESOURCE_GROUP" \
            --name "$AGENT_SUBNET_NAME" \
            --delegations Microsoft.App/environments; then
            
            echo -e "${GREEN}✅ SUCCESS: Microsoft.App/environments delegation added to subnet '$AGENT_SUBNET_NAME'${NC}"
            echo -e "${GREEN}🎯 AI Foundry deployment can now proceed with this subnet${NC}"
            exit 0
        else
            echo -e "${RED}❌ ERROR: Failed to add delegation to subnet${NC}"
            echo -e "${YELLOW}💡 You may need to check permissions or try manually${NC}"
            exit 1
        fi
    else
        echo ""
        echo -e "${BLUE}🔧 To fix this issue, run:${NC}"
        echo "az network vnet subnet update \\"
        echo "  --vnet-name '$VNET_NAME' \\"
        echo "  --resource-group '$VNET_RESOURCE_GROUP' \\"
        echo "  --name '$AGENT_SUBNET_NAME' \\"
        echo "  --delegations Microsoft.App/environments"
        echo ""
        echo -e "${BLUE}🚀 Or run this script with --auto-fix flag to automatically add the delegation${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}📋 Found delegations:${NC}"
echo "$DELEGATIONS"

# Check for required delegation
if echo "$DELEGATIONS" | grep -q "Microsoft.App/environments"; then
    echo -e "${GREEN}✅ SUCCESS: Agent subnet has the required Microsoft.App/environments delegation${NC}"
    echo -e "${GREEN}🎯 AI Foundry deployment can proceed with this existing VNet and subnet${NC}"
    exit 0
else
    echo -e "${RED}❌ CRITICAL: Agent subnet is missing the required Microsoft.App/environments delegation${NC}"
    echo -e "${YELLOW}📝 Required delegation: Microsoft.App/environments${NC}"
    echo -e "${YELLOW}📝 Current delegations: $DELEGATIONS${NC}"
    
    if [[ "$AUTO_FIX" == "true" ]]; then
        echo -e "${BLUE}🔧 Auto-fix enabled. Adding Microsoft.App/environments delegation...${NC}"
        
        # Get current delegations and add the required one
        CURRENT_DELEGATIONS_ARRAY=$(az network vnet subnet show \
            --vnet-name "$VNET_NAME" \
            --resource-group "$VNET_RESOURCE_GROUP" \
            --name "$AGENT_SUBNET_NAME" \
            --query "delegations[].serviceName" \
            --output json)
        
        # Create the new delegations array (preserve existing + add required)
        NEW_DELEGATIONS="Microsoft.App/environments"
        if [[ "$DELEGATIONS" != "" ]]; then
            # If there are existing delegations, we need to preserve them
            echo -e "${YELLOW}⚠️  WARNING: Existing delegations found. This will replace them with Microsoft.App/environments only.${NC}"
            echo -e "${YELLOW}   Current delegations: $DELEGATIONS${NC}"
            echo -e "${YELLOW}   Proceeding with Microsoft.App/environments delegation only...${NC}"
        fi
        
        if az network vnet subnet update \
            --vnet-name "$VNET_NAME" \
            --resource-group "$VNET_RESOURCE_GROUP" \
            --name "$AGENT_SUBNET_NAME" \
            --delegations Microsoft.App/environments; then
            
            echo -e "${GREEN}✅ SUCCESS: Microsoft.App/environments delegation added to subnet '$AGENT_SUBNET_NAME'${NC}"
            echo -e "${GREEN}🎯 AI Foundry deployment can now proceed with this subnet${NC}"
            exit 0
        else
            echo -e "${RED}❌ ERROR: Failed to add delegation to subnet${NC}"
            echo -e "${YELLOW}💡 You may need to check permissions or try manually${NC}"
            exit 1
        fi
    else
        echo ""
        echo -e "${BLUE}🔧 To fix this issue, run:${NC}"
        echo "az network vnet subnet update \\"
        echo "  --vnet-name '$VNET_NAME' \\"
        echo "  --resource-group '$VNET_RESOURCE_GROUP' \\"
        echo "  --name '$AGENT_SUBNET_NAME' \\"
        echo "  --delegations Microsoft.App/environments"
        echo ""
        echo -e "${BLUE}🚀 Or run this script with --auto-fix flag to automatically add the delegation${NC}"
        exit 1
    fi
fi
