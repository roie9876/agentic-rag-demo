#!/usr/bin/env python3
"""
Debug script to trace file size throughout the processing pipeline.
This will help identify where the 1.27MB PDF gets truncated to 644 bytes.
"""

import os
import sys
import base64
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

def test_file_size_pipeline(test_file_path: str):
    """Test the complete file processing pipeline to identify where truncation occurs."""
    
    if not os.path.exists(test_file_path):
        logger.error(f"Test file not found: {test_file_path}")
        return False
    
    filename = os.path.basename(test_file_path)
    
    # Step 1: Read original file
    logger.info("=" * 60)
    logger.info("STEP 1: Original file reading")
    logger.info("=" * 60)
    
    with open(test_file_path, 'rb') as f:
        original_bytes = f.read()
    
    original_size = len(original_bytes)
    logger.info(f"📁 Original file size: {original_size:,} bytes")
    logger.info(f"📄 Filename: {filename}")
    logger.info(f"🔤 First 50 bytes: {repr(original_bytes[:50])}")
    logger.info(f"🔤 Last 50 bytes: {repr(original_bytes[-50:])}")
    
    if filename.endswith('.pdf'):
        if original_bytes.startswith(b'%PDF-'):
            logger.info("✅ Valid PDF header detected")
        else:
            logger.error("❌ Invalid PDF header!")
    
    # Step 2: Base64 encoding (like Streamlit would do)
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Base64 encoding")
    logger.info("=" * 60)
    
    base64_encoded = base64.b64encode(original_bytes).decode('utf-8')
    logger.info(f"📊 Base64 string length: {len(base64_encoded):,} characters")
    logger.info(f"🔤 First 100 chars: {repr(base64_encoded[:100])}")
    
    # Step 3: Base64 decoding (like chunker would do)
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Base64 decoding")
    logger.info("=" * 60)
    
    try:
        decoded_bytes = base64.b64decode(base64_encoded)
        decoded_size = len(decoded_bytes)
        logger.info(f"📊 Decoded size: {decoded_size:,} bytes")
        
        if decoded_size == original_size:
            logger.info("✅ Size matches original!")
        else:
            logger.error(f"❌ Size mismatch! Original: {original_size:,}, Decoded: {decoded_size:,}")
            
        # Check if content matches
        if decoded_bytes == original_bytes:
            logger.info("✅ Content matches original!")
        else:
            logger.error("❌ Content doesn't match original!")
            
    except Exception as e:
        logger.error(f"❌ Base64 decode failed: {e}")
        return False
    
    # Step 4: Test with DocumentChunker pipeline
    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: DocumentChunker pipeline test")
    logger.info("=" * 60)
    
    try:
        from chunking.document_chunking import DocumentChunker
        from chunking.chunker_factory import get_filename_from_data
        
        # Test data structure like the real app uses
        test_data = {
            "fileName": filename,
            "documentBytes": base64_encoded,  # String format
            "documentUrl": "",
        }
        
        logger.info(f"📦 Test data keys: {list(test_data.keys())}")
        logger.info(f"📊 DocumentBytes type: {type(test_data['documentBytes'])}")
        logger.info(f"📊 DocumentBytes length: {len(test_data['documentBytes']):,}")
        
        # Initialize chunker
        dc = DocumentChunker(multimodal=True, openai_client=None)
        
        # Process the document
        logger.info("🔄 Processing with DocumentChunker...")
        chunks, errors, warnings = dc.chunk_documents(test_data)
        
        logger.info(f"📊 Results: {len(chunks)} chunks, {len(errors)} errors, {len(warnings)} warnings")
        
        if errors:
            logger.error("❌ Errors found:")
            for i, error in enumerate(errors, 1):
                logger.error(f"  {i}. {error}")
        
        if warnings:
            logger.warning("⚠️ Warnings found:")
            for i, warning in enumerate(warnings, 1):
                logger.warning(f"  {i}. {warning}")
                
        return len(errors) == 0
        
    except Exception as e:
        logger.error(f"❌ DocumentChunker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    # You can test with any PDF file
    test_files = [
        # Add paths to test files here
        "test_file.pdf",  # Replace with actual file path
        "/Users/robenhai/Downloads/שומה בן חיים.pdf",  # If you have the actual problematic file
    ]
    
    logger.info("🔍 File Size Pipeline Debug Test")
    logger.info("This will help identify where the 1.27MB → 644 bytes truncation occurs")
    
    success = False
    for test_file in test_files:
        if os.path.exists(test_file):
            logger.info(f"\n🎯 Testing with: {test_file}")
            success = test_file_size_pipeline(test_file)
            break
    
    if not success and not any(os.path.exists(f) for f in test_files):
        logger.warning("⚠️ No test files found. Please:")
        logger.warning("1. Put a PDF file in the current directory named 'test_file.pdf'")
        logger.warning("2. Or update the test_files list with the actual path to your problematic PDF")
        logger.warning("3. Then run this script again")

if __name__ == "__main__":
    main()
