import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

class DocumentIntelligenceClientWrapper:
    """
    Tiny wrapper that resolves endpoint / key from multiple env-var aliases
    so existing code can work with either the new DOCUMENT_INTEL_* names
    or the older AZURE_FORMREC_* / AZURE_FORMRECOGNIZER_* names.
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

        if not (ep and key):
            # Let callers detect “DI not configured”
            self.client = None
            self.docint_40_api = False
            return

        self.client = DocumentIntelligenceClient(ep, AzureKeyCredential(key))

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
                    if any(ver in api_version for ver in ['2023-10-31', '2024-', '4.0']):
                        self.docint_40_api = True
            
            # Method 3: Check for methods that were added in 4.0 API
            if hasattr(self.client, 'begin_analyze_document_from_url'):
                # This method exists in newer versions
                self.docint_40_api = True
            
        except Exception:
            # If any error occurs during version detection, assume 4.0 API is not available
            self.docint_40_api = False
