#!/usr/bin/env python3
"""
SharePoint Connectivity Diagnostic
=================================

This script checks SharePoint connectivity using both service principal and interactive auth.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('sharepoint-diagnostic')

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    logger.info(f"Loaded .env from {env_path}")
else:
    logger.error(f".env file not found at {env_path}")

def check_sharepoint_env_vars():
    """Check SharePoint environment variables."""
    required_vars = {
        "AZURE_TENANT_ID": os.getenv("AZURE_TENANT_ID", ""),
        "SHAREPOINT_CLIENT_ID": os.getenv("SHAREPOINT_CLIENT_ID", ""),
        "SHAREPOINT_SITE_DOMAIN": os.getenv("SHAREPOINT_SITE_DOMAIN", ""),
        "SHAREPOINT_DRIVE_NAME": os.getenv("SHAREPOINT_DRIVE_NAME", ""),
    }
    
    # Service Principal specific variables
    sp_vars = {
        "AGENTIC_APP_SPN_CERT_PATH": os.getenv("AGENTIC_APP_SPN_CERT_PATH", ""),
        "AGENTIC_APP_SPN_CERT_PASSWORD": os.getenv("AGENTIC_APP_SPN_CERT_PASSWORD", "") != ""
    }
    
    all_ok = True
    
    logger.info("Checking required SharePoint variables:")
    for var, value in required_vars.items():
        if not value:
            logger.error(f"❌ {var} is not set")
            all_ok = False
        else:
            logger.info(f"✅ {var} is set")
    
    logger.info("\nChecking Service Principal authentication variables:")
    for var, value in sp_vars.items():
        if var == "AGENTIC_APP_SPN_CERT_PATH":
            if not value:
                logger.warning(f"⚠️ {var} is not set, service principal authentication will not work")
            elif not os.path.exists(value):
                logger.error(f"❌ {var} is set but file does not exist: {value}")
                all_ok = False
            else:
                logger.info(f"✅ {var} is set and file exists")
        elif not value:
            logger.warning(f"⚠️ {var} is not set, service principal authentication will not work")
        else:
            logger.info(f"✅ {var} is set")
    
    return all_ok

def test_interactive_auth():
    """Test interactive authentication to SharePoint."""
    try:
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("SHAREPOINT_CLIENT_ID")
        
        if not tenant_id or not client_id:
            logger.error("Interactive auth requires AZURE_TENANT_ID and SHAREPOINT_CLIENT_ID")
            return False
            
        from msal import PublicClientApplication
        
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        logger.info(f"Creating PublicClientApplication with client_id={client_id}")
        app = PublicClientApplication(client_id, authority=authority)
        
        logger.info("Attempting interactive login - a browser window should open...")
        result = app.acquire_token_interactive(["https://graph.microsoft.com/.default"])
        
        if "access_token" in result:
            logger.info("✅ Successfully obtained access token via interactive login")
            return True
        else:
            logger.error(f"❌ Failed to get access token interactively: {result.get('error')}")
            return False
    except Exception as e:
        logger.error(f"❌ Error during interactive authentication: {str(e)}")
        return False
        
def main():
    """Run SharePoint diagnostic checks."""
    logger.info("Starting SharePoint connectivity diagnostic...")
    
    # Check environment variables
    if not check_sharepoint_env_vars():
        logger.warning("Some required environment variables are missing or invalid")
    
    # Ask user if they want to test interactive authentication
    choice = input("\nDo you want to test interactive authentication? (y/n): ").lower()
    if choice.startswith('y'):
        test_interactive_auth()
    
    # Try importing the SharePoint data reader
    try:
        sys.path.append(str(Path(__file__).resolve().parent))
        from connectors.sharepoint.sharepoint_data_reader import SharePointDataReader
        logger.info("✅ Successfully imported SharePointDataReader")
        
        # Create an instance to trigger initialization
        reader = SharePointDataReader()
        logger.info("✅ Successfully initialized SharePointDataReader")
        
    except Exception as e:
        logger.error(f"❌ Error importing or initializing SharePointDataReader: {str(e)}")

if __name__ == "__main__":
    main()
