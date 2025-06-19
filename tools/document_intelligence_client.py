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

        # Quick probe: is the 2023-10-31-preview / v4.0 endpoint available?
        # (Needed for DOCX / PPTX parsing.)
        try:
            # Will raise if the version is unsupported
            _ = self.client.get_account_properties()
            self.docint_40_api = True
        except Exception:
            self.docint_40_api = False
