#!/usr/bin/env python3
"""
Script to add missing OpenAI environment variables to Azure Function App
This script helps configure the Function App with the required OpenAI settings.
"""

import os
from dotenv import load_dotenv

def print_function_app_settings():
    """Print the required Function App settings based on your .env file."""
    
    # Load environment from .env
    load_dotenv()
    
    # Get values from your local .env
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    
    print("🔧 Required Azure Function App Settings")
    print("=" * 50)
    print()
    print("Based on your .env file, add these environment variables")
    print("to your Azure Function App settings:")
    print()
    
    if openai_endpoint:
        print(f"OPENAI_ENDPOINT = {openai_endpoint}")
    else:
        print("❌ AZURE_OPENAI_ENDPOINT not found in .env")
    
    if openai_deployment:
        print(f"OPENAI_DEPLOYMENT = {openai_deployment}")
    else:
        print("❌ AZURE_OPENAI_DEPLOYMENT not found in .env")
    
    print()
    print("📋 How to add these settings:")
    print("1. Go to Azure Portal → Function Apps → Your Function App")
    print("2. Click 'Configuration' → 'Application settings'")
    print("3. Click '+ New application setting' for each setting above")
    print("4. Save the configuration")
    print()
    print("🔄 After adding settings:")
    print("1. Restart your Function App")
    print("2. Test the function again")
    print("3. Check the logs for 'Using managed identity for Azure OpenAI'")

if __name__ == "__main__":
    print_function_app_settings()
