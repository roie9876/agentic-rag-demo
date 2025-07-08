#!/bin/bash
# Fix for BCP177 error in Bicep deployment
# Reverts model configuration to known working values

echo "🔧 Fixing Bicep deployment BCP177 error..."

BICEP_FILE="/home/azureuser/agentic-rag-demo/15-private-network-standard-agent-setup/main.bicep"

# Backup current file
cp "$BICEP_FILE" "$BICEP_FILE.error-backup"

# Fix model name
sed -i "s/param modelName string = 'gpt-4.1'/param modelName string = 'gpt-4o'/g" "$BICEP_FILE"

# Fix model version  
sed -i "s/param modelVersion string = '2025-04-14'/param modelVersion string = '2024-08-06'/g" "$BICEP_FILE"

# Fix comments
sed -i "s/gpt-4.1 model with version 2025-04-14/gpt-4o model with version 2024-08-06/g" "$BICEP_FILE"
sed -i "s/FIXED: gpt-4.1/FIXED: gpt-4o/g" "$BICEP_FILE"
sed -i "s/FIXED: 2025-04-14/FIXED: 2024-08-06/g" "$BICEP_FILE"

echo "✅ Model configuration reverted to working values"
echo "📁 Backup saved as: $BICEP_FILE.error-backup"
echo "🚀 Ready to re-deploy with working configuration"
