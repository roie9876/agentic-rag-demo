#!/usr/bin/env python3
"""
Test the specific Streamlit upload code path that can trigger the DocumentChunker error
"""

import sys
import traceback
import logging
import os
import base64
from pathlib import Path

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_streamlit_upload_path():
    """Test the specific code path used in Streamlit file uploads that might trigger the error"""
    
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import required modules
        from chunking import DocumentChunker
        import sys
        import importlib.util
        
        # Import functions from agentic-rag-demo.py
        spec = importlib.util.spec_from_file_location("agentic_rag_demo", "/Users/robenhai/agentic-rag-demo/agentic-rag-demo.py")
        agentic_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agentic_module)
        
        _chunk_to_docs = agentic_module._chunk_to_docs
        init_openai = agentic_module.init_openai
        
        # Use the actual test.pdf file in the project
        pdf_path = Path("/Users/robenhai/agentic-rag-demo/test.pdf")
        
        if not pdf_path.exists():
            print(f"❌ PDF file not found: {pdf_path}")
            return False
            
        # Read the actual PDF content
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
            
        print(f"Testing Streamlit upload path with {len(pdf_content):,} byte PDF")
        
        # Hebrew filename that causes the issue
        hebrew_filename = "שומה בן חיים.pdf"
        
        # Create OpenAI client for embedding
        try:
            oai_client, _ = init_openai("o3")
            embed_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
            print(f"✓ OpenAI client initialized, embedding deployment: {embed_deploy}")
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI client: {e}")
            return False
        
        # Step 1: Try _chunk_to_docs (this should return empty list due to auth issues)
        print("\n--- Step 1: Testing _chunk_to_docs ---")
        try:
            docs = _chunk_to_docs(
                hebrew_filename,
                pdf_content,  # raw bytes
                "",  # no URL
                oai_client,
                embed_deploy
            )
            print(f"_chunk_to_docs returned {len(docs)} documents")
        except Exception as e:
            print(f"_chunk_to_docs failed: {e}")
            docs = []
        
        # Step 2: If no docs, try the fallback path (this is where the error likely occurs)
        if not docs:
            print("\n--- Step 2: Testing fallback DocumentChunker path ---")
            print("No documents from _chunk_to_docs, trying fallback path...")
            
            # This is the exact code path from the Streamlit upload that might cause the error
            multimodal_enabled = os.getenv("MULTIMODAL", "false").lower() in ["true", "1", "yes"]
            print(f"Multimodal enabled: {multimodal_enabled}")
            
            dc = DocumentChunker(multimodal=multimodal_enabled, openai_client=oai_client if multimodal_enabled else None)
            data = {
                "fileName": hebrew_filename,
                "documentBytes": base64.b64encode(pdf_content).decode("utf-8"),
                "documentUrl": "",
            }
            
            print(f"Calling dc.chunk_documents with Hebrew filename: {hebrew_filename}")
            print(f"Data structure: fileName={data['fileName']}, documentBytes length={len(data['documentBytes'])}")
            
            # This is where the error should occur if it's going to happen
            chunks, errors, warnings = dc.chunk_documents(data)
            
            print(f"DocumentChunker results:")
            print(f"- Chunks: {len(chunks)}")
            print(f"- Errors: {len(errors)}")
            print(f"- Warnings: {len(warnings)}")
            
            if errors:
                print("Errors encountered:")
                for error in errors:
                    print(f"  - {error}")
                    
                # Check if this is the specific error we're looking for
                for error in errors:
                    if "sequence item 0: expected str instance, dict found" in str(error):
                        print("\n🎯 FOUND THE ERROR WE'RE LOOKING FOR!")
                        return False
                        
            if chunks:
                print("Sample chunk:")
                chunk = chunks[0]
                print(f"  Keys: {list(chunk.keys())}")
                if 'page_chunk' in chunk:
                    content = chunk['page_chunk']
                    print(f"  Content preview: {str(content)[:100]}...")
                    
        return True
        
    except Exception as e:
        print(f"Exception caught: {e}")
        print("Full traceback:")
        traceback.print_exc()
        
        # Check if this is the specific error we're looking for
        if "sequence item 0: expected str instance, dict found" in str(e):
            print("\n🎯 FOUND THE ERROR WE'RE LOOKING FOR!")
            print("This is the exact error reported by the user.")
            
            # Try to extract the exact line where the error occurs
            tb = traceback.format_exc()
            lines = tb.split('\n')
            for i, line in enumerate(lines):
                if 'join' in line.lower() and ('sequence item' in tb or 'expected str instance' in tb):
                    print(f"Error likely at: {line.strip()}")
                    if i > 0:
                        print(f"Previous context: {lines[i-1].strip()}")
                    if i < len(lines) - 1:
                        print(f"Next context: {lines[i+1].strip()}")
        
        return False

if __name__ == "__main__":
    print("Testing Streamlit upload code path with Hebrew PDF")
    print("=" * 70)
    
    success = test_streamlit_upload_path()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Test completed successfully - no DocumentChunker error found")
    else:
        print("❌ Test failed or error reproduced")
    
    sys.exit(0 if success else 1)
