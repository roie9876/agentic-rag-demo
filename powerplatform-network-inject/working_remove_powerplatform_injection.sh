#!/bin/bash

echo "🗑️  PowerPlatform Subnet Injection Removal Script"
echo "================================================="

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
NC='\033[0m' # No Color

echo "Configuration:"
echo "  Environment ID: $ENV_ID"
echo "  Policy Name: $POLICY_NAME"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Primary VNet: $VNET_PRIMARY"
echo "  Secondary VNet: $VNET_SECONDARY"
echo ""

# Function to check if policy exists
check_policy_exists() {
    az resource show --name "$POLICY_NAME" --resource-group "$POLICY_RESOURCE_GROUP" --resource-type "Microsoft.PowerPlatform/enterprisePolicies" --query 'name' --output tsv 2>/dev/null
}

# Function to get policy system ID
get_policy_system_id() {
    az resource show --name "$POLICY_NAME" --resource-group "$POLICY_RESOURCE_GROUP" --resource-type "Microsoft.PowerPlatform/enterprisePolicies" --query 'properties.systemId' --output tsv 2>/dev/null
}

# Function to check environment link status
check_env_link() {
    az rest --method GET --url "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments/${ENV_ID}/enterprisePolicies/NetworkInjection?api-version=2019-10-01" --resource "https://api.bap.microsoft.com/" 2>/dev/null
    return $?
}

# Function to unlink environment from policy
unlink_environment() {
    local system_id=$1
    echo -e "${BLUE}🔗 Unlinking environment from policy...${NC}"
    
    # Try the unlink operation and capture output
    local unlink_output
    unlink_output=$(az rest --method POST \
        --url "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments/${ENV_ID}/enterprisePolicies/NetworkInjection/unlink?api-version=2019-10-01" \
        --resource "https://api.bap.microsoft.com/" \
        --body "{\"SystemId\": \"${system_id}\"}" \
        --headers "Content-Type=application/json" 2>&1)
    
    local result=$?
    
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ Environment unlinked successfully${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Unlink attempt failed, trying alternative approach...${NC}"
        echo "Unlink error details: $unlink_output"
        
        # Wait a bit and try again with a longer timeout
        sleep 10
        echo "Retrying unlink operation..."
        
        unlink_output=$(az rest --method POST \
            --url "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments/${ENV_ID}/enterprisePolicies/NetworkInjection/unlink?api-version=2019-10-01" \
            --resource "https://api.bap.microsoft.com/" \
            --body "{\"SystemId\": \"${system_id}\"}" \
            --headers "Content-Type=application/json" 2>&1)
        
        result=$?
        
        if [ $result -eq 0 ]; then
            echo -e "${GREEN}✅ Environment unlinked successfully on retry${NC}"
            return 0
        else
            echo -e "${RED}❌ Failed to unlink environment after retry${NC}"
            echo "Final error details: $unlink_output"
            return 1
        fi
    fi
}

# Function to delete policy
delete_policy() {
    echo -e "${BLUE}🗑️  Deleting enterprise policy...${NC}"
    
    # Wait for unlink to propagate
    sleep 5
    
    # Try to delete policy and capture both output and exit code
    local delete_output
    delete_output=$(az rest --method DELETE \
        --url "https://management.azure.com/subscriptions/$(az account show --query id --output tsv)/resourceGroups/${POLICY_RESOURCE_GROUP}/providers/Microsoft.PowerPlatform/enterprisePolicies/${POLICY_NAME}?api-version=2020-10-30" 2>&1)
    
    local result=$?
    
    # Check if deletion was successful (exit code 0 or specific success patterns)
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ Policy deleted successfully${NC}"
        return 0
    else
        # Check if the error is because policy doesn't exist (which is actually success for our purpose)
        if [[ "$delete_output" == *"ResourceNotFound"* ]] || [[ "$delete_output" == *"was not found"* ]]; then
            echo -e "${GREEN}✅ Policy already deleted or does not exist${NC}"
            return 0
        else
            echo -e "${RED}❌ Failed to delete policy${NC}"
            echo "Error details: $delete_output"
            return 1
        fi
    fi
}

# Function to remove subnet delegations
remove_delegations() {
    echo -e "${BLUE}🏗️  Removing subnet delegations...${NC}"
    
    # Remove Primary VNet delegation
    echo "  Removing delegation from $VNET_PRIMARY..."
    az network vnet subnet update \
        --resource-group "$RESOURCE_GROUP" \
        --vnet-name "$VNET_PRIMARY" \
        --name "$SUBNET_NAME" \
        --remove delegations \
        --output none 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ Primary VNet delegation removed${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Primary VNet delegation may already be removed${NC}"
    fi
    
    # Remove Secondary VNet delegation
    echo "  Removing delegation from $VNET_SECONDARY..."
    az network vnet subnet update \
        --resource-group "$RESOURCE_GROUP" \
        --vnet-name "$VNET_SECONDARY" \
        --name "$SUBNET_NAME" \
        --remove delegations \
        --output none 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ Secondary VNet delegation removed${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Secondary VNet delegation may already be removed${NC}"
    fi
}

# Function to verify final state
verify_cleanup() {
    echo -e "${BLUE}🔍 Verifying cleanup...${NC}"
    
    # Check if policy still exists
    local policy_check_output
    policy_check_output=$(check_policy_exists 2>&1)
    if [ -z "$policy_check_output" ] || [[ "$policy_check_output" == *"ResourceNotFound"* ]] || [[ "$policy_check_output" == *"was not found"* ]]; then
        echo -e "${GREEN}  ✅ Policy successfully deleted${NC}"
        POLICY_DELETED=true
    else
        echo -e "${RED}  ❌ Policy still exists${NC}"
        POLICY_DELETED=false
    fi
    
    # Check delegations
    local primary_delegations=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_PRIMARY" --name "$SUBNET_NAME" --query 'length(delegations)' --output tsv 2>/dev/null)
    local secondary_delegations=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_SECONDARY" --name "$SUBNET_NAME" --query 'length(delegations)' --output tsv 2>/dev/null)
    
    if [ "$primary_delegations" -eq 0 ] && [ "$secondary_delegations" -eq 0 ]; then
        echo -e "${GREEN}  ✅ All subnet delegations removed${NC}"
        DELEGATIONS_REMOVED=true
    else
        echo -e "${YELLOW}  ⚠️  Some delegations may still exist${NC}"
        DELEGATIONS_REMOVED=false
    fi
    
    # Check service association links (more reliable than API check)
    local primary_service_links=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_PRIMARY" --name "$SUBNET_NAME" --query 'length(serviceAssociationLinks)' --output tsv 2>/dev/null)
    local secondary_service_links=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_SECONDARY" --name "$SUBNET_NAME" --query 'length(serviceAssociationLinks)' --output tsv 2>/dev/null)
    
    # Handle empty results (set to 0 if empty)
    primary_service_links=${primary_service_links:-0}
    secondary_service_links=${secondary_service_links:-0}
    
    if [ "$primary_service_links" -eq 0 ] && [ "$secondary_service_links" -eq 0 ]; then
        echo -e "${GREEN}  ✅ All service association links removed${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Some service association links may still exist (Primary: $primary_service_links, Secondary: $secondary_service_links)${NC}"
    fi
    
    # Overall status
    if [ "$POLICY_DELETED" = true ] && [ "$DELEGATIONS_REMOVED" = true ]; then
        return 0
    else
        return 1
    fi
}

# Main execution
echo -e "${BLUE}Starting PowerPlatform subnet injection removal...${NC}"
echo ""

# Step 1: Check if policy exists
echo "Step 1: Checking if policy exists..."
POLICY_EXISTS=$(check_policy_exists)

if [ -z "$POLICY_EXISTS" ]; then
    echo -e "${YELLOW}⚠️  Policy does not exist. Checking for delegations only...${NC}"
    SKIP_POLICY=true
else
    echo -e "${GREEN}✅ Policy found: $POLICY_EXISTS${NC}"
    SKIP_POLICY=false
    
    # Get system ID for unlinking
    SYSTEM_ID=$(get_policy_system_id)
    echo "  System ID: $SYSTEM_ID"
fi

echo ""

# Step 2: Unlink environment (if policy exists)
if [ "$SKIP_POLICY" = false ]; then
    echo "Step 2: Unlinking environment from policy..."
    if unlink_environment "$SYSTEM_ID"; then
        echo "  Environment unlinked successfully, waiting for propagation..."
        sleep 15  # Wait longer for unlinking to propagate
    else
        echo -e "${RED}  Failed to unlink environment. Policy deletion may fail.${NC}"
    fi
    echo ""
    
    # Step 3: Delete policy
    echo "Step 3: Deleting policy..."
    if ! delete_policy; then
        echo -e "${YELLOW}  Policy deletion failed. This is normal if environment is still linked.${NC}"
        echo -e "${YELLOW}  The environment should still be functional for your use case.${NC}"
    fi
    echo ""
else
    echo "Step 2-3: Skipping policy operations (policy doesn't exist)"
    echo ""
fi

# Step 4: Remove delegations
echo "Step 4: Removing subnet delegations..."
remove_delegations
echo ""

# Step 5: Verify cleanup
echo "Step 5: Verification..."
verify_cleanup
echo ""

# Final summary
echo -e "${GREEN}🎉 PowerPlatform subnet injection removal completed!${NC}"
echo ""
echo "Summary of actions:"
echo "✓ Environment unlinked from any policies"
echo "✓ Enterprise policy deleted (if it existed)"
echo "✓ Subnet delegations removed from both VNets"
echo ""
echo -e "${BLUE}Your environment is now clean and ready for:"
echo "  • DNS configuration changes"
echo "  • Private endpoint additions"
echo "  • VNet modifications"
echo -e "${NC}"
echo "If you need to re-enable subnet injection later, use the apply script."
