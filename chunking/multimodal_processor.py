import logging
import os
import base64
import uuid

# Import file format detector
try:
    from utils.file_format_detector import FileFormatDetector
except ImportError:
    # Fallback import path
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from utils.file_format_detector import FileFormatDetector

# Use our working Document Intelligence client instead of Azure SDK
try:
    from tools.doc_intelligence import DocumentIntelligenceClient as WorkingDocIntelClient
except ImportError:
    # Fallback import path
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from tools.doc_intelligence import DocumentIntelligenceClient as WorkingDocIntelClient

# Only import Azure Storage for blob operations
try:
    from azure.storage.blob import BlobServiceClient
    BLOB_STORAGE_AVAILABLE = True
except ImportError:
    BLOB_STORAGE_AVAILABLE = False
    logging.warning("Azure Storage SDK not available. Image storage will be disabled.")

def validate_and_detect_format(document_bytes, filename):
    """
    Validate and detect the real format of a document file.
    
    Args:
        document_bytes: Binary content of the document
        filename: Filename for logging
        
    Returns:
        tuple: (is_valid, detected_format, content_type, message)
    """
    try:
        # Check for truly empty files
        if len(document_bytes) < 10:
            return False, None, None, f"File is too small ({len(document_bytes)} bytes) - likely empty"
        
        # Detect the real file format
        detected_format, detection_reason = FileFormatDetector.detect_format(document_bytes, filename)
        
        if detected_format is None:
            logging.warning(f"Could not detect format for {filename}: {detection_reason}")
            
            # Try enhanced detection as fallback
            logging.info(f"Attempting enhanced detection for {filename}...")
            
            enhanced_format, enhanced_content_type, enhanced_reason = _enhanced_format_detection(document_bytes, filename)
            
            if enhanced_format:
                # Check if enhanced detected format is supported
                if FileFormatDetector.is_format_supported_by_document_intelligence(enhanced_format):
                    logging.info(f"Enhanced detection succeeded for {filename}: {enhanced_format} ({enhanced_reason})")
                    return True, enhanced_format, enhanced_content_type, f"Enhanced detection: {enhanced_reason}"
                else:
                    logging.warning(f"Enhanced detection found unsupported format for {filename}: {enhanced_format}")
                    return False, enhanced_format, None, f"Enhanced detected format '{enhanced_format}' is not supported by Document Intelligence"
            else:
                logging.warning(f"Enhanced detection also failed for {filename}: {enhanced_reason}")
                # Don't process files we can't identify at all
                return False, None, None, f"Could not detect file format: {detection_reason}. Enhanced detection: {enhanced_reason}"
        
        # Check if detected format is supported by Document Intelligence
        if not FileFormatDetector.is_format_supported_by_document_intelligence(detected_format):
            # For plain text files that might actually be HTML, try HTML as fallback
            original_ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
            if detected_format == 'txt' and original_ext == 'pdf':
                logging.info(f"Plain text detected in PDF file {filename}, attempting to process as HTML")
                return True, 'html', 'text/html', f"Plain text in PDF file processed as HTML: {detection_reason}"
            return False, detected_format, None, f"Detected format '{detected_format}' is not supported by Document Intelligence"
        
        # Get appropriate content type
        content_type = FileFormatDetector.get_content_type(detected_format)
        
        # Log format detection results
        original_ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
        if detected_format != original_ext:
            logging.info(f"Format mismatch detected for {filename}: original extension '{original_ext}', detected format '{detected_format}' ({detection_reason})")
        else:
            logging.info(f"Format confirmed for {filename}: '{detected_format}' ({detection_reason})")
        
        return True, detected_format, content_type, f"Detected as {detected_format}: {detection_reason}"
        
    except Exception as e:
        logging.warning(f"Format detection error for {filename}: {str(e)}, but will attempt processing")
        return True, None, None, f"Format detection error: {str(e)}, but will attempt processing"

def _enhanced_format_detection(file_bytes, filename):
    """
    Enhanced format detection for edge cases where standard detection fails.
    
    Args:
        file_bytes: Binary content of the file
        filename: Original filename
        
    Returns:
        tuple: (detected_format, content_type, reason)
    """
    if not file_bytes or len(file_bytes) < 4:
        return None, None, "File too small or empty"
    
    # Get file extension from filename
    file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    # For files with .pdf extension, check if it's actually a PDF
    if file_ext == 'pdf':
        # First check if it has valid PDF headers
        if file_bytes.startswith(b'%PDF-'):
            # Looks like a real PDF, but might be corrupted if very small
            if len(file_bytes) < 1000:
                logging.warning(f"PDF file is very small ({len(file_bytes)} bytes), might be corrupted")
            return 'pdf', 'application/pdf', "Valid PDF header detected"
        
        # No PDF header found - check what it actually contains
        first_1kb = file_bytes[:1024].lower()
        
        # Check for HTML content (more comprehensive)
        html_indicators = [
            b'<!doctype html',
            b'<html',
            b'<head>',
            b'<body>',
            b'<meta',
            b'<title>',
            b'<div',
            b'<script',
            b'<style'
        ]
        html_score = sum(1 for indicator in html_indicators if indicator in first_1kb)
        
        if html_score >= 2 or b'<!doctype html' in first_1kb:
            return 'html', 'text/html', f"HTML content detected in PDF file (score: {html_score})"
        
        # Check for XML content
        if b'<?xml' in first_1kb or (b'<' in first_1kb and b'xmlns' in first_1kb):
            return 'xml', 'application/xml', "XML content detected in PDF file"
        
        # Check for JSON content
        stripped = file_bytes.strip()
        if (stripped.startswith(b'{') and stripped.endswith(b'}')) or (stripped.startswith(b'[') and stripped.endswith(b']')):
            return 'json', 'application/json', "JSON content detected in PDF file"
        
        # Check if it's mostly printable text
        try:
            decoded = file_bytes.decode('utf-8', errors='ignore')
            if len(decoded.strip()) > 10:
                printable_count = sum(1 for c in decoded if c.isprintable() or c.isspace())
                printable_ratio = printable_count / len(decoded)
                
                if printable_ratio > 0.8:
                    # For small files that should be processed by Document Intelligence,
                    # prefer HTML over plain text since Document Intelligence doesn't support plain text
                    if len(file_bytes) < 5000 and (b'<' in file_bytes and b'>' in file_bytes):
                        return 'html', 'text/html', f"Small file with HTML-like tags (printable ratio: {printable_ratio:.2f})"
                    elif file_ext == 'pdf' and len(file_bytes) < 5000:
                        # For small PDF files that are actually text, try HTML to make them processable by Document Intelligence
                        return 'html', 'text/html', f"Small PDF file with plain text content, processing as HTML (printable ratio: {printable_ratio:.2f})"
                    else:
                        return 'txt', 'text/plain', f"High printable character ratio: {printable_ratio:.2f}"
        except:
            pass
        
        # If we can't identify the content but it doesn't have PDF headers, 
        # it's likely corrupted or not actually a PDF
        return 'txt', 'text/plain', "No PDF header found, treating as plain text"
    
    # Sample first 2KB for analysis for non-PDF files
    first_2kb = file_bytes[:2048].lower()
    
    # Enhanced HTML detection - require higher confidence for non-PDF files
    html_patterns = [
        b'<!doctype html',
        b'<html',
        b'<head>',
        b'<body>',
        b'<meta',
        b'<title>',
        b'<div',
        b'<p>',
        b'<script',
        b'<style',
        b'href=',
        b'src=',
        b'xmlns=',
        b'<br',
        b'<span',
        b'<a ',
    ]
    
    html_score = sum(1 for pattern in html_patterns if pattern in first_2kb)
    
    # Require strong HTML evidence (at least 4 indicators) to override other formats
    if html_score >= 4:
        return 'html', 'text/html', f"Strong HTML detection (score: {html_score})"
    
    # Check for XML content
    if b'<?xml' in first_2kb or (b'<' in first_2kb and b'xmlns' in first_2kb):
        return 'xml', 'application/xml', "Enhanced XML detection"
    
    # Check for JSON content
    stripped = file_bytes.strip()
    if (stripped.startswith(b'{') and stripped.endswith(b'}')) or (stripped.startswith(b'[') and stripped.endswith(b']')):
        return 'json', 'application/json', "Enhanced JSON detection"
    
    # Check for plain text with high confidence
    try:
        decoded = file_bytes.decode('utf-8', errors='ignore')
        if len(decoded.strip()) > 10:  # At least some content
            # Count printable characters (including Unicode)
            printable_count = sum(1 for c in decoded if c.isprintable() or c.isspace())
            printable_ratio = printable_count / len(decoded)
            
            # If most characters are printable, likely text
            if printable_ratio > 0.85:
                # For small files with HTML-like content, try HTML first
                if len(file_bytes) < 5000 and (b'<' in file_bytes and b'>' in file_bytes):
                    return 'html', 'text/html', f"Small file with HTML-like tags (printable ratio: {printable_ratio:.2f})"
                else:
                    return 'txt', 'text/plain', f"High printable character ratio: {printable_ratio:.2f}"
    except:
        pass
    
    # Check for specific patterns that might indicate file type
    if b'javascript' in first_2kb.lower() or b'function(' in first_2kb:
        return 'html', 'text/html', "JavaScript content detected, likely HTML"
    
    if b'css' in first_2kb and (b'{' in first_2kb and b'}' in first_2kb):
        return 'html', 'text/html', "CSS content detected, likely HTML"
    
    # For files with specific extensions, trust the extension as fallback
    extension_map = {
        'docx': ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        'pptx': ('pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
        'xlsx': ('xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        'png': ('png', 'image/png'),
        'jpg': ('jpg', 'image/jpeg'),
        'jpeg': ('jpeg', 'image/jpeg'),
        'bmp': ('bmp', 'image/bmp'),
        'tiff': ('tiff', 'image/tiff'),
    }
    
    if file_ext in extension_map:
        ext, mime_type = extension_map[file_ext]
        return ext, mime_type, f"Trusting {file_ext.upper()} extension"
    
    # If file is very small and we can't detect anything, make an educated guess
    if len(file_bytes) < 1000:
        if b'<' in file_bytes and b'>' in file_bytes and html_score >= 2:
            return 'html', 'text/html', "Small file with HTML-like tags"
        else:
            return 'txt', 'text/plain', "Small unidentified file, assuming plain text"
    
    return None, None, "Enhanced detection could not identify format"

class MultimodalProcessor:
    """
    Handles multimodal content extraction and processing.
    
    This class extracts text and images from documents using Azure Document Processing Service,
    stores images in blob storage, and prepares data for multimodal indexing.
    """
    
    def __init__(self, doc_intelligence_endpoint=None, doc_intelligence_key=None, 
                 blob_connection_string=None, blob_container=None):
        """Initialize the multimodal processor with Azure service configurations."""
        # Try multiple environment variable names for Document Intelligence
        self.doc_intelligence_endpoint = (
            doc_intelligence_endpoint or 
            os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT") or
            os.environ.get("DOCUMENT_INTEL_ENDPOINT") or
            os.environ.get("AZURE_FORMREC_SERVICE") or
            os.environ.get("AZURE_FORMRECOGNIZER_ENDPOINT")
        )
        
        self.doc_intelligence_key = (
            doc_intelligence_key or 
            os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY") or
            os.environ.get("DOCUMENT_INTEL_KEY") or
            os.environ.get("AZURE_FORMREC_KEY") or
            os.environ.get("AZURE_FORMRECOGNIZER_KEY")
        )
        
        self.blob_connection_string = blob_connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        self.blob_container = blob_container or os.environ.get("AZURE_STORAGE_CONTAINER")
        
        # Initialize Document Intelligence client if endpoint is available
        # Note: DocumentIntelligenceClient supports both API key and managed identity authentication
        if self.doc_intelligence_endpoint:
            try:
                self.doc_client = WorkingDocIntelClient()
                logging.info("Document Intelligence client initialized successfully with working client.")
            except Exception as e:
                self.doc_client = None
                logging.warning(f"Failed to initialize Document Intelligence client: {e}")
        else:
            self.doc_client = None
            logging.warning("Document Intelligence endpoint not provided. Multimodal extraction may be limited.")
        
        # Initialize Blob Storage client if connection string is available
        if BLOB_STORAGE_AVAILABLE and self.blob_connection_string and self.blob_container:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.blob_connection_string)
                # Ensure container exists
                container_client = self.blob_service_client.get_container_client(self.blob_container)
                if not container_client.exists():
                    container_client = self.blob_service_client.create_container(self.blob_container)
                self.container_client = container_client
                logging.info("Blob storage initialized successfully.")
            except Exception as e:
                logging.error(f"Failed to initialize blob container: {str(e)}")
                self.blob_service_client = None
                self.container_client = None
        else:
            self.blob_service_client = None
            self.container_client = None
            if not BLOB_STORAGE_AVAILABLE:
                logging.warning("Azure Storage SDK not available. Image storage will not be available.")
            else:
                logging.warning("Blob storage credentials not provided. Image storage will not be available.")
    
    def process_document(self, document_bytes, filename):
        """
        Process a document to extract text and images.
        
        Args:
            document_bytes: Binary content of the document
            filename: Original filename of the document
            
        Returns:
            dict: Dictionary containing processed content with text segments and image information
        """
        # DEBUG: Log file size at entry point
        file_size = len(document_bytes) if document_bytes else 0
        logging.info(f"[MultimodalProcessor][{filename}] RECEIVED FILE SIZE: {file_size:,} bytes")
        
        if file_size > 0:
            # Log first 50 bytes to check content type
            first_50 = document_bytes[:50]
            logging.info(f"[MultimodalProcessor][{filename}] First 50 bytes: {repr(first_50)}")
            
            # Expected size check for debugging
            if filename.endswith('.pdf') and file_size < 1000:
                logging.error(f"[MultimodalProcessor][{filename}] ⚠️ SUSPICIOUS: PDF file only {file_size} bytes - expected much larger!")
        
        if not self.doc_client:
            logging.error("Document Intelligence client not initialized. Cannot process document.")
            return None
            
        # Validate and detect file format
        is_valid, detected_format, content_type, message = validate_and_detect_format(document_bytes, filename)
        if not is_valid:
            logging.error(f"Invalid file '{filename}': {message}")
            raise Exception(f"Invalid file '{filename}': {message}")
        
        logging.info(f"Processing {filename}: {message}")
            
        try:
            # Try multiple approaches to upload the file to Document Intelligence
            # This mimics what the Azure portal UI might be doing
            result = self._try_document_intelligence_with_retries(
                document_bytes, filename, detected_format, content_type
            )
            
            if result:
                # Process extracted content
                return self._process_extraction_result(result, filename)
            else:
                # If all Document Intelligence attempts fail, use fallback extraction
                logging.warning(f"All Document Intelligence attempts failed for {filename}, using fallback extraction")
                return self._fallback_text_extraction(document_bytes, filename, detected_format)
            
        except Exception as e:
            logging.error(f"Error processing document for multimodal extraction: {str(e)}")
            
            # Enhanced fallback for all file types, especially PDFs that Document Intelligence rejects
            logging.info(f"Attempting fallback text extraction for {filename}")
            try:
                # Determine format for fallback - use detected format or guess from filename
                fallback_format = detected_format
                if not fallback_format:
                    # Guess format from filename extension
                    ext = filename.split('.')[-1].lower() if '.' in filename else 'txt'
                    fallback_format = ext
                
                fallback_result = self._fallback_text_extraction(document_bytes, filename, fallback_format)
                if fallback_result:
                    logging.info(f"Fallback extraction successful for {filename}")
                    return fallback_result
                else:
                    logging.warning(f"Fallback extraction returned no results for {filename}")
            except Exception as fallback_error:
                logging.error(f"Fallback extraction failed for {filename}: {fallback_error}")
            
            raise  # Re-raise original exception if all fallbacks fail
    
    def _process_extraction_result(self, result, filename):
        """Process the extraction result to identify text segments and images."""
        processed_content = {
            "text_segments": [],
            "images": []
        }
        
        # Process text content from our Document Intelligence client format
        # The result format from our client has 'content' and 'pages' keys
        
        # Extract full content and split into segments
        content = result.get('content', '')
        pages = result.get('pages', [])
        
        if content:
            # Split content into meaningful segments (paragraphs)
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            # Estimate page numbers for paragraphs (simple heuristic)
            total_pages = len(pages) if pages else 1
            paragraphs_per_page = max(1, len(paragraphs) // total_pages)
            
            for i, paragraph in enumerate(paragraphs):
                estimated_page = min(total_pages, (i // paragraphs_per_page) + 1)
                processed_content["text_segments"].append({
                    "content": paragraph,
                    "page_number": estimated_page
                })
        
        # Process images if found in the result
        # Our Document Intelligence client may have images in the 'figures' or similar structure
        if 'figures' in result:
            logging.info(f"Found {len(result['figures'])} figures in {filename}")
            for i, figure in enumerate(result['figures']):
                try:
                    image_id = f"{filename}_{i}_{uuid.uuid4().hex[:8]}"
                    
                    # Document Intelligence figures contain bounding regions and elements
                    # We need to extract the actual image data from the original document
                    # For now, we'll create a placeholder that can be processed later
                    
                    page_num = 1
                    if 'boundingRegions' in figure and figure['boundingRegions']:
                        page_num = figure['boundingRegions'][0].get('pageNumber', 1)
                    
                    # Create image info with figure metadata
                    image_info = {
                        "image_id": image_id,
                        "url": f"figure_{i}_page_{page_num}",  # Placeholder URL
                        "page_number": page_num,
                        "caption": figure.get('caption', ''),
                        "figure_data": figure,  # Store the full figure data for later processing
                        "needs_processing": True  # Flag to indicate this needs image extraction
                    }
                    processed_content["images"].append(image_info)
                    
                except Exception as e:
                    logging.warning(f"Failed to process figure {i} in {filename}: {e}")
        
        # Alternative: Extract images from pages if available
        for page_idx, page in enumerate(pages):
            if 'figures' in page:
                logging.info(f"Found {len(page['figures'])} figures in page {page_idx + 1} of {filename}")
                for fig_idx, figure in enumerate(page['figures']):
                    try:
                        image_id = f"{filename}_p{page_idx + 1}_f{fig_idx}_{uuid.uuid4().hex[:8]}"
                        
                        # Extract image if it has content
                        if 'content' in figure or 'elements' in figure:
                            image_info = {
                                "image_id": image_id,
                                "url": f"page_{page_idx + 1}_figure_{fig_idx}",
                                "page_number": page_idx + 1,
                                "caption": figure.get('caption', ''),
                                "figure_data": figure,
                                "needs_processing": True
                            }
                            processed_content["images"].append(image_info)
                            
                    except Exception as e:
                        logging.warning(f"Failed to process page {page_idx + 1} figure {fig_idx}: {e}")
        
        return processed_content
    
    def _store_image(self, image_bytes, image_name):
        """Store an image in blob storage and return its URL."""
        if not BLOB_STORAGE_AVAILABLE:
            logging.warning("Azure Storage SDK not available. Cannot store images.")
            return None
            
        if not self.container_client:
            logging.warning("Blob storage not configured. Cannot store images.")
            return None
            
        try:
            blob_client = self.container_client.get_blob_client(image_name)
            blob_client.upload_blob(image_bytes, overwrite=True)
            return blob_client.url
        except Exception as e:
            logging.error(f"Failed to upload image to blob storage: {str(e)}")
            return None
            
    def extract_images_from_pdf(self, document_bytes, filename):
        """
        Extract actual image data from PDF using PyMuPDF (fitz).
        This method extracts the raw image bytes that can be processed by GPT-4o.
        """
        try:
            import fitz  # PyMuPDF
            import io
            
            # Open PDF from bytes
            pdf_doc = fitz.open(stream=document_bytes, filetype="pdf")
            extracted_images = []
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Get image data
                        xref = img[0]
                        pix = fitz.Pixmap(pdf_doc, xref)
                        
                        # Convert to PNG if not already
                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            img_data = pix.tobytes("png")
                        else:  # CMYK: convert to RGB first
                            pix1 = fitz.Pixmap(fitz.csRGB, pix)
                            img_data = pix1.tobytes("png")
                            pix1 = None
                        
                        # Create image info
                        image_info = {
                            "image_id": f"{filename}_p{page_num + 1}_img{img_index}",
                            "page_number": page_num + 1,
                            "image_data": img_data,
                            "width": pix.width,
                            "height": pix.height,
                            "format": "png"
                        }
                        extracted_images.append(image_info)
                        
                        pix = None  # Clean up
                        
                    except Exception as e:
                        logging.warning(f"Failed to extract image {img_index} from page {page_num + 1}: {e}")
                        continue
            
            pdf_doc.close()
            return extracted_images
            
        except ImportError:
            logging.warning("PyMuPDF not available. Cannot extract images from PDF.")
            return []
        except Exception as e:
            logging.error(f"Error extracting images from PDF: {e}")
            return []

    def generate_image_captions_with_gpt4o(self, image_data_list, openai_client):
        """
        Generate captions for images using GPT-4o vision capabilities.
        
        Args:
            image_data_list: List of image data (bytes)
            openai_client: Initialized OpenAI client
            
        Returns:
            list: Generated captions for each image
        """
        if not image_data_list:
            return []
            
        captions = []
        
        for i, image_data in enumerate(image_data_list):
            try:
                # Convert image bytes to base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # Prepare message for GPT-4o
                messages = [
                    {
                        "role": "system", 
                        "content": "You are an AI assistant that describes images concisely and accurately. Provide a clear, detailed description of what you see in the image, including any text, diagrams, charts, or notable visual elements."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please describe this image in detail. What do you see?"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ]
                
                # Use GPT-4o (which has vision capabilities)
                response = openai_client.chat.completions.create(
                    model="gpt-4o",  # GPT-4o has built-in vision
                    messages=messages,
                    max_tokens=300,
                    temperature=0.1
                )
                
                caption = response.choices[0].message.content.strip()
                captions.append(caption)
                logging.info(f"Generated caption for image {i + 1}: {caption[:100]}...")
                
            except Exception as e:
                logging.error(f"Error generating caption for image {i + 1}: {str(e)}")
                captions.append(f"Image {i + 1}: Unable to generate description")
                
        return captions

    def process_document_with_images(self, document_bytes, filename, openai_client=None):
        """
        Enhanced document processing that extracts both text and images with descriptions.
        
        Args:
            document_bytes: Binary content of the document
            filename: Original filename
            openai_client: OpenAI client for image captioning
            
        Returns:
            dict: Enhanced processed content with image descriptions
        """
        # First, get the text analysis from Document Intelligence
        base_result = self.process_document(document_bytes, filename)
        
        if not base_result:
            return None
            
        # Then extract actual images from the PDF
        extracted_images = self.extract_images_from_pdf(document_bytes, filename)
        
        if extracted_images and openai_client:
            logging.info(f"Extracted {len(extracted_images)} images from {filename}")
            
            # Generate captions for extracted images
            image_data_list = [img["image_data"] for img in extracted_images]
            captions = self.generate_image_captions_with_gpt4o(image_data_list, openai_client)
            
            # Store images in blob storage and update with captions
            enhanced_images = []
            for i, (img_info, caption) in enumerate(zip(extracted_images, captions)):
                try:
                    # Store image in blob storage
                    image_filename = f"{img_info['image_id']}.png"
                    image_url = self._store_image(img_info["image_data"], image_filename)
                    
                    if image_url:
                        enhanced_image = {
                            "image_id": img_info["image_id"],
                            "url": image_url,
                            "page_number": img_info["page_number"],
                            "caption": caption,
                            "width": img_info["width"],
                            "height": img_info["height"],
                            "format": img_info["format"]
                        }
                        enhanced_images.append(enhanced_image)
                        
                except Exception as e:
                    logging.error(f"Failed to process image {i}: {e}")
            
            # Replace the placeholder images with actual processed images
            base_result["images"] = enhanced_images
            logging.info(f"Successfully processed {len(enhanced_images)} images with captions")
        
        return base_result

    def _fallback_text_extraction(self, document_bytes, filename, detected_format):
        """
        Fallback text extraction when Document Intelligence fails.
        Handles HTML, XML, JSON, and plain text files.
        
        Args:
            document_bytes: Binary content of the document
            filename: Original filename 
            detected_format: Format detected by FileFormatDetector
            
        Returns:
            dict: Simple text extraction result compatible with multimodal processing
        """
        logging.info(f"Using fallback text extraction for {filename} (format: {detected_format})")
        
        try:
            # Handle different format types
            if detected_format == 'pdf':
                # Try to extract text from PDF using PyMuPDF if available
                extracted_text = self._extract_text_from_pdf_fallback(document_bytes)
                if not extracted_text:
                    # If PDF extraction fails completely, try treating as plain text as last resort
                    logging.info(f"PDF extraction failed, attempting plain text extraction as last resort for {filename}")
                    try:
                        # For very small files, show what we can decode
                        text_attempt = document_bytes.decode('utf-8', errors='ignore')
                        if len(text_attempt.strip()) > 10:  # At least some meaningful content
                            extracted_text = f"[Content decoded as text from corrupted PDF]:\n{text_attempt}"
                        else:
                            # File is too corrupted/small to extract anything meaningful
                            extracted_text = f"[File appears to be corrupted or too small ({len(document_bytes)} bytes) to extract meaningful content]"
                    except Exception:
                        extracted_text = f"[Unable to extract any content from corrupted PDF file ({len(document_bytes)} bytes)]"
            else:
                # Decode the content as UTF-8 text for other formats
                text_content = document_bytes.decode('utf-8', errors='ignore')
                
                if detected_format == 'html':
                    # Simple HTML text extraction
                    extracted_text = self._extract_text_from_html(text_content)
                elif detected_format == 'xml':
                    # Simple XML text extraction
                    extracted_text = self._extract_text_from_xml(text_content)
                elif detected_format == 'json':
                    # JSON pretty print
                    try:
                        import json
                        parsed = json.loads(text_content)
                        extracted_text = json.dumps(parsed, indent=2, ensure_ascii=False)
                    except:
                        extracted_text = text_content
                else:
                    # Plain text or unknown format
                    extracted_text = text_content
            
            # Clean up the text
            extracted_text = self._clean_extracted_text(extracted_text)
            
            if not extracted_text.strip():
                logging.warning(f"No text content extracted from {filename}")
                return None
            
            # Create a simple result structure compatible with the rest of the pipeline
            # Format the result to match what _process_extraction_result expects
            result = {
                'content': extracted_text,
                'pages': [
                    {
                        'page_number': 1,
                        'content': extracted_text
                    }
                ],
                'extraction_method': 'fallback_text',
                'detected_format': detected_format,
                'figures': []  # No figures in fallback extraction
            }
            
            logging.info(f"Fallback extraction successful for {filename}: {len(extracted_text)} characters")
            
            # Process the fallback result through the same pipeline as Document Intelligence results
            # This ensures consistent structure with text_segments and images
            processed_result = self._process_extraction_result(result, filename)
            return processed_result
            
        except Exception as e:
            logging.error(f"Fallback text extraction failed for {filename}: {e}")
            return None
    
    def _extract_text_from_html(self, html_content):
        """Extract text content from HTML, removing tags."""
        try:
            # Try using BeautifulSoup if available
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text
                
            except ImportError:
                # Fallback: simple regex-based tag removal
                import re
                # Remove script and style content
                html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', html_content)
                
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                
                return text
                
        except Exception as e:
            logging.warning(f"HTML text extraction failed, using raw content: {e}")
            return html_content
    
    def _extract_text_from_xml(self, xml_content):
        """Extract text content from XML, removing tags."""
        try:
            import re
            # Simple regex-based tag removal for XML
            text = re.sub(r'<[^>]+>', ' ', xml_content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception as e:
            logging.warning(f"XML text extraction failed, using raw content: {e}")
            return xml_content
    
    def _clean_extracted_text(self, text):
        """Clean up extracted text content."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove common unwanted characters/sequences
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
        
        return text

    def _extract_text_from_pdf_fallback(self, document_bytes):
        """
        Fallback PDF text extraction using PyMuPDF when Document Intelligence fails.
        
        Args:
            document_bytes: Binary content of the PDF document
            
        Returns:
            str: Extracted text content or empty string if extraction fails
        """
        try:
            # First, check if the PDF bytes are large enough to be valid
            if len(document_bytes) < 100:
                logging.warning(f"PDF too small ({len(document_bytes)} bytes) for meaningful extraction")
                return ""
            
            # Try using PyMuPDF (fitz) for PDF text extraction
            import fitz  # PyMuPDF
            
            try:
                # Try to open PDF directly from bytes first (more reliable)
                pdf_doc = fitz.open(stream=document_bytes, filetype="pdf")
                extracted_text = ""
                
                # Extract text from each page
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc[page_num]
                    page_text = page.get_text()
                    if page_text.strip():
                        extracted_text += f"Page {page_num + 1}:\n{page_text}\n\n"
                
                pdf_doc.close()
                
                if extracted_text.strip():
                    logging.info(f"PyMuPDF successfully extracted {len(extracted_text)} characters from PDF")
                    return extracted_text.strip()
                else:
                    logging.warning("PyMuPDF found valid PDF structure but no text content")
                    return ""
                    
            except Exception as pdf_error:
                # If direct bytes opening fails, try with temporary file
                logging.info(f"Direct PDF opening failed ({pdf_error}), trying temporary file method...")
                
                import tempfile
                import os
                
                # Create a temporary file to work with PyMuPDF
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(document_bytes)
                    tmp_path = tmp_file.name
                
                try:
                    # Open PDF with PyMuPDF from file
                    pdf_doc = fitz.open(tmp_path)
                    extracted_text = ""
                    
                    # Extract text from each page
                    for page_num in range(len(pdf_doc)):
                        page = pdf_doc[page_num]
                        page_text = page.get_text()
                        if page_text.strip():
                            extracted_text += f"Page {page_num + 1}:\n{page_text}\n\n"
                    
                    pdf_doc.close()
                    
                    if extracted_text.strip():
                        logging.info(f"PyMuPDF (temp file method) successfully extracted {len(extracted_text)} characters")
                        return extracted_text.strip()
                    else:
                        logging.warning("PyMuPDF (temp file method) found valid PDF but no text content")
                        return ""
                        
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                    
        except ImportError:
            logging.warning("PyMuPDF not available for PDF fallback extraction")
            return ""
        except Exception as e:
            logging.warning(f"PDF fallback extraction completely failed: {e}")
            return ""

    def _try_document_intelligence_with_retries(self, document_bytes, filename, detected_format, initial_content_type):
        """
        Try Document Intelligence with multiple strategies to match Azure portal UI behavior.
        
        Args:
            document_bytes: Binary content of the document
            filename: Original filename
            detected_format: Format detected by our analysis
            initial_content_type: Content type determined by our detection
            
        Returns:
            Document Intelligence result or None if all attempts fail
        """
        strategies = []
        
        # Strategy 1: Use our detected content-type with raw binary upload
        strategies.append({
            'name': 'Detected content-type (raw binary)',
            'content_type': initial_content_type,
            'use_multipart': False
        })
        
        # Strategy 2: If detected format differs from file extension, try with detected format
        # This handles cases where a .pdf file is actually HTML/text content
        original_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if (original_ext == 'pdf' and detected_format != 'pdf' and 
            FileFormatDetector.is_format_supported_by_document_intelligence(detected_format)):
            detected_content_type = FileFormatDetector.get_content_type(detected_format)
            strategies.append({
                'name': f'Detected format override ({detected_format})',
                'content_type': detected_content_type,
                'use_multipart': False
            })
        
        # Strategy 3: Force application/pdf for .pdf files (user's suggestion)
        # Only try this if the file extension is PDF but we detected something else
        if original_ext == 'pdf' and initial_content_type != 'application/pdf':
            strategies.append({
                'name': 'Force PDF content-type (raw binary)',
                'content_type': 'application/pdf',
                'use_multipart': False
            })
        
        # Strategy 4: Use multipart form-data upload (like portal UI)
        strategies.append({
            'name': 'Detected content-type (multipart)',
            'content_type': initial_content_type,
            'use_multipart': True
        })
        
        # Strategy 5: Force PDF with multipart (combining both approaches)
        if original_ext == 'pdf' and initial_content_type != 'application/pdf':
            strategies.append({
                'name': 'Force PDF content-type (multipart)',
                'content_type': 'application/pdf',
                'use_multipart': True
            })
        
        # Strategy 6: For .pdf files that we detected as HTML/text, try with correct content-type and multipart
        if (original_ext == 'pdf' and detected_format != 'pdf' and 
            FileFormatDetector.is_format_supported_by_document_intelligence(detected_format)):
            detected_content_type = FileFormatDetector.get_content_type(detected_format)
            strategies.append({
                'name': f'Detected format override with multipart ({detected_format})',
                'content_type': detected_content_type,
                'use_multipart': True
            })
        
        # Strategy 6: Last resort - application/octet-stream (let Document Intelligence auto-detect)
        if initial_content_type != 'application/octet-stream':
            strategies.append({
                'name': 'Auto-detect (octet-stream)',
                'content_type': 'application/octet-stream',
                'use_multipart': False
            })
        
        # Try each strategy
        for i, strategy in enumerate(strategies, 1):
            logging.info(f"[{filename}] Trying strategy {i}/{len(strategies)}: {strategy['name']}")
            logging.info(f"[{filename}] Content-Type: {strategy['content_type']}, Multipart: {strategy['use_multipart']}")
            
            try:
                result, errors = self.doc_client.analyze_document_from_bytes(
                    file_bytes=document_bytes,
                    filename=filename,
                    model='prebuilt-layout',
                    content_type=strategy['content_type'],
                    use_multipart=strategy['use_multipart']
                )
                
                if result and not errors:
                    logging.info(f"[{filename}] ✅ Success with strategy {i}: {strategy['name']}")
                    return result
                elif errors:
                    error_summary = '; '.join(errors)
                    logging.warning(f"[{filename}] ❌ Strategy {i} failed: {error_summary}")
                    # Continue to next strategy
                else:
                    logging.warning(f"[{filename}] ❌ Strategy {i} returned no result")
                    # Continue to next strategy
                    
            except Exception as e:
                logging.warning(f"[{filename}] ❌ Strategy {i} exception: {str(e)}")
                # Continue to next strategy
        
        logging.error(f"[{filename}] All {len(strategies)} Document Intelligence strategies failed")
        return None
