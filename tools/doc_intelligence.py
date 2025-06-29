# DocumentIntelligenceClient.py

import os
import time
import json
import logging
import requests
from urllib.parse import urlparse, unquote
from azure.identity import ManagedIdentityCredential, AzureCliCredential, ChainedTokenCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError

class DocumentIntelligenceClient:
    """
    A client for interacting with Azure's Document Intelligence service.

    Attributes:
        service_name (str): The name of the Azure Document Intelligence service.
        api_version (str): The API version to use for the service.
        network_isolation (bool): Flag to indicate if network isolation is enabled.

    Methods:
        analyze_document(file_url, model):
            Analyzes a document using the specified model.
    """

    def __init__(self):
        """
        Initializes the DocumentIntelligence client.
        """
        # ai service resource name
        # Endpoint / service resolution
        raw_endpoint = os.getenv("AZURE_FORMREC_ENDPOINT")  # full URL, e.g. https://swedencentral.api.cognitive.microsoft.com
        service_name  = os.getenv("AZURE_FORMREC_SERVICE")  # short name, e.g. swedencentral
        if raw_endpoint:
            # remove a trailing slash if present
            self.endpoint = raw_endpoint.rstrip("/")
        elif service_name:
            # Check if service_name already contains a URL structure
            if '.' in service_name:
                if service_name.startswith('http'):
                    self.endpoint = service_name.rstrip("/")
                else:
                    self.endpoint = f"https://{service_name}"
            else:
                self.endpoint = f"https://{service_name}.cognitiveservices.azure.com"
        else:
            logging.error("[docintelligence] You must set either 'AZURE_FORMREC_ENDPOINT' or 'AZURE_FORMREC_SERVICE'.")
            raise EnvironmentError("Neither 'AZURE_FORMREC_ENDPOINT' nor 'AZURE_FORMREC_SERVICE' is set.")

        # keep for backward‑compatibility with any external references
        self.service_name = service_name if service_name else urlparse(self.endpoint).hostname.split(".")[0]

        # API configuration
        self.DOCINT_40_API = '2023-10-31-preview'
        self.DEFAULT_API_VERSION = '2024-11-30'
        self.api_version = os.getenv('FORM_REC_API_VERSION', os.getenv('DOCINT_API_VERSION', self.DEFAULT_API_VERSION))
        self.docint_40_api = self.api_version >= self.DOCINT_40_API

        # Network isolation
        network_isolation = os.getenv('NETWORK_ISOLATION', 'false')
        self.network_isolation = network_isolation.lower() == 'true'

        # Supported extensions
        self.file_extensions = [
            "pdf",
            "bmp",
            "jpg",
            "jpeg",
            "png",
            "tiff"
        ]
        self.ai_service_type = "formrecognizer"
        self.output_content_format = ""
        self.docint_features = "" 
        self.analyze_output_options = ""

        if self.docint_40_api:
            self.ai_service_type = "documentintelligence"
            self.file_extensions.extend(["docx", "pptx", "xlsx", "html"])
            self.output_content_format = "markdown"            
            self.analyze_output_options = "figures"

        # Get the API key for authentication
        self.api_key = os.getenv('AZURE_FORMREC_KEY', os.getenv('DOCUMENT_INTEL_KEY', ''))
        
        if not self.api_key:
            # Initialize the ChainedTokenCredential with ManagedIdentityCredential and AzureCliCredential as fallback
            try:
                self.credential = ChainedTokenCredential(
                    ManagedIdentityCredential(),
                    AzureCliCredential()
                )
                logging.debug("[docintelligence] Initialized ChainedTokenCredential with ManagedIdentityCredential and AzureCliCredential.")
            except Exception as e:
                logging.error(f"[docintelligence] Failed to initialize ChainedTokenCredential and no API key found: {e}")
                raise
        else:
            self.credential = None
            logging.debug("[docintelligence] Using API key authentication")

    def _get_file_extension(self, filepath):
        """
        Extracts the file extension from a given filepath.

        Args:
            filepath (str): The path or URL of the file.

        Returns:
            str: The file extension.
        """
        clean_filepath = filepath.split('?')[0]
        return clean_filepath.split('.')[-1].lower()

    def _get_content_type(self, file_ext):
        """
        Maps file extensions to their corresponding MIME types.

        Args:
            file_ext (str): The file extension.

        Returns:
            str: The MIME type.
        """
        extensions = {
            "pdf": "application/pdf", 
            "bmp": "image/bmp",
            "jpg": "image/jpeg",            
            "jpeg": "image/jpeg",
            "png": "image/png",
            "tiff": "image/tiff",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "html": "text/html" 
        }
        return extensions.get(file_ext, "application/octet-stream")

    def analyze_document_from_bytes(self, file_bytes: bytes, filename: str, model='prebuilt-layout', content_type=None, use_multipart=False):
        """
        Analyzes a document using the specified model, with input as bytes.

        Args:
            file_bytes (bytes): The bytes of the document to be analyzed.
            filename (str): The name of the document file.
            model (str): The model to use for document analysis.
            content_type (str, optional): Override content-type for the request. If None, will be determined from filename.
            use_multipart (bool): Whether to use multipart/form-data upload (like portal UI) instead of raw binary upload.

        Returns:
            tuple: A tuple containing the analysis result and any errors encountered.
        """
        result = {}
        errors = []
        result_id = None

        # DEBUG: Add detailed file size and content analysis
        file_size = len(file_bytes)
        logging.info(f"[docintelligence][{filename}] RECEIVED FILE SIZE: {file_size:,} bytes")
        
        # Log first and last 50 bytes to help diagnose truncation
        if file_size > 0:
            first_50 = file_bytes[:50]
            last_50 = file_bytes[-50:] if file_size >= 50 else file_bytes
            logging.info(f"[docintelligence][{filename}] First 50 bytes: {repr(first_50)}")
            logging.info(f"[docintelligence][{filename}] Last 50 bytes: {repr(last_50)}")
            
            # Check if it's actually a PDF
            if file_bytes.startswith(b'%PDF-'):
                logging.info(f"[docintelligence][{filename}] ✅ Valid PDF header detected")
                # Look for EOF marker
                if b'%%EOF' in file_bytes[-100:]:
                    logging.info(f"[docintelligence][{filename}] ✅ PDF EOF marker found")
                else:
                    logging.warning(f"[docintelligence][{filename}] ⚠️ PDF EOF marker NOT found - file may be truncated")
            else:
                logging.warning(f"[docintelligence][{filename}] ❌ No PDF header found - processing as {self._get_file_extension(filename).upper()} file")
                # Try to detect what type of content it actually is
                try:
                    text_preview = file_bytes.decode('utf-8', errors='ignore')[:200]
                    logging.info(f"[docintelligence][{filename}] Content as text: {repr(text_preview)}")
                except:
                    pass
        
        # Get the file extension from the filename
        file_ext = self._get_file_extension(filename)

        # Use provided content_type or determine from file extension
        if content_type:
            logging.info(f"[docintelligence][{filename}] Using provided content-type: {content_type}")
        else:
            if file_ext not in self.file_extensions:
                error_message = f"File extension '{file_ext}' is not supported."
                logging.error(f"[docintelligence][{filename}] {error_message}")
                errors.append(error_message)
                return result, errors
            content_type = self._get_content_type(file_ext)

        if file_ext == "pdf":
            self.docint_features = "ocr.highResolution"

        # Set request endpoint
        request_endpoint = f"{self.endpoint}/{self.ai_service_type}/documentModels/{model}:analyze?api-version={self.api_version}"
        if self.docint_features:
            request_endpoint += f"&features={self.docint_features}" 
        if self.output_content_format:
            request_endpoint += f"&outputContentFormat={self.output_content_format}"
        if self.analyze_output_options:
            request_endpoint += f"&output={self.analyze_output_options}"

        # Set request headers and data based on upload method
        if use_multipart:
            # Use multipart/form-data upload (like Azure portal UI)
            headers = {
                "x-ms-useragent": "gpt-rag/1.0.0"
                # Don't set Content-Type - let requests handle multipart boundary
            }
            files = {
                'file': (filename, file_bytes, content_type)
            }
            data = None
            logging.info(f"[docintelligence][{filename}] Using multipart/form-data upload")
        else:
            # Use raw binary upload (current method)
            headers = {
                "Content-Type": content_type,
                "x-ms-useragent": "gpt-rag/1.0.0"
            }
            files = None
            data = file_bytes
            logging.info(f"[docintelligence][{filename}] Using raw binary upload")
        
        try:
            # Use API key if available, otherwise fall back to token authentication
            if self.api_key:
                headers["Ocp-Apim-Subscription-Key"] = self.api_key
                logging.debug(f"[docintelligence][{filename}] Using API key authentication.")
            else:
                token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
                headers["Authorization"] = f"Bearer {token.token}"
                logging.debug(f"[docintelligence][{filename}] Retrieved authentication token.")
        except ClientAuthenticationError as e:
            error_message = f"Authentication failed: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors
        except Exception as e:
            error_message = f"Unexpected error during authentication: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors

        try:
            if use_multipart:
                response = requests.post(request_endpoint, headers=headers, files=files)
            else:
                response = requests.post(request_endpoint, headers=headers, data=data)
            logging.info(f"[docintelligence][{filename}] Sent analysis request.")
        except Exception as e:
            error_message = f"Error when sending request to Document Intelligence API: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors

        if response.status_code != 202:
            error_messages = {
                404: "Resource not found. Please verify your request URL. The Document Intelligence API version you are using may not be supported in your region.",
            }    
            error_message = error_messages.get(
                response.status_code, 
                f"Document Intelligence request error, code {response.status_code}: {response.text}"
            )
            logging.error(f"[docintelligence][{filename}] {error_message}")
            logging.error(f"[docintelligence][{filename}] Request URL: {request_endpoint}")
            logging.error(f"[docintelligence][{filename}] Content-Type: {content_type}")
            logging.error(f"[docintelligence][{filename}] File size: {len(file_bytes)} bytes")
            errors.append(error_message)
            return result, errors

        get_url = response.headers.get("Operation-Location")
        if not get_url:
            error_message = "Operation-Location header not found in the response."
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors

        # Extract result_id
        try:
            result_id = get_url.split("/")[-1].split("?")[0]
            logging.debug(f"[docintelligence][{filename}] Extracted result_id: {result_id}")
        except Exception as e:
            error_message = f"Error extracting result_id: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)

        result_headers = headers.copy()
        result_headers["Content-Type"] = "application/json-patch+json"

        while True:
            try:
                result_response = requests.get(get_url, headers=result_headers)
                result_json = result_response.json()

                if result_response.status_code != 200 or result_json.get("status") == "failed":
                    error_message = f"Document Intelligence polling error, code {result_response.status_code}: {result_response.text}"
                    logging.error(f"[docintelligence][{filename}] {error_message}")
                    errors.append(error_message)
                    break

                if result_json.get("status") == "succeeded":
                    result = result_json.get('analyzeResult', {})
                    logging.debug(f"[docintelligence][{filename}] Analysis succeeded.")
                    break

                logging.debug(f"[docintelligence][{filename}] Analysis in progress. Waiting for 2 seconds before retrying.")
                time.sleep(2)
            except Exception as e:
                error_message = f"Error during polling for analysis result: {e}"
                logging.error(f"[docintelligence][{filename}] {error_message}")
                errors.append(error_message)
                break

        # enrich result
        result['result_id'] = result_id
        result['model_id'] = model

        return result, errors


    def analyze_document_from_blob_url(self, file_url, model='prebuilt-layout'):
        """
        Analyzes a document in a blob container using the specified model.

        Args:
            file_url (str): The URL of the blob containing the document.
            model (str): The model to use for document analysis.

        Returns:
            tuple: A tuple containing the analysis result and any errors encountered.
        """
        result = {}
        errors = []
        result_id = None

        filename = os.path.basename(urlparse(file_url).path)
        file_ext = self._get_file_extension(file_url)

        if file_ext == "pdf":
            self.docint_features = "ocr.highResolution"

        # Set request endpoint
        request_endpoint = f"{self.endpoint}/{self.ai_service_type}/documentModels/{model}:analyze?api-version={self.api_version}"
        if self.docint_features:
            request_endpoint += f"&features={self.docint_features}" 
        if self.output_content_format:
            request_endpoint += f"&outputContentFormat={self.output_content_format}"
        if self.analyze_output_options:
            request_endpoint += f"&output={self.analyze_output_options}"

        # Set request headers
        headers = {
            "Content-Type": self._get_content_type(file_ext),
            "x-ms-useragent": "gpt-rag/1.0.0"
        }
        
        try:
            # Use API key if available, otherwise fall back to token authentication
            if self.api_key:
                headers["Ocp-Apim-Subscription-Key"] = self.api_key
                logging.debug(f"[docintelligence][{filename}] Using API key authentication.")
            else:
                token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
                headers["Authorization"] = f"Bearer {token.token}"
                logging.debug(f"[docintelligence][{filename}] Retrieved authentication token.")
        except ClientAuthenticationError as e:
            error_message = f"Authentication failed: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors
        except Exception as e:
            error_message = f"Unexpected error during authentication: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors

        parsed_url = urlparse(file_url)
        account_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        container_name = parsed_url.path.split("/")[1]
        blob_name = unquote(parsed_url.path[len(f"/{container_name}/"):])

        logging.debug(f"[docintelligence][{filename}] Connecting to blob storage.")

        try:
            blob_service_client = BlobServiceClient(account_url=account_url, credential=self.credential)
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            data = blob_client.download_blob().readall()
            logging.debug(f"[docintelligence][{filename}] Downloaded blob data.")
        except ResourceNotFoundError:
            error_message = f"Blob '{blob_name}' not found in container '{container_name}'."
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors
        except ClientAuthenticationError as e:
            error_message = f"Authentication failed when accessing blob storage: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors
        except Exception as e:
            error_message = f"Error accessing blob storage: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors

        try:
            response = requests.post(request_endpoint, headers=headers, data=data)
            logging.info(f"[docintelligence][{filename}] Sent analysis request.")
        except Exception as e:
            error_message = f"Error when sending request to Document Intelligence API: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors

        if response.status_code != 202:
            error_messages = {
                404: "Resource not found. Please verify your request URL. The Document Intelligence API version you are using may not be supported in your region.",
            }
            error_message = error_messages.get(
                response.status_code, 
                f"Document Intelligence request error, code {response.status_code}: {response.text}"
            )
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors

        get_url = response.headers.get("Operation-Location")
        if not get_url:
            error_message = "Operation-Location header not found in the response."
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)
            return result, errors

        # Extract result_id
        try:
            result_id = get_url.split("/")[-1].split("?")[0]
            logging.debug(f"[docintelligence][{filename}] Extracted result_id: {result_id}")
        except Exception as e:
            error_message = f"Error extracting result_id: {e}"
            logging.error(f"[docintelligence][{filename}] {error_message}")
            errors.append(error_message)

        result_headers = headers.copy()
        result_headers["Content-Type"] = "application/json-patch+json"

        while True:
            try:
                result_response = requests.get(get_url, headers=result_headers)
                result_json = result_response.json()

                if result_response.status_code != 200 or result_json.get("status") == "failed":
                    error_message = f"Document Intelligence polling error, code {result_response.status_code}: {result_response.text}"
                    logging.error(f"[docintelligence][{filename}] {error_message}")
                    errors.append(error_message)
                    break

                if result_json.get("status") == "succeeded":
                    result = result_json.get('analyzeResult', {})
                    logging.debug(f"[docintelligence][{filename}] Analysis succeeded.")
                    break

                logging.debug(f"[docintelligence][{filename}] Analysis in progress. Waiting for 2 seconds before retrying.")
                time.sleep(2)
            except Exception as e:
                error_message = f"Error during polling for analysis result: {e}"
                logging.error(f"[docintelligence][{filename}] {error_message}")
                errors.append(error_message)
                break

        # enrich result
        result['result_id'] = result_id
        result['model_id'] = model

        return result, errors


    def get_figure(self, model_id: str, result_id: str, figure_id: str) -> bytes:
        """
        Retrieves the binary image data for a specific figure from the Document Intelligence service.

        Args:
            model_id (str): The ID of the document model used for analysis.
            result_id (str): The ID of the analysis result.
            figure_id (str): The ID of the figure to retrieve.

        Returns:
            bytes: The binary image data of the figure.

        Raises:
            Exception: If the request fails or the response is invalid.
        """
        endpoint = f"{self.endpoint}/documentintelligence/documentModels/{model_id}/analyzeResults/{result_id}/figures/{figure_id}"
        url = f"{endpoint}?api-version={self.api_version}"

        headers = {
            "x-ms-useragent": "gpt-rag/1.0.0"
        }
        
        try:
            # Use API key if available, otherwise fall back to token authentication
            if self.api_key:
                headers["Ocp-Apim-Subscription-Key"] = self.api_key
                logging.debug(f"[docintelligence] Using API key authentication for fetching figure {figure_id}.")
            else:
                token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
                headers["Authorization"] = f"Bearer {token.token}"
                logging.debug(f"[docintelligence] Using token authentication for fetching figure {figure_id}.")
            
            logging.debug(f"[docintelligence] Fetching figure {figure_id} from result {result_id} using model {model_id}.")
        except ClientAuthenticationError as e:
            error_message = f"Authentication failed while fetching figure: {e}"
            logging.error(f"[docintelligence] {error_message}")
            raise Exception(error_message)
        except Exception as e:
            error_message = f"Unexpected error during authentication while fetching figure: {e}"
            logging.error(f"[docintelligence] {error_message}")
            raise Exception(error_message)

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                logging.debug(f"[docintelligence] Successfully retrieved figure {figure_id}.")
                return response.content  # Returns binary data
            else:
                error_message = f"Failed to retrieve figure {figure_id}, status code {response.status_code}: {response.text}"
                logging.error(f"[docintelligence] {error_message}")
                raise Exception(error_message)
        except Exception as e:
            error_message = f"Error when sending GET request for figure {figure_id}: {e}"
            logging.error(f"[docintelligence] {error_message}")
            raise Exception(error_message)