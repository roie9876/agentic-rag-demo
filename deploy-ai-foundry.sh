#!/bin/bash

# Universal AI Foundry Account Deployment Script
# Works on any machine with any user

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}🔍 $1${NC}"
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

# Function to find project root
find_project_root() {
    local current_dir="$(pwd)"
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Check if we're already in project root
    if [[ -f "${current_dir}/agentic-rag-demo.py" ]]; then
        echo "${current_dir}"
        return 0
    fi
    
    # Check script directory
    if [[ -f "${script_dir}/agentic-rag-demo.py" ]]; then
        echo "${script_dir}"
        return 0
    fi
    
    # Search upwards from script directory
    local search_dir="${script_dir}"
    while [[ "${search_dir}" != "/" ]]; do
        if [[ -f "${search_dir}/agentic-rag-demo.py" ]]; then
            echo "${search_dir}"
            return 0
        fi
        search_dir="$(dirname "${search_dir}")"
    done
    
    return 1
}

# Main deployment function
main() {
    print_status "Starting AI Foundry Account Deployment"
    
    # Find project root
    print_status "Detecting project root..."
    if ! PROJECT_ROOT=$(find_project_root); then
        print_error "Could not find project root (agentic-rag-demo.py not found)"
        exit 1
    fi
    print_success "Project root: ${PROJECT_ROOT}"
    
    # Set deployment path
    DEPLOYMENT_PATH="${PROJECT_ROOT}/15-private-network-standard-agent-setup"
    
    # Verify deployment directory exists
    if [[ ! -d "${DEPLOYMENT_PATH}" ]]; then
        print_error "Deployment directory not found: ${DEPLOYMENT_PATH}"
        exit 1
    fi
    print_success "Deployment path: ${DEPLOYMENT_PATH}"
    
    # Change to deployment directory
    print_status "Changing to deployment directory..."
    cd "${DEPLOYMENT_PATH}"
    
    # Verify required files exist
    TEMPLATE_FILE="main.json"
    PARAMETERS_FILE="azuredeploy.parameters.json"
    
    if [[ ! -f "${TEMPLATE_FILE}" ]]; then
        print_error "Template file not found: ${TEMPLATE_FILE}"
        exit 1
    fi
    
    if [[ ! -f "${PARAMETERS_FILE}" ]]; then
        print_error "Parameters file not found: ${PARAMETERS_FILE}"
        exit 1
    fi
    
    print_success "Required files verified"
    
    # Check if user provided resource group
    if [[ -z "$1" ]]; then
        print_error "Usage: $0 <resource-group-name> [subscription-id]"
        print_warning "Example: $0 my-ai-foundry-rg 12345678-1234-1234-1234-123456789012"
        exit 1
    fi
    
    RESOURCE_GROUP="$1"
    SUBSCRIPTION_ID="$2"
    
    # Set subscription if provided
    if [[ -n "${SUBSCRIPTION_ID}" ]]; then
        print_status "Setting Azure subscription: ${SUBSCRIPTION_ID}"
        az account set --subscription "${SUBSCRIPTION_ID}"
        print_success "Subscription set successfully"
    fi
    
    # Verify Azure CLI is logged in
    print_status "Verifying Azure CLI authentication..."
    if ! az account show > /dev/null 2>&1; then
        print_error "Azure CLI not authenticated. Please run 'az login' first."
        exit 1
    fi
    
    CURRENT_SUBSCRIPTION=$(az account show --query "name" -o tsv)
    CURRENT_USER=$(az account show --query "user.name" -o tsv)
    print_success "Authenticated as: ${CURRENT_USER}"
    print_success "Current subscription: ${CURRENT_SUBSCRIPTION}"
    
    # Check if resource group exists
    print_status "Checking resource group: ${RESOURCE_GROUP}"
    if az group show --name "${RESOURCE_GROUP}" > /dev/null 2>&1; then
        print_success "Resource group exists: ${RESOURCE_GROUP}"
    else
        print_warning "Resource group does not exist: ${RESOURCE_GROUP}"
        read -p "Create resource group? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Creating resource group: ${RESOURCE_GROUP}"
            az group create --name "${RESOURCE_GROUP}" --location "East US"
            print_success "Resource group created successfully"
        else
            print_error "Deployment cancelled - resource group required"
            exit 1
        fi
    fi
    
    # Start deployment
    print_status "Starting AI Foundry Account deployment..."
    print_status "Resource Group: ${RESOURCE_GROUP}"
    print_status "Template: ${TEMPLATE_FILE}"
    print_status "Parameters: ${PARAMETERS_FILE}"
    
    # Deploy with Azure CLI
    DEPLOYMENT_NAME="ai-foundry-deployment-$(date +%Y%m%d-%H%M%S)"
    
    if az deployment group create \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${DEPLOYMENT_NAME}" \
        --template-file "${TEMPLATE_FILE}" \
        --parameters "@${PARAMETERS_FILE}"; then
        
        print_success "🎉 AI Foundry Account deployment completed successfully!"
        print_success "Deployment name: ${DEPLOYMENT_NAME}"
        print_success "Resource group: ${RESOURCE_GROUP}"
        
        # Return to project root
        cd "${PROJECT_ROOT}"
        print_status "Returned to project root: ${PROJECT_ROOT}"
        
        print_status "Next steps:"
        echo "1. Run health checks: python3 agentic-rag-demo.py"
        echo "2. Create search index"
        echo "3. Upload documents"
        echo "4. Test retrieval"
        
    else
        print_error "Deployment failed!"
        print_warning "Check the error messages above for details"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
