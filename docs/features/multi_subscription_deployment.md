"""
AI Foundry Multi-Subscription Deployment Enhancement
===================================================

This enhancement adds subscription selection capability to the AI Foundry Account deployment configuration.

## New Features Added:

### 1. Resource-Level Subscription Selection
Each resource type now has its own subscription selector:
- 🌌 **Cosmos DB**: Select subscription for Cosmos DB deployment or existing resource
- 🔍 **AI Search**: Select subscription for AI Search deployment or existing resource  
- 💾 **Storage Account**: Select subscription for Storage deployment or existing resource
- 🌐 **Virtual Network**: Select subscription for VNet deployment or existing VNet/subnets

### 2. Cross-Subscription Configuration Support
- **Hub-Spoke Architecture**: Deploy resources across different subscriptions
- **Enterprise Scenarios**: DNS zones in Network Hub, resources in Application Spokes
- **Resource Sharing**: Use existing resources from different subscriptions

### 3. Enhanced UI Features
- **Current Subscription Highlighting**: 🌟 indicator shows current subscription
- **Context Switching**: One-click switching to target subscriptions
- **Resource Caching**: Efficient resource loading with subscription-aware caching
- **Refresh Controls**: Manual refresh buttons for resource lists

### 4. Intelligent Defaults
- **Current Subscription Priority**: Defaults to current Azure CLI subscription
- **Smart Resource Grouping**: Groups resources by subscription and resource group
- **Cross-Sub Indicators**: Clear indicators when resources are in different subscriptions

## Usage Scenarios:

### Enterprise Hub-Spoke Model
```
🏢 Network Hub Subscription:
  - Private DNS zones in 'private-rg'
  - Virtual Network with subnets
  
🏢 Application Spoke Subscription:
  - AI Foundry Account resources
  - Cosmos DB, AI Search, Storage
  - Private endpoints connecting to Hub VNet
```

### Multi-Subscription Resource Sharing
```
📊 Data Subscription:
  - AI Search with existing indexes
  - Storage with document repositories
  
🤖 AI Subscription:
  - AI Foundry Account
  - Cosmos DB for conversations
  - Private endpoints for secure access
```

## Technical Implementation:

### Session State Management
Each resource maintains its own subscription context:
- `{resource_key}_subscription_id`: Selected subscription for each resource
- `{resource_key}_resources_{subscription_id}`: Cached resources per subscription
- Automatic cleanup on subscription changes

### Azure CLI Context Switching
- Temporary context switching for resource enumeration
- Automatic restoration of original context
- Error handling for authentication failures

### Resource Discovery
- Subscription-aware resource discovery
- Cross-subscription resource ID validation
- Private endpoint suggestions across subscriptions

## Configuration Options:

### For New Resources:
- Select target subscription for deployment
- Resources created in chosen subscription
- Cross-subscription networking supported

### For Existing Resources:
- Select subscription containing existing resources
- Cross-subscription resource access
- Private endpoint configuration across subscriptions

## Benefits:

1. **Enterprise Ready**: Supports complex multi-subscription architectures
2. **Flexible Deployment**: Mix new and existing resources across subscriptions
3. **Security Compliant**: Proper subscription isolation with cross-subscription access
4. **User Friendly**: Clear indicators and one-click subscription switching
5. **Resource Efficient**: Reuse existing resources from any accessible subscription

## Migration from Single-Subscription:

Existing deployments remain fully compatible:
- Default behavior uses current subscription for all resources
- New subscription selectors default to current subscription
- No breaking changes to existing configurations

This enhancement enables enterprise-grade multi-subscription AI Foundry deployments while maintaining simplicity for single-subscription scenarios.
"""
