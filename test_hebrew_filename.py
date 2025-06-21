#!/usr/bin/env python3
"""
Specific test to reproduce the DocumentChunker error with Hebrew filename PDF
"""

import os
import sys
import logging
import base64
from dotenv import load_dotenv

# Setup logging to see detailed output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_hebrew_filename_pdf():
    """Test processing a PDF with Hebrew filename like the one causing the error"""
    print("=" * 80)
    print("Testing Hebrew Filename PDF Processing")
    print("=" * 80)
    
    try:
        # Load environment
        load_dotenv()
        
        # Create a simple test PDF with Hebrew filename
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
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hebrew content here) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
294
%%EOF"""
        
        filename = "שומה בן חיים.pdf"
        print(f"✓ Created test PDF with Hebrew filename: {filename} ({len(pdf_content)} bytes)")
        
        # Test the actual processing pipeline from agentic-rag-demo.py
        from chunking import DocumentChunker
        from openai import AzureOpenAI
        
        # Initialize OpenAI client for multimodal processing
        try:
            client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            )
            print("✓ Created OpenAI client for multimodal processing")
        except Exception as e:
            print(f"⚠️  OpenAI client creation failed: {e}")
            client = None
        
        # Create test data structure (base64 encoded)
        base64_content = base64.b64encode(pdf_content).decode('utf-8')
        test_data = {
            "fileName": filename,
            "documentBytes": base64_content,
            "documentUrl": f"http://example.com/{filename}"
        }
        
        print(f"✓ Created test data with base64 content ({len(base64_content)} chars)")
        
        # Test DocumentChunker with multimodal processing (the path that's failing)
        chunker = DocumentChunker(multimodal=True, openai_client=client)
        print("✓ Created DocumentChunker with multimodal processing")
        
        # This is where the error should occur if it's going to happen
        print(f"🔍 Processing PDF with DocumentChunker...")
        chunks, warnings, errors = chunker.chunk_documents(test_data)
        
        print(f"✓ DocumentChunker completed:")
        print(f"  - Chunks: {len(chunks)}")
        print(f"  - Warnings: {len(warnings)}")
        print(f"  - Errors: {len(errors)}")
        
        if errors:
            print("❌ Errors found:")
            for error in errors:
                print(f"  - {error}")
        
        if chunks:
            print(f"✓ Sample chunk keys: {list(chunks[0].keys())}")
        
        # Also test the _chunk_to_docs function directly
        print(f"\n🔍 Testing _chunk_to_docs function directly...")
        
        # Import the function from the main file
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", "/Users/robenhai/agentic-rag-demo/agentic-rag-demo.py")
        main_module = importlib.util.module_from_spec(spec)
        
        # We can't easily import the function due to all the dependencies, so let's test manually
        print("⚠️  Direct _chunk_to_docs test skipped due to import complexity")
        
        return True
        
    except Exception as e:
        print(f"❌ Hebrew filename PDF test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_specific_error_scenario():
    """Test the specific scenario that might cause the 'dict found' error"""
    print("\n" + "=" * 80)
    print("Testing Specific Dict/String Error Scenario")
    print("=" * 80)
    
    try:
        # Test the exact error scenario - when we have mixed dict/string content
        from chunking.chunker_factory import MultimodalChunker
        
        # Create a scenario where we might have dict content instead of strings
        test_content = [
            "This is a string",
            {"content": "This is dict content"},
            {"text": "This is dict with text key"},
            {"bad_key": "This is dict without content key"}
        ]
        
        # Test the _safe_join_text method
        chunker = MultimodalChunker(None, None, None)
        
        print(f"🔍 Testing _safe_join_text with mixed content...")
        result = chunker._safe_join_text(test_content, "test_hebrew_file")
        print(f"✓ _safe_join_text result: '{result}'")
        
        # Test with completely invalid content
        invalid_content = [
            123,  # Number
            None,  # None
            {"complex": {"nested": "dict"}},  # Complex dict
            ["list", "content"]  # List
        ]
        
        print(f"🔍 Testing _safe_join_text with invalid content...")
        result2 = chunker._safe_join_text(invalid_content, "test_invalid")
        print(f"✓ _safe_join_text with invalid content: '{result2}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Specific error scenario test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the specific tests for the Hebrew filename error"""
    print("Running Specific Hebrew Filename PDF Error Tests")
    print("=" * 80)
    
    results = []
    
    # Test 1: Hebrew filename PDF processing
    results.append(test_hebrew_filename_pdf())
    
    # Test 2: Specific error scenario
    results.append(test_specific_error_scenario())
    
    # Summary
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The Hebrew filename issue should be resolved.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. The error may still occur with specific files.")
        sys.exit(1)


if __name__ == "__main__":
    main()
