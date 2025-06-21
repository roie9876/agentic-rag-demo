#!/usr/bin/env python3
"""
Test script to reproduce the DocumentChunker error with the actual Hebrew PDF file
"""

import sys
import traceback
import logging
import os
from pathlib import Path

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_actual_hebrew_pdf():
    """Test processing the actual test.pdf file that causes the error"""
    
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        from chunking import DocumentChunker
        import base64
        
        # Use the actual test.pdf file in the project
        pdf_path = Path("/Users/robenhai/agentic-rag-demo/test.pdf")
        
        if not pdf_path.exists():
            print(f"❌ PDF file not found: {pdf_path}")
            return False
            
        print(f"Found PDF file: {pdf_path}")
        print(f"File size: {pdf_path.stat().st_size:,} bytes")
        
        # Read the actual PDF content
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
            
        print(f"Read {len(pdf_content):,} bytes from PDF")
        print(f"First 50 bytes: {pdf_content[:50]}")
        print(f"Last 50 bytes: {pdf_content[-50:]}")
        
        # Test with Hebrew filename to reproduce the issue
        hebrew_filename = "שומה בן חיים.pdf"
        
        # Create test data structure with the actual PDF content
        test_data = {
            "fileName": hebrew_filename,
            "documentBytes": base64.b64encode(pdf_content).decode("utf-8"),
            "documentUrl": f"http://example.com/{hebrew_filename}"
        }
        
        print(f"Testing DocumentChunker with Hebrew filename: {hebrew_filename}")
        print(f"Base64 encoded size: {len(test_data['documentBytes']):,} characters")
        
        # Create DocumentChunker with multimodal processing
        chunker = DocumentChunker(multimodal=True)
        
        # Process the document - this should trigger the error if it exists
        print("Starting document processing...")
        chunks, errors, warnings = chunker.chunk_documents(test_data)
        
        print(f"Processing completed:")
        print(f"- Chunks: {len(chunks)}")
        print(f"- Errors: {len(errors)}")
        print(f"- Warnings: {len(warnings)}")
        
        if errors:
            print("Errors encountered:")
            for error in errors:
                print(f"  - {error}")
                
        if chunks:
            print("Sample chunk keys:")
            for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
                print(f"  Chunk {i+1}: {list(chunk.keys())}")
                if 'page_chunk' in chunk:
                    content = chunk['page_chunk']
                    print(f"    Content preview: {str(content)[:100]}...")
                    
        return len(errors) == 0
        
    except Exception as e:
        print(f"Exception caught: {e}")
        print("Full traceback:")
        traceback.print_exc()
        
        # Check if this is the specific error we're looking for
        if "sequence item 0: expected str instance, dict found" in str(e):
            print("\n🎯 FOUND THE ERROR WE'RE LOOKING FOR!")
            print("This is the exact error reported by the user.")
            
            # Let's try to get more details about where this happens
            import traceback
            tb_lines = traceback.format_exc().split('\n')
            for i, line in enumerate(tb_lines):
                if 'join' in line.lower() or 'sequence item' in line:
                    print(f"Error context: {line}")
                    if i > 0:
                        print(f"Previous line: {tb_lines[i-1]}")
                    if i < len(tb_lines) - 1:
                        print(f"Next line: {tb_lines[i+1]}")
        
        return False

if __name__ == "__main__":
    print("Testing with actual Hebrew PDF file")
    print("=" * 60)
    
    success = test_actual_hebrew_pdf()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test completed successfully - no DocumentChunker error found")
    else:
        print("❌ Test failed or error reproduced")
    
    sys.exit(0 if success else 1)
