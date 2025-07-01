"""
Azure Authentication Service for Private and Public Resources

This module provides a unified authentication service that can handle both:
1. Public resources with API keys/connection strings
2. Private resources with managed identity authentication

It ensures backward compatibility while enabling private endpoint support.
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, ManagedIdentityCredential, AzureCliCredential
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
    logging.debug(f"Loaded environment variables from {env_path}")
except ImportError:
    logging.warning("python-dotenv not available, environment variables must be set externally")

# Storage imports (optional)
try:
    from azure.storage.blob import BlobServiceClient
    BLOB_STORAGE_AVAILABLE = True
except ImportError:
    BLOB_STORAGE_AVAILABLE = False
    logging.warning("Azure Storage SDK not available. Blob storage features will be disabled.")

class AzureAuthService:
    """
    Unified authentication service for Azure resources supporting both
    public (key-based) and private (managed identity) authentication.
    """
    
    def __init__(self):
        """Initialize the authentication service."""
        self._credential = None
        self._init_credential()
    
    def _init_credential(self):
        """Initialize Azure credentials for managed identity authentication."""
        try:
            self._credential = ChainedTokenCredential(
                ManagedIdentityCredential(),
                AzureCliCredential()
            )
            logging.debug("Azure credential initialized successfully")
        except Exception as e:
            logging.warning(f"Failed to initialize Azure credential: {e}")
            self._credential = None
    
    def get_document_intelligence_config(self) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Get Document Intelligence configuration with fallback support.
        
        Returns:
            Tuple of (endpoint, api_key, use_managed_identity)
        """
        # Try multiple environment variable names for endpoint
        endpoint = (
            os.getenv("DOCUMENT_INTEL_ENDPOINT") or
            os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT") or
            os.getenv("AZURE_FORMREC_ENDPOINT") or
            os.getenv("AZURE_FORMREC_SERVICE")
        )
        
        # Try multiple environment variable names for API key
        api_key = (
            os.getenv("DOCUMENT_INTEL_KEY") or
            os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY") or
            os.getenv("AZURE_FORMREC_KEY")
        )
        
        # Determine authentication method
        use_managed_identity = not bool(api_key)
        
        # Validate endpoint
        if not endpoint:
            logging.error("Document Intelligence endpoint not configured. Please set one of: DOCUMENT_INTEL_ENDPOINT, AZURE_FORMREC_ENDPOINT, or AZURE_FORMREC_SERVICE")
            return None, None, False
        
        # Ensure endpoint format is correct
        if not endpoint.startswith('http'):
            if '.' in endpoint:
                endpoint = f"https://{endpoint}"
            else:
                endpoint = f"https://{endpoint}.cognitiveservices.azure.com"
        
        endpoint = endpoint.rstrip('/')
        
        logging.info(f"Document Intelligence config: endpoint={endpoint}, auth_method={'managed_identity' if use_managed_identity else 'api_key'}")
        
        return endpoint, api_key, use_managed_identity
    
    def create_blob_service_client(self, connection_string: Optional[str] = None, 
                                   account_name: Optional[str] = None,
                                   account_url: Optional[str] = None,
                                   auto_fallback: bool = True) -> Optional[BlobServiceClient]:
        """
        Create a BlobServiceClient supporting both connection string and managed identity authentication.
        
        Args:
            connection_string: Azure Storage connection string (for public storage)
            account_name: Storage account name (for managed identity)
            account_url: Storage account URL (for managed identity)
            auto_fallback: If True, automatically fallback to managed identity if connection string fails
            
        Returns:
            BlobServiceClient instance or None if configuration is invalid
        """
        if not BLOB_STORAGE_AVAILABLE:
            logging.warning("Azure Storage SDK not available")
            return None
        
        try:
            # Try connection string first (backward compatibility)
            if connection_string:
                logging.info("Initializing blob storage with connection string")
                try:
                    return BlobServiceClient.from_connection_string(connection_string)
                except Exception as e:
                    # Check if this is a KeyBasedAuthenticationNotPermitted error
                    if "KeyBasedAuthenticationNotPermitted" in str(e):
                        logging.info("Storage account requires managed identity authentication. Connection string authentication is disabled.")
                        # Extract account name from connection string for managed identity fallback
                        if auto_fallback:
                            try:
                                for part in connection_string.split(';'):
                                    if part.startswith('AccountName='):
                                        extracted_account_name = part.split('=', 1)[1]
                                        logging.info(f"Attempting managed identity fallback with account: {extracted_account_name}")
                                        fallback_url = f"https://{extracted_account_name}.blob.core.windows.net"
                                        if self._credential:
                                            return BlobServiceClient(account_url=fallback_url, credential=self._credential)
                                        break
                            except Exception as fallback_error:
                                logging.warning(f"Managed identity fallback failed: {fallback_error}")
                    else:
                        logging.error(f"Connection string authentication failed: {e}")
                    raise e
            
            # Try managed identity with account URL
            if account_url and self._credential:
                logging.info("Initializing blob storage with managed identity (account URL)")
                return BlobServiceClient(account_url=account_url, credential=self._credential)
            
            # Try managed identity with account name
            if account_name and self._credential:
                account_url = f"https://{account_name}.blob.core.windows.net"
                logging.info(f"Initializing blob storage with managed identity (account name: {account_name})")
                return BlobServiceClient(account_url=account_url, credential=self._credential)
            
            logging.warning("No valid blob storage configuration found")
            return None
            
        except Exception as e:
            logging.error(f"Failed to create blob service client: {e}")
            return None
    
    def get_storage_config_from_env(self) -> Dict[str, Any]:
        """
        Extract storage configuration from environment variables.
        
        Returns:
            Dictionary with storage configuration
        """
        config = {}
        
        # Connection string (for public storage)
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            config['connection_string'] = connection_string
            # Extract account name from connection string for fallback
            try:
                for part in connection_string.split(';'):
                    if part.startswith('AccountName='):
                        config['account_name'] = part.split('=', 1)[1]
                        break
            except:
                pass
        
        # Direct account configuration (for managed identity)
        account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        if account_name:
            config['account_name'] = account_name
            config['account_url'] = f"https://{account_name}.blob.core.windows.net"
        
        account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        if account_url:
            config['account_url'] = account_url
        
        # Container name
        container_name = os.getenv("AZURE_STORAGE_CONTAINER", "images")
        config['container_name'] = container_name
        
        return config
    
    def create_blob_client_from_env(self) -> Tuple[Optional[BlobServiceClient], Optional[str]]:
        """
        Create blob service client from environment variables with automatic fallback.
        
        Returns:
            Tuple of (BlobServiceClient, container_name) or (None, None)
        """
        storage_config = self.get_storage_config_from_env()
        container_name = storage_config.get('container_name', 'images')
        
        # Try connection string first (backward compatibility) with auto-fallback enabled
        if 'connection_string' in storage_config:
            try:
                client = self.create_blob_service_client(
                    connection_string=storage_config['connection_string'],
                    auto_fallback=True
                )
                if client:
                    return client, container_name
            except Exception as e:
                # If connection string failed and we have managed identity config, try it
                logging.warning(f"Connection string authentication failed: {e}")
                if "KeyBasedAuthenticationNotPermitted" in str(e):
                    logging.info("Attempting direct managed identity authentication...")
        
        # Try managed identity with account URL
        if 'account_url' in storage_config:
            try:
                client = self.create_blob_service_client(
                    account_url=storage_config['account_url'],
                    auto_fallback=False
                )
                if client:
                    return client, container_name
            except Exception as e:
                logging.warning(f"Managed identity with account URL failed: {e}")
        
        # Try managed identity with account name
        if 'account_name' in storage_config:
            try:
                client = self.create_blob_service_client(
                    account_name=storage_config['account_name'],
                    auto_fallback=False
                )
                if client:
                    return client, container_name
            except Exception as e:
                logging.warning(f"Managed identity with account name failed: {e}")
        
        logging.warning("Could not create blob service client from environment variables")
        return None, None
    
    def set_document_intelligence_env_vars(self):
        """
        Set the required environment variables for Document Intelligence compatibility.
        This ensures backward compatibility with existing code that looks for specific variable names.
        """
        endpoint, api_key, use_managed_identity = self.get_document_intelligence_config()
        
        if endpoint:
            # Set the environment variables that the existing code expects
            if not os.getenv("AZURE_FORMREC_ENDPOINT"):
                os.environ["AZURE_FORMREC_ENDPOINT"] = endpoint
                logging.info(f"Set AZURE_FORMREC_ENDPOINT = {endpoint}")
            if not os.getenv("AZURE_FORMREC_SERVICE"):
                os.environ["AZURE_FORMREC_SERVICE"] = endpoint
                logging.info(f"Set AZURE_FORMREC_SERVICE = {endpoint}")
            
            if api_key and not os.getenv("AZURE_FORMREC_KEY"):
                os.environ["AZURE_FORMREC_KEY"] = api_key
                logging.info("Set AZURE_FORMREC_KEY for API key authentication")
            
            logging.info(f"Document Intelligence compatibility environment variables configured")
        else:
            logging.warning("No Document Intelligence endpoint available to set compatibility variables")
    
    def setup_all_compatibility_env_vars(self):
        """
        Set up all compatibility environment variables for legacy code.
        This should be called early in the application startup.
        """
        logging.info("Setting up all compatibility environment variables...")
        
        # Set up Document Intelligence compatibility
        self.set_document_intelligence_env_vars()
        
        # Set up Azure Storage compatibility
        storage_config = self.get_storage_config_from_env()
        if storage_config:
            logging.info(f"Azure Storage configuration available: {list(storage_config.keys())}")
        else:
            logging.warning("No Azure Storage configuration found")
        
        logging.info("All compatibility environment variables setup complete")
    
    @property
    def credential(self):
        """Get the Azure credential for managed identity authentication."""
        return self._credential

# Global instance for easy access
azure_auth_service = AzureAuthService()
