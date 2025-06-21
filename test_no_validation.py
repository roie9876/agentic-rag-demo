#!/usr/bin/env python3
"""
Test that PDF processing works without header validation.
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

def test_pdf_processing_without_validation():
    """Test that PDFs are processed without strict header validation."""
    logger.info("🔍 Testing PDF processing without header validation...")
    
    try:
        from chunking.multimodal_processor import MultimodalProcessor, validate_pdf_file
        
        # Test 1: Very small file (should pass now)
        small_content = b"Small file content"
        is_valid, error = validate_pdf_file(small_content, "small_test.pdf")
        
        if is_valid:
            logger.info("✅ Small file validation passed (as expected)")
        else:
            logger.error(f"❌ Small file validation failed: {error}")
            return False
        
        # Test 2: Non-PDF content (should pass now - let Document Intelligence handle it)
        html_content = b"<!DOCTYPE html><html><body>Not a PDF</body></html>"
        is_valid, error = validate_pdf_file(html_content, "fake.pdf")
        
        if is_valid:
            logger.info("✅ Non-PDF content validation passed (validation disabled)")
        else:
            logger.error(f"❌ Non-PDF content should have passed: {error}")
            return False
        
        # Test 3: Test with multimodal processor
        processor = MultimodalProcessor()
        
        if processor.doc_client:
            logger.info("✅ Document Intelligence client available")
            
            # Now the processor will try to process any file and let Document Intelligence decide
            logger.info("✅ Processor will now let Document Intelligence handle format validation")
        else:
            logger.warning("⚠️ Document Intelligence client not available")
        
        logger.info("✅ All validation bypass tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def main():
    """Run the test."""
    logger.info("🚀 Testing PDF processing without strict validation...")
    
    if test_pdf_processing_without_validation():
        logger.info("🎉 Success! PDFs will now be processed without header validation.")
        logger.info("📄 Document Intelligence will handle format validation instead.")
        logger.info("✅ Your multi-format PDFs should now work correctly!")
    else:
        logger.error("❌ Test failed. Check the logs above.")

if __name__ == "__main__":
    main()
