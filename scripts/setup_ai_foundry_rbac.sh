#!/bin/bash
"""
AI Foundry RBAC Setup and Verification Script
This script helps you set up and verify the necessary RBAC permissions for AI Foundry access.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}🚀 $1${NC}"
    echo "=================================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}🔸 $1${NC}"
}

# Check if Azure CLI is installed and logged in
check_azure_cli() {
    print_info "Checking Azure CLI..."
    
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if logged in
    if ! az account show &> /dev/null; then
        print_error "Not logged into Azure CLI. Please run 'az login' first."
        exit 1
    fi
    
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
    print_success "Logged into Azure CLI"
    print_info "Subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"
}

# Find AI Foundry resources
find_ai_foundry_resources() {
    print_info "Searching for AI Foundry resources..."
    
    # Find all ML workspaces (AI Foundry hubs)
    WORKSPACES=$(az ml workspace list --query "[].{Name:name, ResourceGroup:resourceGroup, Location:location}" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$WORKSPACES" ]; then
        print_warning "No AI Foundry hubs found in this subscription"
        return 1
    fi
    
    print_success "Found AI Foundry hubs:"
    echo "$WORKSPACES" | while IFS=$'\t' read -r name rg location; do
        echo "  📍 $name (in $rg, $location)"
    done
    
    return 0
}

# Get user input for configuration
get_configuration() {
    print_header "Configuration"
    
    # Get current user
    CURRENT_USER=$(az account show --query user.name -o tsv 2>/dev/null || echo "")
    if [ -n "$CURRENT_USER" ]; then
        print_info "Current user: $CURRENT_USER"
    fi
    
    # Get user/principal to assign permissions to
    echo
    read -p "🔸 Enter email or principal ID to assign permissions to [$CURRENT_USER]: " TARGET_USER
    TARGET_USER=${TARGET_USER:-$CURRENT_USER}
    
    # Get resource group
    echo
    print_info "Available resource groups:"
    az group list --query "[].name" -o tsv | head -10
    echo
    read -p "🔸 Enter resource group name: " RESOURCE_GROUP
    
    if [ -z "$RESOURCE_GROUP" ]; then
        print_error "Resource group is required"
        exit 1
    fi
    
    # Get AI Foundry hub name
    echo
    print_info "AI Foundry hubs in resource group '$RESOURCE_GROUP':"
    HUB_OPTIONS=$(az ml workspace list --resource-group "$RESOURCE_GROUP" --query "[].name" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$HUB_OPTIONS" ]; then
        print_warning "No AI Foundry hubs found in resource group '$RESOURCE_GROUP'"
        echo
        read -p "🔸 Enter AI Foundry hub name manually: " HUB_NAME
    else
        echo "$HUB_OPTIONS"
        echo
        read -p "🔸 Enter AI Foundry hub name: " HUB_NAME
    fi
    
    if [ -z "$HUB_NAME" ]; then
        print_error "Hub name is required"
        exit 1
    fi
    
    # Construct resource ID
    HUB_RESOURCE_ID="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.MachineLearningServices/workspaces/$HUB_NAME"
    
    echo
    print_info "Configuration Summary:"
    echo "  👤 Target User: $TARGET_USER"
    echo "  📂 Resource Group: $RESOURCE_GROUP"
    echo "  🏢 AI Foundry Hub: $HUB_NAME"
    echo "  🆔 Hub Resource ID: $HUB_RESOURCE_ID"
    echo
}

# Check current permissions
check_current_permissions() {
    print_header "Current Permissions"
    
    print_info "Checking current role assignments for: $TARGET_USER"
    
    # Check hub-level permissions
    echo
    print_info "Hub-level permissions:"
    HUB_ROLES=$(az role assignment list --assignee "$TARGET_USER" --scope "$HUB_RESOURCE_ID" --query "[].roleDefinitionName" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$HUB_ROLES" ]; then
        print_warning "No hub-level permissions found"
    else
        echo "$HUB_ROLES" | while read -r role; do
            print_success "  $role"
        done
    fi
    
    # Check resource group level permissions
    echo
    print_info "Resource group-level permissions:"
    RG_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"
    RG_ROLES=$(az role assignment list --assignee "$TARGET_USER" --scope "$RG_SCOPE" --query "[].roleDefinitionName" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$RG_ROLES" ]; then
        print_warning "No resource group-level permissions found"
    else
        echo "$RG_ROLES" | while read -r role; do
            print_success "  $role"
        done
    fi
    
    # Check if user has sufficient permissions
    SUFFICIENT_ROLES="Azure AI Developer|Azure AI Administrator|Cognitive Services User|Owner|Contributor"
    
    ALL_ROLES="$HUB_ROLES $RG_ROLES"
    HAS_SUFFICIENT=false
    
    for role in $ALL_ROLES; do
        if echo "$role" | grep -E "$SUFFICIENT_ROLES" > /dev/null; then
            HAS_SUFFICIENT=true
            break
        fi
    done
    
    if [ "$HAS_SUFFICIENT" = true ]; then
        print_success "User has sufficient permissions for AI Foundry access"
        return 0
    else
        print_warning "User may not have sufficient permissions for AI Foundry access"
        return 1
    fi
}

# Assign required permissions
assign_permissions() {
    print_header "Assigning Permissions"
    
    echo
    print_info "Available roles for AI Foundry:"
    echo "  1. Azure AI Developer (Recommended - full project access)"
    echo "  2. Cognitive Services User (Minimum - read-only access)"
    echo "  3. Azure AI Administrator (Full admin access - use carefully)"
    echo
    
    read -p "🔸 Select role to assign (1-3) [1]: " ROLE_CHOICE
    ROLE_CHOICE=${ROLE_CHOICE:-1}
    
    case $ROLE_CHOICE in
        1)
            ROLE_NAME="Azure AI Developer"
            ;;
        2)
            ROLE_NAME="Cognitive Services User"
            ;;
        3)
            ROLE_NAME="Azure AI Administrator"
            print_warning "This role grants full administrative access. Use with caution."
            read -p "Are you sure you want to proceed? (y/N): " CONFIRM
            if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
                print_info "Permission assignment cancelled"
                return 0
            fi
            ;;
        *)
            print_error "Invalid choice"
            return 1
            ;;
    esac
    
    echo
    print_info "Assigning role '$ROLE_NAME' to '$TARGET_USER' on hub '$HUB_NAME'..."
    
    if az role assignment create \
        --assignee "$TARGET_USER" \
        --role "$ROLE_NAME" \
        --scope "$HUB_RESOURCE_ID" \
        --output none 2>/dev/null; then
        print_success "Role assignment completed successfully"
    else
        print_error "Failed to assign role. Check if:"
        echo "  - The user/principal ID is correct"
        echo "  - You have permissions to assign roles"
        echo "  - The hub exists and the resource ID is correct"
        return 1
    fi
}

# Test AI Foundry access
test_access() {
    print_header "Testing AI Foundry Access"
    
    print_info "Testing access by running the project checker..."
    
    # Check if the Python script exists
    SCRIPT_PATH="/home/azureuser/agentic-rag-demo/scripts/check_ai_foundry_project.py"
    
    if [ -f "$SCRIPT_PATH" ]; then
        print_info "Running AI Foundry project checker..."
        python3 "$SCRIPT_PATH" || print_warning "Project checker encountered issues"
    else
        print_info "Project checker script not found. You can test manually by:"
        echo "  1. Running the check_ai_foundry_project.py script"
        echo "  2. Or testing API access directly"
    fi
}

# Main execution
main() {
    print_header "AI Foundry RBAC Setup and Verification"
    echo "This script helps you set up and verify RBAC permissions for Azure AI Foundry."
    echo
    
    # Check prerequisites
    check_azure_cli
    echo
    
    # Find resources
    if ! find_ai_foundry_resources; then
        print_warning "Consider creating an AI Foundry hub first if you haven't already"
    fi
    echo
    
    # Get configuration
    get_configuration
    
    # Check current permissions
    if check_current_permissions; then
        echo
        read -p "🔸 Permissions look good. Do you want to test access? (Y/n): " TEST_CHOICE
        if [[ ! "$TEST_CHOICE" =~ ^[Nn]$ ]]; then
            test_access
        fi
    else
        echo
        read -p "🔸 Do you want to assign additional permissions? (Y/n): " ASSIGN_CHOICE
        if [[ ! "$ASSIGN_CHOICE" =~ ^[Nn]$ ]]; then
            if assign_permissions; then
                echo
                print_info "Waiting a moment for permissions to propagate..."
                sleep 5
                echo
                test_access
            fi
        fi
    fi
    
    echo
    print_success "Setup complete!"
    print_info "If you're still having issues, check the detailed documentation in:"
    print_info "  docs/AI_FOUNDRY_RBAC_REQUIREMENTS.md"
}

# Run main function
main "$@"
