#!/usr/bin/env python3
"""
Configure Azure Function App Settings
Adds the missing environment variables needed for LLM summarization.
"""

import os
import sys
from dotenv import load_dotenv

def main():
    # Load local environment
    load_dotenv()
    
    # Get Azure OpenAI settings from .env
    openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    openai_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
    api_version = os.getenv('API_VERSION')
    
    print("🔧 Azure Function App Configuration Helper")
    print("=" * 50)
    print()
    print("Based on your .env file, add these settings to your Azure Function App:")
    print()
    print("📋 REQUIRED ENVIRONMENT VARIABLES:")
    print(f"  OPENAI_ENDPOINT={openai_endpoint}")
    print(f"  OPENAI_DEPLOYMENT={openai_deployment}")
    print()
    print("📋 OPTIONAL (since you want to remove API_VERSION from loading):")
    print(f"  # API_VERSION={api_version}  # Remove this if you want")
    print()
    print("🎯 HOW TO ADD THESE TO YOUR FUNCTION APP:")
    print()
    print("Option 1 - Azure Portal:")
    print("  1. Go to your Function App in Azure Portal")
    print("  2. Navigate to Settings → Environment variables")
    print("  3. Add the variables above")
    print()
    print("Option 2 - Azure CLI:")
    function_name = "your-function-app-name"
    resource_group = "your-resource-group"
    
    print(f'  az functionapp config appsettings set \\')
    print(f'    --name {function_name} \\')
    print(f'    --resource-group {resource_group} \\')
    print(f'    --settings \\')
    print(f'      "OPENAI_ENDPOINT={openai_endpoint}" \\')
    print(f'      "OPENAI_DEPLOYMENT={openai_deployment}"')
    print()
    print("🔍 CURRENT FUNCTION APP SETTINGS (from logs):")
    print("  ✅ SERVICE_NAME: private-ai-search")
    print("  ✅ AGENT_NAME: malan-prod-agent") 
    print("  ✅ INDEX_NAME: malan-prod")
    print("  ❌ OPENAI_ENDPOINT: NOT SET")
    print("  ❌ OPENAI_DEPLOYMENT: NOT SET")
    print()
    print("After adding these settings, your Azure Function will:")
    print("  ✅ Retrieve chunks from the knowledge agent")
    print("  ✅ Summarize them with Azure OpenAI LLM")
    print("  ✅ Return coherent, summarized answers")

if __name__ == "__main__":
    main()
