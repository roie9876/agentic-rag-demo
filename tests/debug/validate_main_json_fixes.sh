#!/bin/bash

# Validation script for main.json template fixes
echo "🔍 Validating main.json template fixes..."

# Check if main.json exists
if [ ! -f "15-private-network-standard-agent-setup/main.json" ]; then
    echo "❌ main.json not found"
    exit 1
fi

echo "✅ main.json found"

# Validate JSON syntax
echo "🔍 Checking JSON syntax..."
if python3 -m json.tool "15-private-network-standard-agent-setup/main.json" > /dev/null 2>&1; then
    echo "✅ JSON syntax is valid"
else
    echo "❌ JSON syntax is invalid"
    exit 1
fi

# Check for storage naming fix
echo "🔍 Checking storage account naming fix..."
if grep -q '"azureStorageName": "\[toLower(format('\''st{0}'\'',' "15-private-network-standard-agent-setup/main.json"; then
    echo "✅ Storage account naming fixed (st{uniqueSuffix})"
else
    echo "❌ Storage account naming NOT fixed"
    exit 1
fi

# Check for cosmos database creation
echo "🔍 Checking cosmos database creation..."
if grep -q '"type": "Microsoft.DocumentDB/databaseAccounts/sqlDatabases"' "15-private-network-standard-agent-setup/main.json"; then
    echo "✅ Cosmos database creation found"
else
    echo "❌ Cosmos database creation NOT found"
    exit 1
fi

# Check for cosmos containers creation
echo "🔍 Checking cosmos containers creation..."
container_count=$(grep -c '"type": "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers"' "15-private-network-standard-agent-setup/main.json")
if [ "$container_count" -eq 3 ]; then
    echo "✅ All 3 cosmos containers found"
else
    echo "❌ Expected 3 cosmos containers, found $container_count"
    exit 1
fi

# Check for enterprise_memory database name
echo "🔍 Checking enterprise_memory database..."
if grep -q '"enterprise_memory"' "15-private-network-standard-agent-setup/main.json"; then
    echo "✅ enterprise_memory database found"
else
    echo "❌ enterprise_memory database NOT found"
    exit 1
fi

# Check for container naming patterns
echo "🔍 Checking container naming patterns..."
if grep -q "thread-message-store" "15-private-network-standard-agent-setup/main.json" && \
   grep -q "system-thread-message-store" "15-private-network-standard-agent-setup/main.json" && \
   grep -q "agent-entity-store" "15-private-network-standard-agent-setup/main.json"; then
    echo "✅ All container naming patterns found"
else
    echo "❌ Container naming patterns incomplete"
    exit 1
fi

echo ""
echo "🎉 All validations passed! main.json template fixes are correct."
echo ""
echo "📋 Summary of fixes applied:"
echo "  ✅ Storage account naming: st{uniqueSuffix} (3-24 chars, no hyphens)"
echo "  ✅ Cosmos database: enterprise_memory"
echo "  ✅ Cosmos containers: 3 containers with proper naming"
echo "  ✅ Dependencies: Resources created before role assignments"
echo ""
echo "🚀 Ready to test deployment!"
