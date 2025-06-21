#!/usr/bin/env python3
"""
Test the improved embedding function that uses AzureOpenAIClient
"""
import os
import sys
sys.path.append('/Users/robenhai/agentic-rag-demo')

from dotenv import load_dotenv
load_dotenv()

# Test the improved embedding function
def test_improved_embedding():
    print("=== Testing Improved Embedding Function ===")
    
    try:
        from tools.aoai import AzureOpenAIClient
        
        # Create a very long text that exceeds 8192 tokens
        long_text = "This is a test sentence. " * 1000  # About 5000 words
        print(f"Created test text with {len(long_text):,} characters")
        
        # Test with AzureOpenAIClient directly
        print("\n--- Testing AzureOpenAIClient directly ---")
        aoai_client = AzureOpenAIClient(document_filename="test")
        
        try:
            embeddings = aoai_client.get_embeddings(long_text)
            print(f"✅ Success! Got embeddings with {len(embeddings)} dimensions")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
    except Exception as e:
        print(f"❌ Failed to test: {e}")

if __name__ == "__main__":
    test_improved_embedding()
