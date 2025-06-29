import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

class DocumentIntelligenceClientWrapper:
    """
    Tiny wrapper that resolves endpoint / key from multiple env-var aliases
    so existing code can work with either the new DOCUMENT_INTEL_* names
    or the older AZURE_FORMREC_* / AZURE_FORMRECOGNIZER_* names.
    Supports both key-based and managed identity authentication.
    """
    def __init__(self) -> None:
        ep  = (
            os.getenv("DOCUMENT_INTEL_ENDPOINT") or
            os.getenv("AZURE_FORMREC_SERVICE") or
            os.getenv("AZURE_FORMRECOGNIZER_ENDPOINT") or
            ""
        ).rstrip("/")

        key = (
            os.getenv("DOCUMENT_INTEL_KEY") or
            os.getenv("AZURE_FORMREC_KEY") or
            os.getenv("AZURE_FORMRECOGNIZER_KEY") or
            ""
        )

        if not ep:
            # Let callers detect "DI not configured"
            self.client = None
            self.docint_40_api = False
            return

        # Use managed identity if no key is provided, otherwise use key auth
        if key:
            credential = AzureKeyCredential(key)
        else:
            credential = DefaultAzureCredential()
            
        self.client = DocumentIntelligenceClient(ep, credential)

        # Check for v4.0 API availability (needed for DOCX/PPTX parsing)
        # We'll use multiple methods to detect 4.0 API availability
        self.docint_40_api = False
        try:
            # Method 1: Try to check if get_account_properties exists
            if hasattr(self.client, 'get_account_properties'):
                try:
                    _ = self.client.get_account_properties()
                    self.docint_40_api = True
                except Exception:
                    pass

            # Method 2: Check API version through client._config.api_version if available
            if hasattr(self.client, '_config') and hasattr(self.client._config, 'api_version'):
                api_version = getattr(self.client._config, 'api_version', '')
                if api_version:
                    # Check for 4.0-compatible API versions
                    if '2024' in api_version or '2025' in api_version:
                        self.docint_40_api = True
        except Exception:
            # If any method fails, assume it's not 4.0 API
            pass

        # Store API version for diagnostics
        self.api_version = "Unknown"
        if hasattr(self.client, '_config') and hasattr(self.client._config, 'api_version'):
            self.api_version = getattr(self.client._config, 'api_version', 'Unknown')
