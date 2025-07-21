#!/bin/bash

echo "🔍 PowerPlatform Subnet Injection Verification Script"
echo "======================================================"

# Variables - Update these as needed
RESOURCE_GROUP="private-rg"
VNET_PRIMARY="PowerPlatform-Primary-vNET"
VNET_SECONDARY="PowerPlatform-Secondart-vNET"
SUBNET_NAME="default"
ENV_ID="b98e9fde-ed33-e9cb-b7c7-b79e43946c48"
POLICY_RESOURCE_GROUP="powerplatform-enterprise-policies"
POLICY_NAME="PowerPlatformSubnetInjectionPolicy-Europe"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "Configuration being verified:"
echo "  Environment ID: $ENV_ID"
echo "  Policy Name: $POLICY_NAME"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Primary VNet: $VNET_PRIMARY"
echo "  Secondary VNet: $VNET_SECONDARY"
echo ""

# Initialize status counters
TOTAL_CHECKS=0
PASSED_CHECKS=0

# Function to increment check counters
check_result() {
    local status=$1
    local message=$2
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ "$status" = "PASS" ]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        echo -e "${GREEN}✅ PASS: $message${NC}"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  WARN: $message${NC}"
    else
        echo -e "${RED}❌ FAIL: $message${NC}"
    fi
}

echo -e "${CYAN}===================================================${NC}"
echo -e "${CYAN}1. ENTERPRISE POLICY VERIFICATION${NC}"
echo -e "${CYAN}===================================================${NC}"

# Check if policy exists
echo "Checking if enterprise policy exists..."
POLICY_EXISTS=$(az resource show --name "$POLICY_NAME" --resource-group "$POLICY_RESOURCE_GROUP" --resource-type "Microsoft.PowerPlatform/enterprisePolicies" --query 'name' --output tsv 2>/dev/null)

if [ -n "$POLICY_EXISTS" ]; then
    check_result "PASS" "Enterprise policy '$POLICY_NAME' exists"
    
    # Get policy details
    POLICY_DETAILS=$(az resource show --name "$POLICY_NAME" --resource-group "$POLICY_RESOURCE_GROUP" --resource-type "Microsoft.PowerPlatform/enterprisePolicies" --output json 2>/dev/null)
    
    # Check policy location
    POLICY_LOCATION=$(echo "$POLICY_DETAILS" | jq -r '.location')
    if [ "$POLICY_LOCATION" = "europe" ]; then
        check_result "PASS" "Policy location is 'europe'"
    else
        check_result "FAIL" "Policy location is '$POLICY_LOCATION', expected 'europe'"
    fi
    
    # Check policy kind
    POLICY_KIND=$(echo "$POLICY_DETAILS" | jq -r '.kind')
    if [ "$POLICY_KIND" = "NetworkInjection" ]; then
        check_result "PASS" "Policy kind is 'NetworkInjection'"
    else
        check_result "FAIL" "Policy kind is '$POLICY_KIND', expected 'NetworkInjection'"
    fi
    
    # Get system ID
    SYSTEM_ID=$(echo "$POLICY_DETAILS" | jq -r '.properties.systemId')
    echo "  System ID: $SYSTEM_ID"
    
    # Check VNet configuration in policy
    echo ""
    echo "Checking VNet configuration in policy..."
    VNET_COUNT=$(echo "$POLICY_DETAILS" | jq '.properties.networkInjection.virtualNetworks | length')
    if [ "$VNET_COUNT" -eq 2 ]; then
        check_result "PASS" "Policy configured with 2 VNets"
    else
        check_result "FAIL" "Policy configured with $VNET_COUNT VNets, expected 2"
    fi
    
    # Check specific VNets
    PRIMARY_VNET_IN_POLICY=$(echo "$POLICY_DETAILS" | jq -r --arg vnet "$VNET_PRIMARY" '.properties.networkInjection.virtualNetworks[] | select(.id | contains($vnet)) | .id')
    SECONDARY_VNET_IN_POLICY=$(echo "$POLICY_DETAILS" | jq -r --arg vnet "$VNET_SECONDARY" '.properties.networkInjection.virtualNetworks[] | select(.id | contains($vnet)) | .id')
    
    if [ -n "$PRIMARY_VNET_IN_POLICY" ]; then
        check_result "PASS" "Primary VNet '$VNET_PRIMARY' configured in policy"
    else
        check_result "FAIL" "Primary VNet '$VNET_PRIMARY' not found in policy"
    fi
    
    if [ -n "$SECONDARY_VNET_IN_POLICY" ]; then
        check_result "PASS" "Secondary VNet '$VNET_SECONDARY' configured in policy"
    else
        check_result "FAIL" "Secondary VNet '$VNET_SECONDARY' not found in policy"
    fi
    
else
    check_result "FAIL" "Enterprise policy '$POLICY_NAME' does not exist"
    SYSTEM_ID=""
fi

echo ""
echo -e "${CYAN}===================================================${NC}"
echo -e "${CYAN}2. SUBNET DELEGATION VERIFICATION${NC}"
echo -e "${CYAN}===================================================${NC}"

# Check Primary VNet subnet delegations
echo "Checking Primary VNet subnet delegations..."
PRIMARY_SUBNET_DETAILS=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_PRIMARY" --name "$SUBNET_NAME" --output json 2>/dev/null)

if [ $? -eq 0 ]; then
    check_result "PASS" "Primary VNet subnet '$SUBNET_NAME' exists"
    
    # Check delegations
    PRIMARY_DELEGATIONS=$(echo "$PRIMARY_SUBNET_DETAILS" | jq -r '.delegations[]? | select(.serviceName == "Microsoft.PowerPlatform/enterprisePolicies") | .serviceName')
    if [ -n "$PRIMARY_DELEGATIONS" ]; then
        check_result "PASS" "Primary VNet has PowerPlatform delegation"
    else
        check_result "FAIL" "Primary VNet missing PowerPlatform delegation"
    fi
    
    # Check service association links
    PRIMARY_SERVICE_LINKS=$(echo "$PRIMARY_SUBNET_DETAILS" | jq -r '.serviceAssociationLinks[]? | .name')
    if [ -n "$PRIMARY_SERVICE_LINKS" ]; then
        check_result "PASS" "Primary VNet has service association links: $PRIMARY_SERVICE_LINKS"
    else
        check_result "WARN" "Primary VNet has no service association links (may still be provisioning)"
    fi
else
    check_result "FAIL" "Primary VNet subnet '$SUBNET_NAME' not found"
fi

# Check Secondary VNet subnet delegations
echo ""
echo "Checking Secondary VNet subnet delegations..."
SECONDARY_SUBNET_DETAILS=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_SECONDARY" --name "$SUBNET_NAME" --output json 2>/dev/null)

if [ $? -eq 0 ]; then
    check_result "PASS" "Secondary VNet subnet '$SUBNET_NAME' exists"
    
    # Check delegations
    SECONDARY_DELEGATIONS=$(echo "$SECONDARY_SUBNET_DETAILS" | jq -r '.delegations[]? | select(.serviceName == "Microsoft.PowerPlatform/enterprisePolicies") | .serviceName')
    if [ -n "$SECONDARY_DELEGATIONS" ]; then
        check_result "PASS" "Secondary VNet has PowerPlatform delegation"
    else
        check_result "FAIL" "Secondary VNet missing PowerPlatform delegation"
    fi
    
    # Check service association links
    SECONDARY_SERVICE_LINKS=$(echo "$SECONDARY_SUBNET_DETAILS" | jq -r '.serviceAssociationLinks[]? | .name')
    if [ -n "$SECONDARY_SERVICE_LINKS" ]; then
        check_result "PASS" "Secondary VNet has service association links: $SECONDARY_SERVICE_LINKS"
    else
        check_result "WARN" "Secondary VNet has no service association links (may still be provisioning)"
    fi
else
    check_result "FAIL" "Secondary VNet subnet '$SUBNET_NAME' not found"
fi

echo ""
echo -e "${CYAN}===================================================${NC}"
echo -e "${CYAN}3. ENVIRONMENT LINK VERIFICATION${NC}"
echo -e "${CYAN}===================================================${NC}"

# Check if environment is linked to the policy
echo "Checking environment link to policy..."
ENV_LINK_RESPONSE=$(az rest --method GET --url "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments/${ENV_ID}/enterprisePolicies/NetworkInjection?api-version=2019-10-01" --resource "https://api.bap.microsoft.com/" 2>/dev/null)

if [ $? -eq 0 ]; then
    check_result "PASS" "Environment is linked to a NetworkInjection policy (via API)"
    
    # Extract linked policy system ID
    LINKED_SYSTEM_ID=$(echo "$ENV_LINK_RESPONSE" | jq -r '.systemId // empty' 2>/dev/null)
    if [ -n "$LINKED_SYSTEM_ID" ] && [ "$LINKED_SYSTEM_ID" = "$SYSTEM_ID" ]; then
        check_result "PASS" "Environment linked to correct policy (System ID match)"
    elif [ -n "$LINKED_SYSTEM_ID" ]; then
        check_result "WARN" "Environment linked to different policy: $LINKED_SYSTEM_ID"
    else
        check_result "WARN" "Could not determine linked policy system ID"
    fi
else
    # The API might not show the link immediately, so check service association links as alternative verification
    echo "  API link check failed, verifying through service association links..."
    
    # Check both VNets for active service association links
    PRIMARY_LINKS=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_PRIMARY" --name "$SUBNET_NAME" --query 'serviceAssociationLinks[?allowDelete==`false`].name' --output tsv 2>/dev/null)
    SECONDARY_LINKS=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_SECONDARY" --name "$SUBNET_NAME" --query 'serviceAssociationLinks[?allowDelete==`false`].name' --output tsv 2>/dev/null)
    
    if [ -n "$PRIMARY_LINKS" ] && [ -n "$SECONDARY_LINKS" ]; then
        check_result "PASS" "Environment linked via service association links (active on both VNets)"
    elif [ -n "$PRIMARY_LINKS" ] || [ -n "$SECONDARY_LINKS" ]; then
        check_result "WARN" "Environment partially linked (service links on some VNets)"
    else
        check_result "FAIL" "Environment is not linked to any NetworkInjection policy"
    fi
fi

# Check environment details
echo ""
echo "Checking environment details..."
ENV_DETAILS=$(az rest --method GET --url "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments/${ENV_ID}?api-version=2019-10-01" --resource "https://api.bap.microsoft.com/" 2>/dev/null)

if [ $? -eq 0 ]; then
    ENV_NAME=$(echo "$ENV_DETAILS" | jq -r '.properties.displayName // .name')
    ENV_REGION=$(echo "$ENV_DETAILS" | jq -r '.properties.azureRegionHint // .location')
    ENV_STATE=$(echo "$ENV_DETAILS" | jq -r '.properties.provisioningState // "Unknown"')
    
    check_result "PASS" "Environment details retrieved"
    echo "  Environment Name: $ENV_NAME"
    echo "  Environment Region: $ENV_REGION"
    echo "  Environment State: $ENV_STATE"
    
    # Check if environment is in europe region
    if [[ "$ENV_REGION" =~ ^(europe|westeurope|northeurope)$ ]]; then
        check_result "PASS" "Environment is in Europe region ($ENV_REGION)"
    else
        check_result "WARN" "Environment region '$ENV_REGION' may not be optimal for europe policy"
    fi
else
    check_result "FAIL" "Could not retrieve environment details"
fi

echo ""
echo -e "${CYAN}===================================================${NC}"
echo -e "${CYAN}4. NETWORK CONNECTIVITY TEST${NC}"
echo -e "${CYAN}===================================================${NC}"

# Test connectivity to the VNets
echo "Testing network connectivity..."

# Check if VNets are reachable and in the same region
PRIMARY_VNET_DETAILS=$(az network vnet show --resource-group "$RESOURCE_GROUP" --name "$VNET_PRIMARY" --output json 2>/dev/null)
SECONDARY_VNET_DETAILS=$(az network vnet show --resource-group "$RESOURCE_GROUP" --name "$VNET_SECONDARY" --output json 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$PRIMARY_VNET_DETAILS" ]; then
    PRIMARY_LOCATION=$(echo "$PRIMARY_VNET_DETAILS" | jq -r '.location')
    check_result "PASS" "Primary VNet accessible (Location: $PRIMARY_LOCATION)"
else
    check_result "FAIL" "Primary VNet not accessible"
fi

if [ $? -eq 0 ] && [ -n "$SECONDARY_VNET_DETAILS" ]; then
    SECONDARY_LOCATION=$(echo "$SECONDARY_VNET_DETAILS" | jq -r '.location')
    check_result "PASS" "Secondary VNet accessible (Location: $SECONDARY_LOCATION)"
else
    check_result "FAIL" "Secondary VNet not accessible"
fi

# Check if both VNets are in supported regions for europe
if [ -n "$PRIMARY_LOCATION" ] && [ -n "$SECONDARY_LOCATION" ]; then
    if [[ "$PRIMARY_LOCATION" =~ ^(westeurope|northeurope)$ ]] && [[ "$SECONDARY_LOCATION" =~ ^(westeurope|northeurope)$ ]]; then
        check_result "PASS" "Both VNets are in supported Europe regions"
    else
        check_result "WARN" "VNet locations may not be optimal for europe policy"
    fi
fi

echo ""
echo -e "${CYAN}===================================================${NC}"
echo -e "${CYAN}5. SUMMARY & RECOMMENDATIONS${NC}"
echo -e "${CYAN}===================================================${NC}"

# Calculate success rate
SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo "Verification Results:"
echo "  Total Checks: $TOTAL_CHECKS"
echo "  Passed Checks: $PASSED_CHECKS"
echo "  Success Rate: ${SUCCESS_RATE}%"
echo ""

if [ $SUCCESS_RATE -ge 90 ]; then
    echo -e "${GREEN}🎉 EXCELLENT: Subnet injection is properly configured!${NC}"
    echo -e "${GREEN}Your PowerPlatform environment should be able to access private endpoints.${NC}"
elif [ $SUCCESS_RATE -ge 70 ]; then
    echo -e "${YELLOW}⚠️  GOOD: Subnet injection is mostly configured but may need attention.${NC}"
    echo -e "${YELLOW}Check the warnings above and wait for full propagation.${NC}"
else
    echo -e "${RED}❌ POOR: Subnet injection has significant issues.${NC}"
    echo -e "${RED}Review the failed checks and consider re-running the apply script.${NC}"
fi

echo ""
echo "Next Steps:"
if [ $SUCCESS_RATE -ge 80 ]; then
    echo "✓ Try connecting to your blob storage from Power Platform"
    echo "✓ Test private endpoint connectivity"
    echo "✓ If issues persist, wait 5-10 minutes for full propagation"
else
    echo "✗ Fix the failed checks above"
    echo "✗ Consider running the apply script again: ./apply_powerplatform_injection.sh"
    echo "✗ Check Azure portal for any additional configuration issues"
fi

echo ""
echo "Detailed Information:"
echo "  Policy ARM ID: /subscriptions/$(az account show --query id --output tsv)/resourceGroups/$POLICY_RESOURCE_GROUP/providers/Microsoft.PowerPlatform/enterprisePolicies/$POLICY_NAME"
if [ -n "$SYSTEM_ID" ]; then
    echo "  Policy System ID: $SYSTEM_ID"
fi
echo "  Environment ID: $ENV_ID"
echo ""
echo "🔍 Verification completed at $(date)"
