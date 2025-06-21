#!/usr/bin/env python3
"""
Test script for handling small/corrupted PDF files like 'שומה בן חיים.pdf'
"""

import os
import sys
import logging

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chunking.multimodal_processor import MultimodalProcessor, validate_and_detect_format

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_small_fake_pdf():
    """Create a small fake PDF file similar to the problematic one (644 bytes)"""
    # Create some minimal content that might appear in a corrupted PDF
    fake_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000125 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n223\n%%EOF"
    
    # Truncate to 644 bytes to match the problematic file size
    return fake_pdf_content[:644]

def test_small_pdf_processing():
    """Test processing of a small/corrupted PDF file"""
    print("Testing small PDF file processing...")
    
    # Create a fake small PDF
    fake_pdf_bytes = create_small_fake_pdf()
    filename = "שומה בן חיים.pdf"
    
    print(f"Created fake PDF: {len(fake_pdf_bytes)} bytes")
    print(f"First 100 bytes: {fake_pdf_bytes[:100]}")
    
    # Test format validation
    print("\n=== Format Validation ===")
    is_valid, detected_format, content_type, message = validate_and_detect_format(fake_pdf_bytes, filename)
    print(f"Valid: {is_valid}")
    print(f"Detected format: {detected_format}")
    print(f"Content type: {content_type}")
    print(f"Message: {message}")
    
    # Test multimodal processing
    print("\n=== Multimodal Processing ===")
    processor = MultimodalProcessor()
    
    try:
        result = processor.process_document(fake_pdf_bytes, filename)
        if result:
            print("Processing successful!")
            print(f"Result type: {result.get('extraction_method', 'unknown')}")
            print(f"Content length: {len(result.get('content', ''))}")
            if 'pages' in result:
                print(f"Number of pages: {len(result['pages'])}")
        else:
            print("Processing returned None")
    except Exception as e:
        print(f"Processing failed: {e}")
        print(f"Error type: {type(e).__name__}")

def test_fallback_extraction():
    """Test direct fallback extraction"""
    print("\n=== Testing Fallback Extraction ===")
    
    # Create a fake small PDF
    fake_pdf_bytes = create_small_fake_pdf()
    filename = "שומה בן חיים.pdf"
    
    processor = MultimodalProcessor()
    
    try:
        result = processor._fallback_text_extraction(fake_pdf_bytes, filename, 'pdf')
        if result:
            print("Fallback extraction successful!")
            print(f"Content length: {len(result.get('content', ''))}")
            print(f"Extraction method: {result.get('extraction_method')}")
            print(f"Content preview: {result.get('content', '')[:200]}...")
        else:
            print("Fallback extraction returned None")
    except Exception as e:
        print(f"Fallback extraction failed: {e}")

def test_empty_file():
    """Test handling of truly empty files"""
    print("\n=== Testing Empty File ===")
    
    empty_bytes = b""
    filename = "empty.pdf"
    
    print(f"Empty file: {len(empty_bytes)} bytes")
    
    # Test format validation
    is_valid, detected_format, content_type, message = validate_and_detect_format(empty_bytes, filename)
    print(f"Valid: {is_valid}")
    print(f"Message: {message}")

if __name__ == "__main__":
    print("Testing small/corrupted PDF handling...")
    
    test_small_pdf_processing()
    test_fallback_extraction()
    test_empty_file()
    
    print("\nTest completed!")

def create_small_valid_pdf():
    """Create a small but valid PDF similar to your 599-byte file."""
    # This creates a minimal valid PDF that's similar in size to your file
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Resources <<
/Font <<
/F1 4 0 R
>>
>>
/Contents 5 0 R
>>
endobj

4 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

5 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000274 00000 n 
0000000361 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
456
%%EOF"""
    return pdf_content

def test_small_pdf_validation():
    """Test that small PDFs like yours now pass validation."""
    logger.info("🔍 Testing small PDF validation...")
    
    try:
        from chunking.multimodal_processor import validate_pdf_file
        
        # Test with a small PDF similar to yours
        small_pdf = create_small_valid_pdf()
        logger.info(f"Created test PDF: {len(small_pdf)} bytes")
        
        # Test the validation
        is_valid, error_message = validate_pdf_file(small_pdf, "test_small.pdf")
        
        if is_valid:
            logger.info("✅ Small PDF validation passed!")
            return True
        else:
            logger.error(f"❌ Small PDF validation failed: {error_message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_document_processing():
    """Test the complete document processing pipeline."""
    logger.info("🔍 Testing document processing with small PDF...")
    
    try:
        from chunking.document_chunking import DocumentChunker
        
        # Create small PDF
        small_pdf = create_small_valid_pdf()
        
        # Test processing without OpenAI client first
        dc = DocumentChunker(multimodal=True, openai_client=None)
        
        data = {
            "fileName": "תעשייה אווירית – ויקיפדיה.pdf",  # Use your exact filename
            "documentBytes": base64.b64encode(small_pdf).decode("utf-8"),
            "documentUrl": "",
        }
        
        logger.info("Processing small PDF...")
        chunks, errors, warnings = dc.chunk_documents(data)
        
        logger.info(f"Results:")
        logger.info(f"  Chunks: {len(chunks)}")
        logger.info(f"  Errors: {len(errors)}")
        logger.info(f"  Warnings: {len(warnings)}")
        
        if errors:
            for error in errors:
                logger.error(f"  Error: {error}")
            return False
        
        if chunks:
            logger.info("✅ Document processing succeeded!")
            for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
                content = chunk.get('content', '')[:100]
                logger.info(f"  Chunk {i}: {content}...")
            return True
        else:
            logger.error("❌ No chunks produced")
            return False
            
    except Exception as e:
        logger.error(f"❌ Document processing failed: {e}")
        return False

def main():
    """Run the small PDF tests."""
    logger.info("🚀 Testing small PDF handling (like your 599-byte file)...")
    
    # Test 1: PDF validation
    test1_result = test_small_pdf_validation()
    
    # Test 2: Document processing
    test2_result = test_document_processing()
    
    logger.info("\n" + "="*50)
    logger.info("TEST RESULTS")
    logger.info("="*50)
    logger.info(f"Small PDF validation: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    logger.info(f"Document processing: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        logger.info("🎉 Small PDF handling is now working!")
        logger.info("Your 599-byte PDF should now process successfully.")
    else:
        logger.error("❌ Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main()
