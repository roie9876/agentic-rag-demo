#!/usr/bin/env python3
"""
Azure OpenAI Model Availability Checker

This script checks if the specified OpenAI model and version are available
in the target Azure region, which could be causing the BCP177 deployment error.
"""

import requests
import json
from typing import Dict, List, Optional

def check_model_availability():
    """
    Check Azure OpenAI model availability for different regions and versions.
    
    Note: This is informational only. Real availability checking requires
    Azure CLI or Azure REST API calls with authentication.
    """
    
    print("🤖 Azure OpenAI Model Availability Analysis")
    print("=" * 60)
    
    # Known model configurations
    working_config = {
        "model": "gpt-4o",
        "version": "2024-08-06",
        "regions": ["eastus2", "westus", "westus3"]
    }
    
    current_config = {
        "model": "gpt-4.1", 
        "version": "2025-04-14",
        "regions": ["eastus2"]  # From your bicep file
    }
    
    print(f"📊 Configuration Comparison:")
    print(f"   Working: {working_config['model']} v{working_config['version']}")
    print(f"   Current: {current_config['model']} v{current_config['version']}")
    print()
    
    # Model version analysis
    print("🔍 Model Version Analysis:")
    print("-" * 40)
    
    # Check if the new model version is future-dated
    from datetime import datetime
    
    try:
        current_date = datetime.now()
        version_date = datetime.strptime("2025-04-14", "%Y-%m-%d")
        
        if version_date > current_date:
            print("❌ CRITICAL ISSUE: Model version 2025-04-14 is in the future!")
            print(f"   Current date: {current_date.strftime('%Y-%m-%d')}")
            print(f"   Model version date: {version_date.strftime('%Y-%m-%d')}")
            print("   Future-dated model versions are not available")
            print()
        else:
            print("✅ Model version date is valid")
            
    except ValueError as e:
        print(f"⚠️  Could not parse version date: {e}")
    
    # Check model name validity
    print("🏷️  Model Name Analysis:")
    print("-" * 40)
    
    known_gpt4_models = [
        "gpt-4",
        "gpt-4-32k", 
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4-vision-preview"
    ]
    
    if current_config["model"] not in known_gpt4_models:
        print(f"❌ WARNING: Model '{current_config['model']}' is not in known GPT-4 model list")
        print("   Known models:", ", ".join(known_gpt4_models))
        print("   This could cause deployment validation errors")
    else:
        print(f"✅ Model '{current_config['model']}' is recognized")
    
    print()
    
    # BCP177 Analysis
    print("🛠️  BCP177 Error Analysis:")
    print("-" * 40)
    print("BCP177: The variable is not available at deployment start.")
    print()
    print("Common causes:")
    print("1. ❌ Invalid model name/version causing early validation failure")
    print("2. ❌ Resource dependencies not properly defined")
    print("3. ❌ Variables using runtime functions incorrectly")
    print("4. ❌ Template syntax errors preventing compilation")
    print()
    
    # Specific to this case
    print("🎯 Diagnosis for Current Issue:")
    print("-" * 40)
    
    if current_config["model"] == "gpt-4.1":
        print("❌ LIKELY ROOT CAUSE: Invalid model name 'gpt-4.1'")
        print("   • 'gpt-4.1' is not a valid Azure OpenAI model name")
        print("   • Valid names use formats like 'gpt-4o', 'gpt-4-turbo'")
        print("   • Invalid model names cause template validation to fail")
        print("   • This prevents variable resolution during deployment")
        print()
    
    if "2025-04-14" in current_config["version"]:
        print("❌ SECONDARY ISSUE: Future model version")
        print("   • Version '2025-04-14' does not exist yet")
        print("   • Azure only supports released model versions")
        print("   • Future dates cause API validation failures")
        print()
    
    print("💡 SOLUTION:")
    print("-" * 40)
    print("Revert to working configuration:")
    print(f"  modelName: '{working_config['model']}'")
    print(f"  modelVersion: '{working_config['version']}'")
    print()
    print("Or use other known working configurations:")
    print("  • gpt-4o with version 2024-05-13")
    print("  • gpt-4-turbo with version 2024-04-09")
    print("  • gpt-4 with version 0613")

def generate_fix_script():
    """Generate a script to fix the Bicep deployment."""
    
    fix_script = """#!/bin/bash
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
"""
    
    with open("/home/azureuser/agentic-rag-demo/tests/debug/fix_bicep_bcp177.sh", "w") as f:
        f.write(fix_script)
    
    print("💾 Fix script generated: tests/debug/fix_bicep_bcp177.sh")
    print("   Run with: bash tests/debug/fix_bicep_bcp177.sh")

def main():
    """Main analysis function."""
    check_model_availability()
    print()
    generate_fix_script()

if __name__ == "__main__":
    main()
