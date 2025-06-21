#!/usr/bin/env python3
"""
Debug script to test Document Intelligence with the Hebrew PDF
that works in the studio but fails in our code.
"""

import os
import sys
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
    print("✅ Environment loaded with dotenv")
except ImportError:
    print("⚠️ dotenv not available, using system environment")

# Test environment loading
endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT")
key = os.getenv("DOCUMENT_INTEL_KEY") 

print(f"Endpoint from env: {endpoint}")
print(f"Key configured: {'Yes' if key else 'No'}")

# If env vars not loaded, try manual loading
if not endpoint:
    print("❌ Environment variables not loaded, trying manual approach...")
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('DOCUMENT_INTEL_ENDPOINT='):
                    endpoint = line.split('=', 1)[1].strip()
                    os.environ['DOCUMENT_INTEL_ENDPOINT'] = endpoint
                elif line.startswith('DOCUMENT_INTEL_KEY='):
                    key = line.split('=', 1)[1].strip()
                    os.environ['DOCUMENT_INTEL_KEY'] = key
        print(f"Manual load - Endpoint: {endpoint}")
        print(f"Manual load - Key configured: {'Yes' if key else 'No'}")

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent))

from tools.doc_intelligence import DocumentIntelligenceClient

def test_pdf_with_docint(pdf_path: str):
    """Test the problematic PDF with Document Intelligence directly"""
    
    print(f"\n🔍 Testing PDF: {pdf_path}")
    print(f"📁 File exists: {os.path.exists(pdf_path)}")
    
    if not os.path.exists(pdf_path):
        print("❌ ERROR: PDF file not found!")
        return
        
    # Read the PDF file
    with open(pdf_path, 'rb') as f:
        file_bytes = f.read()
        
    print(f"📊 File size: {len(file_bytes):,} bytes")
    
    # Test Document Intelligence configuration  
    endpoint = os.getenv("DOCUMENT_INTEL_ENDPOINT")
    key = os.getenv("DOCUMENT_INTEL_KEY")
    
    print(f"🌐 Endpoint: {endpoint}")
    print(f"🔑 Key configured: {'Yes' if key else 'No'}")
    
    # Initialize Document Intelligence client
    try:
        print(f"\n🚀 Initializing Document Intelligence client...")
        client = DocumentIntelligenceClient()
        print(f"✅ Client initialized successfully")
        print(f"📋 API Version: {client.api_version}")
        print(f"🎯 Supported extensions: {client.file_extensions}")
        
        # Test the document analysis
        filename = os.path.basename(pdf_path)
        print(f"\n📖 Analyzing document: {filename}")
        print(f"🔄 Starting analysis with model: prebuilt-layout")
        
        result, errors = client.analyze_document_from_bytes(
            file_bytes=file_bytes,
            filename=filename,
            model='prebuilt-layout'
        )
        
        if errors:
            print(f"\n❌ ERRORS FOUND ({len(errors)}):")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
        else:
            print(f"\n✅ SUCCESS! No errors reported")
            
        if result:
            print(f"\n📊 RESULTS:")
            print(f"  📝 Result keys: {list(result.keys())}")
            if 'content' in result:
                content_preview = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
                print(f"  📄 Content preview: {repr(content_preview)}")
            if 'pages' in result:
                print(f"  📃 Number of pages: {len(result['pages'])}")
            if 'result_id' in result:
                print(f"  🆔 Result ID: {result['result_id']}")
            if 'model_id' in result:
                print(f"  🤖 Model ID: {result['model_id']}")
        else:
            print(f"\n⚠️ No result returned (but no errors either)")
                
    except Exception as e:
        print(f"\n💥 Exception during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test with the Hebrew PDF
    pdf_path = "/Users/robenhai/Downloads/תעשייה אווירית – ויקיפדיה.pdf"
    test_pdf_with_docint(pdf_path)
