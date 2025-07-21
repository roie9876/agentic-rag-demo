#!/bin/bash

echo "🔧 PowerPlatform Subnet Injection Apply Script"
echo "=============================================="

# Variables - Update these as needed
RESOURCE_GROUP="private-rg"
VNET_PRIMARY="PowerPlatform-Primary-vNET"
VNET_SECONDARY="PowerPlatform-Secondart-vNET"
SUBNET_NAME="default"
ENV_ID="b98e9fde-ed33-e9cb-b7c7-b79e43946c48"
POLICY_RESOURCE_GROUP="powerplatform-enterprise-policies"
POLICY_NAME="PowerPlatformSubnetInjectionPolicy-Europe"
SUBSCRIPTION_ID=$(az account show --query id --output tsv)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "Configuration:"
echo "  Environment ID: $ENV_ID"
echo "  Policy Name: $POLICY_NAME"
echo "  Policy Resource Group: $POLICY_RESOURCE_GROUP"
echo "  VNet Resource Group: $RESOURCE_GROUP"
echo "  Primary VNet: $VNET_PRIMARY"
echo "  Secondary VNet: $VNET_SECONDARY"
echo "  Subscription: $SUBSCRIPTION_ID"
echo ""

# Function to check if policy exists
check_policy_exists() {
    az resource show --name "$POLICY_NAME" --resource-group "$POLICY_RESOURCE_GROUP" --resource-type "Microsoft.PowerPlatform/enterprisePolicies" --query 'name' --output tsv 2>/dev/null
}

# Function to get policy system ID
get_policy_system_id() {
    az resource show --name "$POLICY_NAME" --resource-group "$POLICY_RESOURCE_GROUP" --resource-type "Microsoft.PowerPlatform/enterprisePolicies" --query 'properties.systemId' --output tsv 2>/dev/null
}

# Function to create policy JSON
create_policy_json() {
    cat > policy-config-temp.json << EOF
{
  "location": "europe",
  "kind": "NetworkInjection",
  "properties": {
    "networkInjection": {
      "virtualNetworks": [
        {
          "id": "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/virtualNetworks/${VNET_PRIMARY}",
          "subnet": {
            "name": "${SUBNET_NAME}"
          }
        },
        {
          "id": "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/virtualNetworks/${VNET_SECONDARY}",
          "subnet": {
            "name": "${SUBNET_NAME}"
          }
        }
      ]
    }
  }
}
EOF
}

# Function to ensure resource group exists
ensure_resource_group() {
    echo -e "${BLUE}📁 Ensuring resource group exists...${NC}"
    
    # Check if resource group exists
    if ! az group show --name "$POLICY_RESOURCE_GROUP" --output none 2>/dev/null; then
        echo "  Creating resource group: $POLICY_RESOURCE_GROUP"
        az group create --name "$POLICY_RESOURCE_GROUP" --location "West Europe" --output none
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✅ Resource group created${NC}"
        else
            echo -e "${RED}  ❌ Failed to create resource group${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}  ✅ Resource group already exists${NC}"
    fi
    return 0
}

# Function to create enterprise policy
create_policy() {
    echo -e "${BLUE}📝 Creating enterprise policy...${NC}"
    
    # Ensure resource group exists
    if ! ensure_resource_group; then
        return 1
    fi
    
    # Create the policy JSON
    create_policy_json
    
    echo "  Creating policy: $POLICY_NAME"
    echo "  Location: europe"
    echo "  Resource Group: $POLICY_RESOURCE_GROUP"
    
    # Create the policy using REST API with error output
    local policy_output
    policy_output=$(az rest --method PUT \
        --url "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${POLICY_RESOURCE_GROUP}/providers/Microsoft.PowerPlatform/enterprisePolicies/${POLICY_NAME}?api-version=2020-10-30" \
        --body @policy-config-temp.json \
        --headers "Content-Type=application/json" 2>&1)
    
    local result=$?
    
    # Clean up temp file
    rm -f policy-config-temp.json
    
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ Policy created successfully${NC}"
        
        # Wait for policy to be fully created
        echo "  ⏳ Waiting for policy to be ready..."
        sleep 10
        
        return 0
    else
        echo -e "${RED}❌ Failed to create policy${NC}"
        echo "Error details: $policy_output"
        return 1
    fi
}

# Function to remove NSGs from PowerPlatform subnets
remove_nsgs_from_subnets() {
    echo -e "${BLUE}🚫 Removing NSGs from PowerPlatform subnets...${NC}"
    echo "  (NSGs are not required for private endpoints and can cause connectivity issues)"
    
    # Check and remove NSG from Primary VNet
    echo "  Checking NSG on $VNET_PRIMARY..."
    local primary_nsg_id=$(az network vnet subnet show --vnet-name "$VNET_PRIMARY" --name "$SUBNET_NAME" --resource-group "$RESOURCE_GROUP" --query 'networkSecurityGroup.id' --output tsv 2>/dev/null || echo "")
    
    if [[ -n "$primary_nsg_id" && "$primary_nsg_id" != "null" ]]; then
        local primary_nsg_name=$(basename "$primary_nsg_id")
        echo "    Found NSG: $primary_nsg_name - removing..."
        
        az network vnet subnet update \
            --vnet-name "$VNET_PRIMARY" \
            --name "$SUBNET_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --remove networkSecurityGroup \
            --output none 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}    ✅ NSG removed from Primary VNet${NC}"
        else
            echo -e "${YELLOW}    ⚠️  Failed to remove NSG from Primary VNet (may not be critical)${NC}"
        fi
    else
        echo -e "${GREEN}    ✅ No NSG found on Primary VNet${NC}"
    fi
    
    # Check and remove NSG from Secondary VNet
    echo "  Checking NSG on $VNET_SECONDARY..."
    local secondary_nsg_id=$(az network vnet subnet show --vnet-name "$VNET_SECONDARY" --name "$SUBNET_NAME" --resource-group "$RESOURCE_GROUP" --query 'networkSecurityGroup.id' --output tsv 2>/dev/null || echo "")
    
    if [[ -n "$secondary_nsg_id" && "$secondary_nsg_id" != "null" ]]; then
        local secondary_nsg_name=$(basename "$secondary_nsg_id")
        echo "    Found NSG: $secondary_nsg_name - removing..."
        
        az network vnet subnet update \
            --vnet-name "$VNET_SECONDARY" \
            --name "$SUBNET_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --remove networkSecurityGroup \
            --output none 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}    ✅ NSG removed from Secondary VNet${NC}"
        else
            echo -e "${YELLOW}    ⚠️  Failed to remove NSG from Secondary VNet (may not be critical)${NC}"
        fi
    else
        echo -e "${GREEN}    ✅ No NSG found on Secondary VNet${NC}"
    fi
    
    echo -e "${GREEN}  ✅ NSG removal completed${NC}"
    echo "  💡 PowerPlatform subnets are now free of NSG restrictions"
    return 0
}

# Function to configure subnet delegations
configure_delegations() {
    echo -e "${BLUE}🏗️  Configuring subnet delegations...${NC}"
    
    # Configure Primary VNet delegation
    echo "  Configuring delegation for $VNET_PRIMARY..."
    az network vnet subnet update \
        --resource-group "$RESOURCE_GROUP" \
        --vnet-name "$VNET_PRIMARY" \
        --name "$SUBNET_NAME" \
        --delegations Microsoft.PowerPlatform/enterprisePolicies \
        --output none 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ Primary VNet delegation configured${NC}"
    else
        echo -e "${RED}  ❌ Failed to configure primary VNet delegation${NC}"
        return 1
    fi
    
    # Configure Secondary VNet delegation
    echo "  Configuring delegation for $VNET_SECONDARY..."
    az network vnet subnet update \
        --resource-group "$RESOURCE_GROUP" \
        --vnet-name "$VNET_SECONDARY" \
        --name "$SUBNET_NAME" \
        --delegations Microsoft.PowerPlatform/enterprisePolicies \
        --output none 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ Secondary VNet delegation configured${NC}"
    else
        echo -e "${RED}  ❌ Failed to configure secondary VNet delegation${NC}"
        return 1
    fi
    
    # Wait for delegations to propagate
    echo "  ⏳ Waiting for delegations to propagate..."
    sleep 30
    
    return 0
}

# Function to link environment to policy
link_environment() {
    local system_id=$1
    echo -e "${BLUE}🔗 Linking environment to policy...${NC}"
    
    az rest --method POST \
        --url "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments/${ENV_ID}/enterprisePolicies/NetworkInjection/link?api-version=2019-10-01" \
        --resource "https://api.bap.microsoft.com/" \
        --body "{\"SystemId\": \"${system_id}\"}" \
        --headers "Content-Type=application/json" \
        --output none 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Environment linked successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to link environment${NC}"
        return 1
    fi
}

# Function to verify configuration
verify_configuration() {
    echo -e "${BLUE}🔍 Verifying configuration...${NC}"
    
    # Check if policy exists and get system ID
    local system_id=$(get_policy_system_id)
    if [ -n "$system_id" ]; then
        echo -e "${GREEN}  ✅ Policy exists with system ID: $system_id${NC}"
    else
        echo -e "${RED}  ❌ Policy not found${NC}"
        return 1
    fi
    
    # Check delegations
    local primary_delegations=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_PRIMARY" --name "$SUBNET_NAME" --query 'delegations[?serviceName==`Microsoft.PowerPlatform/enterprisePolicies`]' --output tsv 2>/dev/null)
    local secondary_delegations=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_SECONDARY" --name "$SUBNET_NAME" --query 'delegations[?serviceName==`Microsoft.PowerPlatform/enterprisePolicies`]' --output tsv 2>/dev/null)
    
    if [ -n "$primary_delegations" ] && [ -n "$secondary_delegations" ]; then
        echo -e "${GREEN}  ✅ Subnet delegations configured correctly${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Some delegations may be missing${NC}"
    fi
    
    # Check environment link (this will show error if not linked, which means we need to check differently)
    echo "  📋 Environment link status check..."
    az rest --method GET \
        --url "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments/${ENV_ID}/enterprisePolicies/NetworkInjection?api-version=2019-10-01" \
        --resource "https://api.bap.microsoft.com/" \
        --output none 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ Environment is linked to policy${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Environment link status unclear${NC}"
    fi
}

# Main execution
echo -e "${BLUE}Starting PowerPlatform subnet injection setup...${NC}"
echo ""

# Step 1: Check if policy already exists
echo "Step 1: Checking if policy already exists..."
POLICY_EXISTS=$(check_policy_exists)

if [ -n "$POLICY_EXISTS" ]; then
    echo -e "${YELLOW}⚠️  Policy already exists: $POLICY_EXISTS${NC}"
    echo "  Using existing policy..."
    SYSTEM_ID=$(get_policy_system_id)
    echo "  System ID: $SYSTEM_ID"
    SKIP_CREATION=true
else
    echo -e "${BLUE}ℹ️  Policy does not exist. Will create new policy...${NC}"
    SKIP_CREATION=false
fi

echo ""

# Step 2: Remove NSGs from PowerPlatform subnets
echo "Step 2: Removing NSGs from PowerPlatform subnets..."
if ! remove_nsgs_from_subnets; then
    echo -e "${YELLOW}⚠️  NSG removal had issues, but continuing...${NC}"
fi

echo ""

# Step 3: Configure delegations (required before policy creation)
echo "Step 3: Configuring subnet delegations..."
if ! configure_delegations; then
    echo -e "${RED}❌ Failed to configure delegations. Exiting.${NC}"
    exit 1
fi

echo ""

# Step 4: Create policy (only if it doesn't exist)
if [ "$SKIP_CREATION" = false ]; then
    echo "Step 4: Creating enterprise policy..."
    if ! create_policy; then
        echo -e "${RED}❌ Failed to create policy. Exiting.${NC}"
        exit 1
    fi
    
    # Get the system ID of the newly created policy
    SYSTEM_ID=$(get_policy_system_id)
    echo "  Created policy with system ID: $SYSTEM_ID"
else
    echo "Step 4: Skipping policy creation (already exists)"
fi

echo ""

# Step 5: Link environment
echo "Step 5: Linking environment to policy..."
if ! link_environment "$SYSTEM_ID"; then
    echo -e "${RED}❌ Failed to link environment. Exiting.${NC}"
    exit 1
fi

echo ""

# Step 6: Verify configuration
echo "Step 6: Verifying configuration..."
verify_configuration

echo ""

# Final summary
echo -e "${GREEN}🎉 PowerPlatform subnet injection setup completed!${NC}"
echo ""
echo "Summary of actions:"
echo "✓ Enterprise policy created/verified"
echo "✓ NSGs removed from PowerPlatform subnets"
echo "✓ Subnet delegations configured on both VNets"
echo "✓ Environment linked to policy"
echo ""
echo -e "${BLUE}Your environment is now configured with subnet injection:"
echo "  • Traffic will route through your VNets"
echo "  • Private endpoints should be accessible"
echo "  • Wait 5-10 minutes for full propagation"
echo -e "${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:"
echo "  1. Wait 5-10 minutes for propagation"
echo "  2. Test your blob storage connection in Power Platform"
echo "  3. Verify private endpoint connectivity"
echo -e "${NC}"
