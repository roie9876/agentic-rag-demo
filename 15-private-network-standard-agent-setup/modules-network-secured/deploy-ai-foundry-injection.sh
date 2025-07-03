#!/bin/bash

# Deploy New AI Foundry Account with Network Injection
# This script creates a new AI Foundry account with network injection enabled,
# reusing existing VNet, subnets, and other infrastructure.

set -e

# Configuration
RESOURCE_GROUP="private-rg"
TEMPLATE_FILE="new-ai-foundry-with-injection.bicep"
PARAMETERS_FILE="new-ai-foundry-injection.parameters.json"
DEPLOYMENT_NAME="ai-foundry-network-injection-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Deploying AI Foundry Account with Network Injection"
echo "=================================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Template: $TEMPLATE_FILE"
echo "Parameters: $PARAMETERS_FILE"
echo "Deployment Name: $DEPLOYMENT_NAME"
echo ""

# Validate template first
echo "📋 Validating Bicep template..."
az deployment group validate \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$TEMPLATE_FILE" \
  --parameters @"$PARAMETERS_FILE" \
  --query "error" \
  --output table

echo "✅ Template validation successful!"
echo ""

# Deploy the template
echo "🔧 Deploying AI Foundry account with network injection..."
echo "This may take 5-10 minutes..."
echo ""

DEPLOYMENT_OUTPUT=$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$TEMPLATE_FILE" \
  --parameters @"$PARAMETERS_FILE" \
  --name "$DEPLOYMENT_NAME" \
  --query "properties.outputs" \
  --output json)

echo "✅ Deployment completed successfully!"
echo ""

# Display results
echo "📊 Deployment Results:"
echo "====================="
echo "$DEPLOYMENT_OUTPUT" | jq -r '
  "AI Foundry Account: " + .aiFoundryAccountName.value,
  "Account ID: " + .aiFoundryAccountId.value,
  "Endpoint: " + .aiFoundryEndpoint.value,
  "Private Endpoint: " + .privateEndpointName.value,
  "Network Injection: " + (.networkInjectionEnabled.value | tostring),
  "Agent Subnet ID: " + .agentSubnetId.value
'

echo ""
echo "🎉 AI Foundry account with network injection has been created!"
echo ""
echo "Key Features:"
echo "✅ Network injection enabled for agent execution"
echo "✅ Private endpoint configured for secure access"
echo "✅ DNS zones configured for private name resolution"
echo "✅ GPT-4o model deployed and ready to use"
echo ""
echo "Your AI agents will now execute within your controlled AgentSubnet."
echo "This provides enhanced security and network isolation for your workloads."
