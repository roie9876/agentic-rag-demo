#!/usr/bin/env python3
"""
Test corrupted PDF handling in the multimodal pipeline.
"""

import os
import sys
import base64
import logging
from pathlib import Path

# Add the current directory to the path for imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("dotenv not available, using system environment variables")

def create_corrupted_pdf():
    """Create a small corrupted PDF for testing."""
    # Create a fake PDF header with very little content (similar to your 599-byte file)
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    fake_pdf += b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    fake_pdf += b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n>>\nendobj\nxref\n"
    # This is intentionally incomplete and will be about 200-300 bytes
    return fake_pdf

def test_corrupted_pdf_handling():
    """Test how the system handles corrupted PDFs."""
    logger.info("🔍 Testing corrupted PDF handling...")
    
    try:
        from chunking.document_chunking import DocumentChunker
        
        # Create a corrupted PDF
        corrupted_pdf_bytes = create_corrupted_pdf()
        logger.info(f"Created fake corrupted PDF: {len(corrupted_pdf_bytes)} bytes")
        
        # Test with multimodal processing
        dc = DocumentChunker(multimodal=True, openai_client=None)  # No OpenAI client for this test
        
        data = {
            "fileName": "תעשייה אווירית – ויקיפדיה.pdf",  # Use the same filename as in error
            "documentBytes": base64.b64encode(corrupted_pdf_bytes).decode("utf-8"),
            "documentUrl": "",
        }
        
        logger.info("Processing corrupted PDF...")
        chunks, errors, warnings = dc.chunk_documents(data)
        
        logger.info(f"Results:")
        logger.info(f"  Chunks: {len(chunks)}")
        logger.info(f"  Errors: {len(errors)}")
        logger.info(f"  Warnings: {len(warnings)}")
        
        if chunks:
            for i, chunk in enumerate(chunks):
                logger.info(f"  Chunk {i}: {chunk.get('content', '')[:100]}...")
                if chunk.get('isCorrupted'):
                    logger.info(f"    ✅ Correctly marked as corrupted")
                else:
                    logger.info(f"    ⚠️ Not marked as corrupted")
        
        if errors:
            for error in errors:
                logger.info(f"  Error: {error}")
                
        if warnings:
            for warning in warnings:
                logger.info(f"  Warning: {warning}")
        
        logger.info("✅ Corrupted PDF test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_multimodal_processor_validation():
    """Test the multimodal processor's PDF validation."""
    logger.info("🔍 Testing multimodal processor validation...")
    
    try:
        from chunking.multimodal_processor import MultimodalProcessor
        
        processor = MultimodalProcessor()
        
        # Test with corrupted PDF
        corrupted_pdf_bytes = create_corrupted_pdf()
        
        try:
            result = processor.process_document(corrupted_pdf_bytes, "test_corrupted.pdf")
            if result:
                logger.error("❌ Processor should have rejected corrupted PDF")
                return False
            else:
                logger.info("✅ Processor correctly rejected corrupted PDF")
                return True
        except Exception as e:
            if "Invalid PDF file" in str(e):
                logger.info("✅ Processor correctly threw validation error")
                return True
            else:
                logger.error(f"❌ Unexpected error: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Test setup failed: {e}")
        return False

def main():
    """Run the corrupted PDF tests."""
    logger.info("🚀 Testing corrupted PDF handling...")
    
    # Test 1: Document chunker with corrupted PDF
    test1_result = test_corrupted_pdf_handling()
    
    # Test 2: Multimodal processor validation
    test2_result = test_multimodal_processor_validation()
    
    logger.info("\n" + "="*50)
    logger.info("TEST RESULTS")
    logger.info("="*50)
    logger.info(f"Corrupted PDF chunking: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    logger.info(f"Multimodal validation: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        logger.info("🎉 All corrupted PDF tests passed!")
        logger.info("The system should now handle corrupted files gracefully.")
    else:
        logger.error("❌ Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main()
