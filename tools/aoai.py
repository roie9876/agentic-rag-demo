# AzureOpenAIClient.py

import logging
import os
import tiktoken
import time
from openai import AzureOpenAI, RateLimitError
from azure.identity import (
    ManagedIdentityCredential,
    AzureCliCredential,
    ChainedTokenCredential,
    get_bearer_token_provider,
)
from azure.core.exceptions import ClientAuthenticationError

class AzureOpenAIClient:
    """
    AzureOpenAIClient uses the OpenAI SDK's built-in retry mechanism with exponential backoff.
    The number of retries is controlled by the MAX_RETRIES environment variable.
    Delays between retries start at 0.5 seconds, doubling up to 8 seconds.
    If a rate limit error occurs after retries, the client will retry once more after the retry-after-ms header duration (if the header is present).
    """
    def __init__(self, document_filename=""):
        """
        Initializes the AzureOpenAI client.

        Parameters:
        document_filename (str, optional): Additional attribute for improved log traceability.
        """        
        self.max_retries = 10  # Maximum number of retries for rate limit errors
        self.max_embeddings_model_input_tokens = 8192
        self.max_gpt_model_input_tokens = 128000  # this is gpt4o max input, if using gpt35turbo use 16385

        self.document_filename = f"[{document_filename}]" if document_filename else ""
        
        # Get endpoint or construct from service name
        self.openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.openai_service_name = os.getenv('AZURE_OPENAI_SERVICE_NAME')
        
        if self.openai_endpoint:
            # Make sure endpoint ends with a trailing slash
            self.openai_api_base = self.openai_endpoint.rstrip('/')
            
            # Fix endpoint URL if it's missing '.openai' before '.azure.com'
            if '.azure.com' in self.openai_api_base and '.openai.azure.com' not in self.openai_api_base:
                self.openai_api_base = self.openai_api_base.replace('.azure.com', '.openai.azure.com')
                logging.info(f"[aoai]{self.document_filename} Corrected OpenAI endpoint URL: {self.openai_api_base}")
        elif self.openai_service_name:
            self.openai_api_base = f"https://{self.openai_service_name}.openai.azure.com"
        else:
            self.openai_api_base = None
            
        self.openai_api_version = os.getenv('AZURE_OPENAI_API_VERSION')
        self.openai_embeddings_deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
        self.openai_gpt_deployment = os.getenv('AZURE_OPENAI_CHATGPT_DEPLOYMENT')
        
        # Log a warning if any environment variable is empty
        env_vars = {
            'AZURE_OPENAI_SERVICE_NAME': self.openai_service_name,
            'AZURE_OPENAI_API_VERSION': self.openai_api_version,
            'AZURE_OPENAI_EMBEDDING_DEPLOYMENT': self.openai_embeddings_deployment,
            'AZURE_OPENAI_CHATGPT_DEPLOYMENT': self.openai_gpt_deployment
        }
        
        for var_name, var_value in env_vars.items():
            if not var_value:
                logging.warning(f'[aoai]{self.document_filename} Environment variable {var_name} is not set.')

        # Initialize the ChainedTokenCredential with ManagedIdentityCredential and AzureCliCredential
        try:
            self.credential = ChainedTokenCredential(
                ManagedIdentityCredential(),
                AzureCliCredential()
            )
            logging.debug(f"[aoai]{self.document_filename} Initialized ChainedTokenCredential with ManagedIdentityCredential and AzureCliCredential.")
        except Exception as e:
            logging.error(f"[aoai]{self.document_filename} Failed to initialize ChainedTokenCredential: {e}")
            raise

        # Initialize the bearer token provider
        try:
            self.token_provider = get_bearer_token_provider(
                self.credential, 
                "https://cognitiveservices.azure.com/.default"
            )
            logging.debug(f"[aoai]{self.document_filename} Initialized bearer token provider.")
        except Exception as e:
            logging.error(f"[aoai]{self.document_filename} Failed to initialize bearer token provider: {e}")
            raise

        # Get API key for alternative authentication
        self.api_key = os.getenv('AZURE_OPENAI_KEY')
        
        # Initialize the AzureOpenAI client
        try:
            # Validate endpoint format before attempting to create client
            if self.openai_api_base and '.azure.com' in self.openai_api_base:
                if '.openai.azure.com' not in self.openai_api_base:
                    old_base = self.openai_api_base
                    self.openai_api_base = self.openai_api_base.replace('.azure.com', '.openai.azure.com')
                    logging.warning(f"[aoai]{self.document_filename} Fixed OpenAI endpoint format from {old_base} to {self.openai_api_base}")
            
            # First try with token provider if available
            if not self.api_key:
                self.client = AzureOpenAI(
                    api_version=self.openai_api_version,
                    azure_endpoint=self.openai_api_base,
                    azure_ad_token_provider=self.token_provider,
                    max_retries=self.max_retries
                )
                logging.debug(f"[aoai]{self.document_filename} Initialized AzureOpenAI client with token authentication.")
            else:
                # Fall back to API key if available
                self.client = AzureOpenAI(
                    api_version=self.openai_api_version,
                    azure_endpoint=self.openai_api_base,
                    api_key=self.api_key,
                    max_retries=self.max_retries
                )
                logging.debug(f"[aoai]{self.document_filename} Initialized AzureOpenAI client with API key authentication.")
                
            # Verify the endpoint by logging it
            logging.info(f"[aoai]{self.document_filename} Using Azure OpenAI endpoint: {self.openai_api_base}")
            
        except ClientAuthenticationError as e:
            logging.error(f"[aoai]{self.document_filename} Authentication failed during AzureOpenAI client initialization: {e}")
            logging.error(f"[aoai]{self.document_filename} Please check your AZURE_OPENAI_KEY or Azure AD credentials.")
            raise
        except ValueError as e:
            logging.error(f"[aoai]{self.document_filename} Invalid parameters for AzureOpenAI client: {e}")
            logging.error(f"[aoai]{self.document_filename} API Base: {self.openai_api_base}, API Version: {self.openai_api_version}")
            raise
        except Exception as e:
            logging.error(f"[aoai]{self.document_filename} Failed to initialize AzureOpenAI client: {e}")
            logging.error(f"[aoai]{self.document_filename} API Base: {self.openai_api_base}, API Version: {self.openai_api_version}")
            raise

    def get_completion(self, prompt, image_base64=None, max_tokens=800, retry_after=True):
        """
        Generates a completion for the given prompt using the Azure OpenAI service.

        Args:
            prompt (str): The input prompt for the model.
            image_base64 (str, optional): Base64 encoded image to be included with the prompt. Defaults to None.
            max_tokens (int, optional): The maximum number of tokens to generate. Defaults to 800.
            retry_after (bool, optional): Flag to determine if the method should retry after rate limiting. Defaults to True.

        Returns:
            str: The generated completion.
        """
        one_liner_prompt = prompt.replace('\n', ' ')
        logging.debug(f"[aoai]{self.document_filename} Getting completion for prompt: {one_liner_prompt[:100]}")

        # Truncate prompt if needed
        prompt = self._truncate_input(prompt, self.max_gpt_model_input_tokens)

        try:

            input_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
            ]

            if not image_base64:
                input_messages.append({"role": "user", "content": prompt})
            else:
                input_messages.append({"role": "user", "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url":f"data:image/jpeg;base64,{image_base64}"
                            }
                        } 
                ]})

            response = self.client.chat.completions.create(
                messages=input_messages,
                model=self.openai_gpt_deployment,
                temperature=0.7,
                top_p=0.95,
                max_tokens=max_tokens
            )

            completion = response.choices[0].message.content
            logging.debug(f"[aoai]{self.document_filename} Completion received successfully.")
            return completion

        except RateLimitError as e:
            if not retry_after:
                logging.error(f"[aoai]{self.document_filename} get_completion: Rate limit error occurred after retries: {e}")
                raise

            retry_after_ms = e.response.headers.get('retry-after-ms')
            if retry_after_ms:
                retry_after_ms = int(retry_after_ms)
                logging.info(f"[aoai]{self.document_filename} get_completion: Reached rate limit, retrying after {retry_after_ms} ms")
                time.sleep(retry_after_ms / 1000)
                return self.get_completion(prompt, max_tokens=max_tokens, retry_after=False)
            else:
                logging.error(f"[aoai]{self.document_filename} get_completion: Rate limit error occurred, no 'retry-after-ms' provided: {e}")
                raise

        except ClientAuthenticationError as e:
            logging.error(f"[aoai]{self.document_filename} get_completion: Authentication failed: {e}")
            raise

        except Exception as e:
            logging.error(f"[aoai]{self.document_filename} get_completion: An unexpected error occurred: {e}")
            raise

    def get_embeddings(self, text, retry_after=True):
        """
        Generates embeddings for the given text using the Azure OpenAI service.

        Args:
            text (str): The input text to generate embeddings for.
            retry_after (bool, optional): Flag to determine if the method should retry after rate limiting. Defaults to True.

        Returns:
            list: The generated embeddings.
        """
        one_liner_text = text.replace('\n', ' ')
        logging.debug(f"[aoai]{self.document_filename} Getting embeddings for text: {one_liner_text[:100]}")        
        
        # Truncate in case it is larger than the maximum input tokens
        text = self._truncate_input(text, self.max_embeddings_model_input_tokens)

        try:
            # Validate that we have a proper endpoint and deployment name
            if not self.openai_api_base:
                raise ValueError("OpenAI endpoint is not set properly. Check AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_SERVICE_NAME.")
                
            if not self.openai_embeddings_deployment:
                raise ValueError("OpenAI embeddings deployment is not set properly. Check AZURE_OPENAI_EMBEDDING_DEPLOYMENT.")
                
            logging.debug(f"[aoai]{self.document_filename} Using OpenAI endpoint: {self.openai_api_base}")
            logging.debug(f"[aoai]{self.document_filename} Using embeddings model: {self.openai_embeddings_deployment}")
                
            response = self.client.embeddings.create(
                input=text,
                model=self.openai_embeddings_deployment
            )
            embeddings = response.data[0].embedding
            logging.debug(f"[aoai]{self.document_filename} Embeddings received successfully.")
            return embeddings
        
        except RateLimitError as e:
            if not retry_after:
                logging.error(f"[aoai]{self.document_filename} get_embeddings: Rate limit error occurred after retries: {e}")
                raise

            retry_after_ms = e.response.headers.get('retry-after-ms')
            if retry_after_ms:
                retry_after_ms = int(retry_after_ms)
                logging.info(f"[aoai]{self.document_filename} get_embeddings: Reached rate limit, retrying after {retry_after_ms} ms")
                time.sleep(retry_after_ms / 1000)
                return self.get_embeddings(text, retry_after=False)
            else:
                logging.error(f"[aoai]{self.document_filename} get_embeddings: Rate limit error occurred, no 'retry-after-ms' provided: {e}")
                raise

        except ClientAuthenticationError as e:
            logging.error(f"[aoai]{self.document_filename} get_embeddings: Authentication failed: {e}")
            logging.error(f"[aoai]{self.document_filename} Please check your AZURE_OPENAI_KEY or Azure AD credentials.")
            raise

        except ConnectionError as e:
            logging.error(f"[aoai]{self.document_filename} get_embeddings: Connection error: {e}")
            logging.error(f"[aoai]{self.document_filename} Please check if the endpoint URL is correct: {self.openai_api_base}")
            
            # Test network connectivity to help diagnose the issue
            connectivity_success, connectivity_message = self._test_network_connectivity()
            if not connectivity_success:
                logging.error(f"[aoai]{self.document_filename} Network connectivity test failed: {connectivity_message}")
            else:
                logging.info(f"[aoai]{self.document_filename} Network connectivity test passed: {connectivity_message}")
            
            # Try alternate URL format if connection issue
            if '.openai.azure.com' not in self.openai_api_base and '.azure.com' in self.openai_api_base:
                original_endpoint = self.openai_api_base
                self.openai_api_base = self.openai_api_base.replace('.azure.com', '.openai.azure.com')
                logging.warning(f"[aoai]{self.document_filename} Trying alternate endpoint format: {self.openai_api_base}")
                
                # Reconnect with the new endpoint format
                try:
                    self.client = AzureOpenAI(
                        api_version=self.openai_api_version,
                        azure_endpoint=self.openai_api_base,
                        api_key=self.api_key if self.api_key else None,
                        azure_ad_token_provider=None if self.api_key else self.token_provider,
                        max_retries=self.max_retries
                    )
                    # Try again with the new client
                    return self.get_embeddings(text, retry_after)
                except Exception as retry_e:
                    # Restore original endpoint if retry fails
                    self.openai_api_base = original_endpoint
                    logging.error(f"[aoai]{self.document_filename} Retry with alternate endpoint failed: {retry_e}")
            
            # Check if the URL includes http/https protocol
            if not self.openai_api_base.startswith("http"):
                logging.error(f"[aoai]{self.document_filename} Endpoint URL is missing protocol (http/https): {self.openai_api_base}")
                
            raise

        except Exception as e:
            error_str = str(e)
            logging.error(f"[aoai]{self.document_filename} get_embeddings: An unexpected error occurred: {e}")
            logging.error(f"[aoai]{self.document_filename} Details - API Base: {self.openai_api_base}, API Version: {self.openai_api_version}, Deployment: {self.openai_embeddings_deployment}")
            
            # More detailed diagnostics for common error types
            if 'ConnectionError' in error_str or 'Connection' in error_str:
                # Test network connectivity to help diagnose the issue
                connectivity_success, connectivity_message = self._test_network_connectivity()
                if not connectivity_success:
                    logging.error(f"[aoai]{self.document_filename} Network connectivity test failed: {connectivity_message}")
                else:
                    logging.info(f"[aoai]{self.document_filename} Network connectivity test passed: {connectivity_message}")
                    
                logging.error(f"[aoai]{self.document_filename} This appears to be a network connection issue. Please check your network settings and firewall rules.")
            elif 'DeserializationError' in error_str or 'ValueError' in error_str:
                logging.error(f"[aoai]{self.document_filename} This appears to be a response parsing error. The API might be returning an unexpected format.")
            elif 'Timeout' in error_str:
                logging.error(f"[aoai]{self.document_filename} This appears to be a timeout error. The API might be experiencing high load or your network connection is slow.")
            
            raise

    def _truncate_input(self, text, max_tokens):
        """
        Truncates the input text to ensure it does not exceed the maximum number of tokens.

        Args:
            text (str): The input text to truncate.
            max_tokens (int): The maximum number of tokens allowed.

        Returns:
            str: The truncated text.
        """
        input_tokens = GptTokenEstimator().estimate_tokens(text)
        if input_tokens > max_tokens:
            logging.info(f"[aoai]{self.document_filename} Input size {input_tokens} exceeded maximum token limit {max_tokens}, truncating...")
            step_size = 1  # Initial step size
            iteration = 0  # Iteration counter

            while GptTokenEstimator().estimate_tokens(text) > max_tokens:
                text = text[:-step_size]
                iteration += 1

                # Increase step size exponentially every 5 iterations
                if iteration % 5 == 0:
                    step_size = min(step_size * 2, 100)

        return text    

    def _test_network_connectivity(self):
        """
        Tests network connectivity to the OpenAI endpoint.
        Returns a tuple of (success, message) where success is a boolean.
        """
        import socket
        from urllib.parse import urlparse
        
        if not self.openai_api_base:
            return False, "OpenAI endpoint URL is not set"
            
        try:
            # Parse the URL to get the hostname
            parsed_url = urlparse(self.openai_api_base)
            host = parsed_url.netloc
            
            # If we couldn't parse the netloc, try the path (could be malformed URL)
            if not host and parsed_url.path:
                host = parsed_url.path
                
            if not host:
                return False, f"Could not parse hostname from endpoint URL: {self.openai_api_base}"
                
            # Remove port number if present
            if ":" in host:
                host = host.split(":")[0]
                
            # Try to resolve the hostname
            try:
                socket.gethostbyname(host)
                return True, f"Successfully resolved hostname: {host}"
            except socket.gaierror:
                return False, f"Could not resolve hostname: {host}. Check DNS or internet connection."
                
        except Exception as e:
            return False, f"Error testing network connectivity: {e}"

class GptTokenEstimator:
    GPT2_TOKENIZER = tiktoken.get_encoding("gpt2")

    def estimate_tokens(self, text: str) -> int:
        """
        Estimates the number of tokens in the given text using the GPT-2 tokenizer.

        Args:
            text (str): The input text.

        Returns:
            int: The estimated number of tokens.
        """
        return len(self.GPT2_TOKENIZER.encode(text))
