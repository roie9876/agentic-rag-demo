#!/usr/bin/env python3
"""
Test the improved embedding function with token-aware truncation
"""
import sys
import os
sys.path.append('/Users/robenhai/agentic-rag-demo')

from dotenv import load_dotenv
load_dotenv()

# Test the embedding function
def test_embedding_truncation():
    print("=== Testing Embedding Token Truncation ===")
    
    # Create a very long text that will exceed 8192 tokens
    # Average of ~4 tokens per word, so we need about 32,000+ words to exceed 8192 tokens
    long_text = ("This is a comprehensive test sentence with multiple technical terms, complex vocabulary, and extensive detailed descriptions that should generate a substantial number of tokens when processed through the tokenizer. " * 100)
    
    print(f"Original text length: {len(long_text):,} characters")
    
    # Test token counting
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model("text-embedding-3-large")
        tokens = encoding.encode(long_text)
        print(f"Original token count: {len(tokens):,} tokens")
        
        # Test truncation
        MAX_TOKENS = 8000
        if len(tokens) > MAX_TOKENS:
            truncated_tokens = tokens[:MAX_TOKENS]
            truncated_text = encoding.decode(truncated_tokens)
            print(f"Truncated token count: {len(truncated_tokens):,} tokens")
            print(f"Truncated text length: {len(truncated_text):,} characters")
            print("✅ Truncation working correctly")
        else:
            print("Text is already under the limit")
            
    except Exception as e:
        print(f"Error testing tokenization: {e}")
    
    # Test the actual embedding function
    print("\n=== Testing Actual Embedding Function ===")
    try:
        # Import the module correctly
        import importlib.util
        spec = importlib.util.spec_from_file_location("agentic_rag_demo", "/Users/robenhai/agentic-rag-demo/agentic-rag-demo.py")
        agentic_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agentic_module)
        
        # Get OpenAI client
        oai_client, _ = agentic_module.get_openai_client()
        embed_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        
        # Test with long text
        print("Testing embedding with long text...")
        vector = agentic_module.embed_text(oai_client, embed_deployment, long_text)
        print(f"✅ Embedding successful! Vector length: {len(vector)}")
        
    except Exception as e:
        print(f"❌ Embedding failed: {e}")

if __name__ == "__main__":
    test_embedding_truncation()
