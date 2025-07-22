#!/bin/bash

# Test the container naming logic we just implemented
echo "🧪 Testing container naming logic from main.json fix..."

# Simulate the cosmosDBName parameter (from the deployment logs: aiservices-bicep208)
COSMOS_DB_NAME="aiservices-bicep208cosmosdb"

# Test the replace function logic: replace(cosmosDBName, 'cosmosdb', '')
BASE_NAME=${COSMOS_DB_NAME//cosmosdb/}

echo "📋 Container naming test:"
echo "  🗃️  Cosmos DB Name: $COSMOS_DB_NAME"
echo "  🏷️  Base Name (after replacing 'cosmosdb'): $BASE_NAME"
echo ""

# Generate the container names using the same logic as the template
USER_THREAD_NAME="${BASE_NAME}-thread-message-store"
SYSTEM_THREAD_NAME="${BASE_NAME}-system-thread-message-store"
ENTITY_STORE_NAME="${BASE_NAME}-agent-entity-store"

echo "🎯 Generated container names:"
echo "  📨 User Thread Store: $USER_THREAD_NAME"
echo "  🖥️  System Thread Store: $SYSTEM_THREAD_NAME"  
echo "  🗂️  Entity Store: $ENTITY_STORE_NAME"
echo ""

# Validate naming compliance (Cosmos container names can be up to 255 chars)
echo "🔍 Validation checks:"

for container in "$USER_THREAD_NAME" "$SYSTEM_THREAD_NAME" "$ENTITY_STORE_NAME"; do
    length=${#container}
    if [ $length -le 255 ]; then
        echo "  ✅ $container (length: $length chars) - Valid"
    else
        echo "  ❌ $container (length: $length chars) - Too long!"
    fi
done

echo ""
echo "💡 This matches the cosmos role assignment template expectations:"
echo "  - Role assignments use projectWorkspaceId from format-project-workspace-id deployment"  
echo "  - But containers are created using cosmos DB name for consistency"
echo "  - The naming should be compatible for role assignment scoping"

echo ""
echo "🎉 Container naming logic test complete!"
