#!/usr/bin/env python3

"""
Test script to reproduce and fix the 0 chunks issue with fallback extraction.
"""

import sys
import base64
import logging
from chunking.multimodal_processor import MultimodalProcessor
from chunking.chunker_factory import ChunkerFactory

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_fallback_chunking():
    """Test that fallback extraction produces chunks"""
    
    # Read the test PDF
    with open('/Users/robenhai/agentic-rag-demo/test.pdf', 'rb') as f:
        pdf_bytes = f.read()
    
    print(f"PDF file size: {len(pdf_bytes):,} bytes")
    
    # Test multimodal processor directly
    processor = MultimodalProcessor()
    result = processor._fallback_text_extraction(pdf_bytes, "test.pdf", "pdf")
    
    print(f"\nFallback extraction result keys: {list(result.keys()) if result else 'None'}")
    
    if result:
        print(f"Content length: {len(result.get('content', ''))}")
        print(f"Pages: {len(result.get('pages', []))}")
        print(f"Figures: {len(result.get('figures', []))}")
        print(f"First 200 chars: {repr(result.get('content', '')[:200])}")
    
    # Test chunker factory with the same file
    data = {
        "documentUrl": "test.pdf",
        "documentBytes": base64.b64encode(pdf_bytes).decode('utf-8')
    }
    
    factory = ChunkerFactory()
    chunker = factory.get_chunker(data, multimodal=True)
    chunks = chunker.get_chunks()
    
    print(f"\nChunker produced {len(chunks)} chunks")
    
    if chunks:
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i}: {len(chunk.get('content', ''))} chars")
            print(f"  Images: {len(chunk.get('relatedImages', []))}")
            print(f"  Page: {chunk.get('page_number', 'unknown')}")
    else:
        print("No chunks produced!")

if __name__ == "__main__":
    test_fallback_chunking()
