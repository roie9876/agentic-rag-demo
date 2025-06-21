import logging
import os
import base64

from .chunkers.doc_analysis_chunker import DocAnalysisChunker
from .chunkers.multimodal_chunker import MultimodalChunker
from .chunkers.langchain_chunker import LangChainChunker
from .chunkers.spreadsheet_chunker import SpreadsheetChunker
from .chunkers.transcription_chunker import TranscriptionChunker
from .chunkers.json_chunker import JSONChunker
from .chunkers.nl2sql_chunker import NL2SQLChunker

from tools.document_intelligence_client import DocumentIntelligenceClientWrapper
from utils import get_filename_from_data, get_file_extension

class ChunkerFactory:
    """Factory class to create appropriate chunker based on file extension."""
    
    def __init__(self):
        docint_client = DocumentIntelligenceClientWrapper()
        self.docint_40_api = docint_client.docint_40_api 
        _multimodality = os.getenv("MULTIMODAL", "false").lower()
        self.multimodality = _multimodality in ["true", "1", "yes"]

    def get_chunker(self, data, multimodal=False, multimodal_processor=None, openai_client=None):
        """
        Get the appropriate chunker based on the document type and multimodal setting.
        
        Args:
            data: Document data
            multimodal: Whether to use multimodal processing
            multimodal_processor: Instance of MultimodalProcessor
            openai_client: OpenAI client for image captioning (optional)
            
        Returns:
            Chunker: The appropriate chunker instance
        """
        if multimodal and multimodal_processor:
            return MultimodalChunker(data, multimodal_processor, openai_client)
            
        filename = get_filename_from_data(data)
        logging.info(f"[chunker_factory][{filename}] Creating chunker")

        extension = get_file_extension(filename)
        
        # Enhanced logging for user information
        processing_info = {
            'vtt': ('TranscriptionChunker', 'Video/Audio transcript processing'),
            'json': ('JSONChunker', 'Structured JSON data extraction'),
            'xlsx': ('SpreadsheetChunker', 'Excel spreadsheet data parsing'), 
            'xls': ('SpreadsheetChunker', 'Excel spreadsheet data parsing'),
            'pdf': ('DocAnalysisChunker' if not self.multimodality else 'MultimodalChunker', 
                   'Azure Document Intelligence with OCR' + (' + multimodal figure processing' if self.multimodality else '')),
            'png': ('DocAnalysisChunker' if not self.multimodality else 'MultimodalChunker',
                   'Azure Document Intelligence image analysis' + (' + multimodal processing' if self.multimodality else '')),
            'jpeg': ('DocAnalysisChunker' if not self.multimodality else 'MultimodalChunker', 
                    'Azure Document Intelligence image analysis' + (' + multimodal processing' if self.multimodality else '')),
            'jpg': ('DocAnalysisChunker' if not self.multimodality else 'MultimodalChunker',
                   'Azure Document Intelligence image analysis' + (' + multimodal processing' if self.multimodality else '')),
            'bmp': ('DocAnalysisChunker' if not self.multimodality else 'MultimodalChunker',
                   'Azure Document Intelligence image analysis' + (' + multimodal processing' if self.multimodality else '')),
            'tiff': ('DocAnalysisChunker' if not self.multimodality else 'MultimodalChunker',
                    'Azure Document Intelligence image analysis' + (' + multimodal processing' if self.multimodality else '')),
            'docx': ('DocAnalysisChunker' if self.docint_40_api else 'LangChainChunker (fallback)', 
                    'Azure Document Intelligence layout analysis' + (' + multimodal processing' if self.multimodality else '') if self.docint_40_api else 'Basic text extraction (Doc Intelligence 4.0 not available)'),
            'pptx': ('DocAnalysisChunker' if self.docint_40_api else 'LangChainChunker (fallback)',
                    'Azure Document Intelligence presentation analysis' + (' + multimodal processing' if self.multimodality else '') if self.docint_40_api else 'Basic text extraction (Doc Intelligence 4.0 not available)'),
            'nl2sql': ('NL2SQLChunker', 'Natural language to SQL processing'),
        }
        
        if extension in processing_info:
            chunker_type, description = processing_info[extension]
            logging.info(f"[chunker_factory][{filename}] Using {chunker_type}: {description}")
        else:
            logging.info(f"[chunker_factory][{filename}] Using LangChainChunker: General text processing")
        
        if extension == 'vtt':
            return TranscriptionChunker(data)
        elif extension == 'json':
            return JSONChunker(data)  
        elif extension in ('xlsx', 'xls'):
            return SpreadsheetChunker(data)
        elif extension in ('pdf', 'png', 'jpeg', 'jpg', 'bmp', 'tiff'):
            if self.multimodality:
                # Create MultimodalProcessor if not provided
                if not multimodal_processor:
                    from .multimodal_processor import MultimodalProcessor
                    multimodal_processor = MultimodalProcessor()
                try:
                    return MultimodalChunker(data, multimodal_processor, openai_client)
                except Exception as e:
                    logging.warning(f"[chunker_factory][{filename}] Multimodal processing failed: {e}. Falling back to DocAnalysisChunker.")
                    try:
                        return DocAnalysisChunker(data)
                    except Exception as e2:
                        logging.warning(f"[chunker_factory][{filename}] DocAnalysisChunker also failed: {e2}. Falling back to LangChainChunker for basic text extraction.")
                        return LangChainChunker(data)
            else:
                try:
                    return DocAnalysisChunker(data)
                except Exception as e:
                    logging.warning(f"[chunker_factory][{filename}] DocAnalysisChunker failed: {e}. Falling back to LangChainChunker for basic text extraction.")
                    return LangChainChunker(data)
        elif extension in ('docx', 'pptx'):
            if self.docint_40_api:
                if self.multimodality:
                    # Create MultimodalProcessor if not provided
                    if not multimodal_processor:
                        from .multimodal_processor import MultimodalProcessor
                        multimodal_processor = MultimodalProcessor()
                    return MultimodalChunker(data, multimodal_processor, openai_client)
                else:
                    return DocAnalysisChunker(data)
            else:
                logging.warning(f"[chunker_factory][{filename}] Document Intelligence 4.0 not available for {extension}. Falling back to LangChainChunker.")
                # Fallback to LangChain chunker instead of throwing error
                return LangChainChunker(data)
        elif extension in ('nl2sql'):
            return NL2SQLChunker(data)
        else:
            return LangChainChunker(data)
        
    @staticmethod
    def get_supported_extensions():
        """
        Get a comma-separated list of supported file extensions.

        Returns:
            str: A comma-separated list of supported file extensions.
        """
        extensions = [
            'vtt',
            'xlsx', 'xls',
            'pdf', 'png', 'jpeg', 'jpg', 'bmp', 'tiff',
            'docx', 'pptx', 'json'
        ]
        return ', '.join(extensions)

class MultimodalChunker:
    """Chunker that processes documents for multimodal content extraction."""
    
    def __init__(self, data, multimodal_processor, openai_client=None):
        self.data = data
        self.multimodal_processor = multimodal_processor
        self.openai_client = openai_client
        self.chunks = []
        
    def get_chunks(self):
        """
        Process the document to extract text chunks and associated images with AI-generated descriptions.
        
        Returns:
            list: List of chunks with text content and related image information
            structured for unified multimodal indexing
        """
        filename = get_filename_from_data(self.data)
        
        # DEBUG: Log the raw documentBytes before decoding
        raw_doc_bytes = self.data.get("documentBytes", "")
        logging.info(f"[MultimodalChunker][{filename}] Raw documentBytes type: {type(raw_doc_bytes)}")
        
        if isinstance(raw_doc_bytes, str):
            logging.info(f"[MultimodalChunker][{filename}] Raw documentBytes string length: {len(raw_doc_bytes):,} chars")
            # Log first 100 characters to see if it's base64 or something else
            logging.info(f"[MultimodalChunker][{filename}] First 100 chars: {repr(raw_doc_bytes[:100])}")
        elif isinstance(raw_doc_bytes, bytes):
            logging.info(f"[MultimodalChunker][{filename}] Raw documentBytes already bytes: {len(raw_doc_bytes):,} bytes")
            document_bytes = raw_doc_bytes  # No decoding needed
        else:
            logging.error(f"[MultimodalChunker][{filename}] Unexpected documentBytes type: {type(raw_doc_bytes)}")
            document_bytes = b""
        
        # Only decode if we have a string (base64 encoded)
        if isinstance(raw_doc_bytes, str):
            try:
                document_bytes = base64.b64decode(raw_doc_bytes)
                logging.info(f"[MultimodalChunker][{filename}] After base64 decode: {len(document_bytes):,} bytes")
                
                # Verify the decoded content
                if filename.endswith('.pdf'):
                    if document_bytes.startswith(b'%PDF-'):
                        logging.info(f"[MultimodalChunker][{filename}] ✅ Valid PDF after decode")
                    else:
                        logging.error(f"[MultimodalChunker][{filename}] ❌ Invalid PDF after decode!")
                        logging.info(f"[MultimodalChunker][{filename}] First 50 bytes: {repr(document_bytes[:50])}")
                        
            except Exception as e:
                logging.error(f"[MultimodalChunker][{filename}] Base64 decode failed: {e}")
                document_bytes = b""
        
        if not document_bytes:
            logging.error(f"[MultimodalChunker][{filename}] No valid document bytes available after decoding. Skipping chunk creation.")
            return []
        
        # Use enhanced processing if OpenAI client is available for image descriptions
        if self.openai_client:
            try:
                processed_content = self.multimodal_processor.process_document_with_images(
                    document_bytes, filename, self.openai_client
                )
                logging.info(f"Enhanced multimodal processing completed for {filename}")
            except Exception as e:
                logging.warning(f"Enhanced processing failed for {filename}: {e}. Falling back to basic processing.")
                processed_content = self.multimodal_processor.process_document(document_bytes, filename)
        else:
            # Fallback to basic processing without image descriptions
            processed_content = self.multimodal_processor.process_document(document_bytes, filename)
        
        if not processed_content:
            return []
            
        # Group text segments and images by page
        pages = {}
        
        # Group text by page - with error handling for missing fields
        if "text_segments" in processed_content:
            for segment in processed_content.get("text_segments", []):
                try:
                    page_num = segment.get("page_number", 0)  # Default to page 0 if missing
                    if page_num not in pages:
                        pages[page_num] = {"text": [], "images": []}
                    content = segment.get("content", "")  # Default to empty if missing
                    if content:
                        # Ensure content is always a string
                        content_str = str(content) if not isinstance(content, str) else content
                        pages[page_num]["text"].append(content_str)
                except Exception as e:
                    logging.warning(f"Error processing text segment in {filename}: {str(e)}")
        
        # Group images by page
        if "images" in processed_content:
            for image in processed_content.get("images", []):
                try:
                    page_num = image.get("page_number", 0)  # Default to page 0 if missing
                    if page_num not in pages:
                        pages[page_num] = {"text": [], "images": []}
                    url = image.get("url")  # Get the image URL
                    if url:
                        # Store more details for retrieval processes
                        image["retrieval_path"] = "direct" if url.startswith("http") else "blob"
                        pages[page_num]["images"].append(image)
                except Exception as e:
                    logging.warning(f"Error processing image in {filename}: {str(e)}")
        
        # Create chunks from the grouped content with additional metadata for retrieval
        chunks = []
        for page_num, content in pages.items():
            # Extract image URLs for relatedImages field
            image_urls = [img["url"] for img in content["images"]]
            
            # Keep individual image captions for captionVector generation
            image_captions = [img.get("caption", "") for img in content["images"] if img.get("caption")]
            
            # Add more detailed image information for retrieval systems
            image_details = [{
                "url": img["url"],
                "caption": img.get("caption", ""),
                "retrieval_path": img.get("retrieval_path", "direct"),
                "width": img.get("width"),
                "height": img.get("height")
            } for img in content["images"]]
            
            chunk = {
                "content": self._safe_join_text(content["text"], filename),
                "contentVector": None,  # Will be generated during embedding process
                "imageCaptions": image_captions,
                "captionVector": None,  # Will be generated during embedding process
                "relatedImages": image_urls,
                "imageDetails": image_details,  # Added for retrieval systems
                "page_number": page_num,
                "filename": filename,
                "isMultimodal": len(image_urls) > 0,  # Flag to indicate multimodal content
                "retrievalHints": {
                    "requiresImageProcessing": len(image_urls) > 0,
                    "imageCount": len(image_urls)
                }
            }
            chunks.append(chunk)
            
        return chunks

    def _safe_join_text(self, text_list, filename=""):
        """
        Safely join text items, ensuring all items are strings and providing 
        detailed error information if the join fails.
        """
        try:
            # Ensure all items are strings
            safe_text_list = []
            for i, item in enumerate(text_list):
                if isinstance(item, str):
                    safe_text_list.append(item)
                elif isinstance(item, dict):
                    # If it's a dict, try to extract meaningful content
                    if "content" in item:
                        safe_text_list.append(str(item["content"]))
                    else:
                        logging.warning(f"[{filename}] Text item {i} is dict without 'content' key: {item}")
                        safe_text_list.append(str(item))
                else:
                    # Convert any other type to string
                    logging.warning(f"[{filename}] Text item {i} is {type(item)}, converting to string: {item}")
                    safe_text_list.append(str(item))
            
            return "\n".join(safe_text_list)
            
        except Exception as e:
            logging.error(f"[{filename}] Failed to join text items: {e}")
            logging.error(f"[{filename}] Text list types: {[type(item) for item in text_list]}")
            logging.error(f"[{filename}] Text list sample: {text_list[:3] if len(text_list) > 3 else text_list}")
            # Return empty string as fallback
            return ""
