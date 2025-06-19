import logging
import os

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

    def get_chunker(self, data):
        """
        Get the appropriate chunker based on the file extension.

        Args:
            extension (str): The file extension.
            data (dict): The data containing document information.

        Returns:
            BaseChunker: An instance of a chunker class.
        """
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
                return MultimodalChunker(data)
            else:
                return DocAnalysisChunker(data)
        elif extension in ('docx', 'pptx'):
            if self.docint_40_api:
                if self.multimodality:
                    return MultimodalChunker(data)
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
