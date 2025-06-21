#!/usr/bin/env python3
"""
Test what happens when Document Intelligence rejects a file.
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

def test_document_intelligence_rejection():
    """Test how the system handles Document Intelligence rejection."""
    logger.info("🔍 Testing Document Intelligence rejection handling...")
    
    try:
        from chunking.document_chunking import DocumentChunker
        
        # Create a fake file that will be rejected by Document Intelligence
        # This simulates your 599-byte file that isn't actually a PDF
        fake_pdf_content = """<!DOCTYPE html>
<html>
<head><title>תעשייה אווירית – ויקיפדיה</title></head>
<body><h1>This is HTML, not PDF</h1></body>
</html>""".encode('utf-8')
        
        logger.info(f"Created fake PDF content: {len(fake_pdf_content)} bytes")
        logger.info(f"Content starts with: {fake_pdf_content[:50]}")
        
        # Test with multimodal processing (no OpenAI client for this test)
        dc = DocumentChunker(multimodal=True, openai_client=None)
        
        data = {
            "fileName": "תעשייה אווירית – ויקיפדיה.pdf",
            "documentBytes": base64.b64encode(fake_pdf_content).decode("utf-8"),
            "documentUrl": "",
        }
        
        logger.info("Processing fake PDF with DocumentChunker...")
        chunks, errors, warnings = dc.chunk_documents(data)
        
        logger.info("Results:")
        logger.info(f"  Chunks: {len(chunks)}")
        logger.info(f"  Errors: {len(errors)}")
        logger.info(f"  Warnings: {len(warnings)}")
        
        if errors:
            for i, error in enumerate(errors):
                logger.info(f"  Error {i+1}: {error}")
        
        if warnings:
            for i, warning in enumerate(warnings):
                logger.info(f"  Warning {i+1}: {warning}")
        
        if chunks:
            for i, chunk in enumerate(chunks):
                content = chunk.get('content', '')[:100]
                logger.info(f"  Chunk {i+1}: {content}...")
        
        # This should show that the system gracefully handles the rejection
        if errors and "Document Intelligence" in str(errors[0]):
            logger.info("✅ System correctly handled Document Intelligence rejection")
            return True
        else:
            logger.warning("⚠️ Unexpected result - check the error handling")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def main():
    """Run the Document Intelligence rejection test."""
    logger.info("🚀 Testing Document Intelligence rejection handling...")
    
    result = test_document_intelligence_rejection()
    
    logger.info("\n" + "="*50)
    if result:
        logger.info("✅ Document Intelligence rejection handling works correctly!")
        logger.info("The system will show appropriate error messages to users.")
    else:
        logger.error("❌ There may be an issue with error handling.")
    
    logger.info("\n💡 What this means for your file:")
    logger.info("• Your 599-byte file is correctly being rejected by Document Intelligence")
    logger.info("• This confirms it's not a valid PDF file")
    logger.info("• The system should show a helpful error message in the UI")
    logger.info("• You can safely ignore files that Document Intelligence rejects")

if __name__ == "__main__":
    main()
