#!/usr/bin/env python3
"""
Debug script to trace the exact location of the DocumentChunker error
"""

import sys
import traceback
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_hebrew_pdf_processing():
    """Test processing a file with Hebrew filename to reproduce the error"""
    
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        from chunking import DocumentChunker
        
        # Create a simple test document with Hebrew filename
        test_data = {
            "fileName": "שומה בן חיים.pdf",
            "documentBytes": "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCgoyIDAgb2JqCjw8Ci9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagoKMyAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDIgMCBSCi9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCj4+CmVuZG9iagoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDQKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjE5NAolJUVPRg==",
            "documentUrl": "http://example.com/שומה בן חיים.pdf"
        }
        
        print(f"Testing DocumentChunker with Hebrew filename: {test_data['fileName']}")
        
        # Create DocumentChunker
        chunker = DocumentChunker(multimodal=True)
        
        # Process the document - this should trigger the error
        chunks, errors, warnings = chunker.chunk_documents(test_data)
        
        print(f"Processing completed:")
        print(f"- Chunks: {len(chunks)}")
        print(f"- Errors: {len(errors)}")
        print(f"- Warnings: {len(warnings)}")
        
        if errors:
            print("Errors encountered:")
            for error in errors:
                print(f"  - {error}")
                
        return len(errors) == 0
        
    except Exception as e:
        print(f"Exception caught: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hebrew_pdf_processing()
    sys.exit(0 if success else 1)
