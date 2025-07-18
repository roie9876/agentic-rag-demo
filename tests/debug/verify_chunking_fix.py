#!/usr/bin/env python3
"""
Verify that the token-aware chunking fix is working correctly.
This test checks if large files are now properly split into multiple chunks.
"""
import os
import sys
import tempfile
import logging

# Add the project root to the path
sys.path.insert(0, '/home/azureuser/agentic-rag-demo')

# Set up logging to capture the chunking messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("🔍 VERIFYING TOKEN-AWARE CHUNKING FIX")
print("=" * 60)

# Create a large document that should trigger chunking
large_content = """
This is a comprehensive technical document that contains extensive information about system architecture, implementation details, and operational procedures. The document is designed to provide thorough coverage of all aspects of the system, including detailed technical specifications, implementation guidelines, operational procedures, troubleshooting guides, and maintenance protocols. Each section contains comprehensive information that is essential for understanding the complete system architecture and its various components. The documentation covers both theoretical concepts and practical implementation details, ensuring that readers have access to all necessary information for successful system deployment and operation. Additionally, the document includes best practices, performance optimization guidelines, security considerations, and scalability recommendations. Implementation procedures are documented with clear, step-by-step instructions. Each procedure includes prerequisites, detailed steps, expected outcomes, and troubleshooting information. The documentation also covers advanced topics such as system integration, data migration, backup and recovery procedures, and disaster recovery planning. Performance monitoring and optimization strategies are discussed in detail, including metrics collection, analysis techniques, and optimization recommendations. Security protocols and compliance requirements are thoroughly documented, ensuring that all implementations meet industry standards and regulatory requirements. The document concludes with comprehensive appendices that include reference materials, configuration examples, troubleshooting guides, and frequently asked questions. These appendices provide quick access to detailed technical information.
""" * 100

print(f"📄 Test document size: {len(large_content):,} characters")

# Test token counting
try:
    import tiktoken
    encoding = tiktoken.encoding_for_model('text-embedding-3-large')
    tokens = len(encoding.encode(large_content))
    print(f"🔢 Token count: {tokens:,} tokens")
    
    if tokens > 8192:
        print("✅ Test document exceeds embedding limit - should trigger chunking")
    else:
        print("⚠️ Test document may be too small to trigger chunking")
        
except ImportError:
    print("⚠️ tiktoken not available")

# Create a temporary file to test with
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    f.write(large_content)
    temp_file = f.name

try:
    # Test the chunking functions directly first
    print("\n🧪 Testing chunking functions directly...")
    
    from core.document_processor import _split_large_content_token_aware, _split_large_content_fallback
    
    # Test token-aware splitting
    chunks = _split_large_content_token_aware(large_content, max_tokens=6000)
    print(f"✅ Token-aware splitting: {len(chunks)} chunks created")
    
    # Verify each chunk is within limits
    for i, chunk in enumerate(chunks[:3], 1):  # Check first 3 chunks
        chunk_len = len(chunk)
        try:
            chunk_tokens = len(encoding.encode(chunk))
            status = "✅ Within limits" if chunk_tokens <= 6000 else "❌ EXCEEDS LIMIT"
            print(f"   Chunk {i}: {chunk_len:,} chars, {chunk_tokens:,} tokens - {status}")
        except:
            print(f"   Chunk {i}: {chunk_len:,} chars")
    
    if len(chunks) > 3:
        print(f"   ... and {len(chunks) - 3} more chunks")
    
    # Test the full document processing pipeline
    print(f"\n🔧 Testing full document processing with chunk_to_docs...")
    
    # Read the temp file as bytes
    with open(temp_file, 'rb') as f:
        file_bytes = f.read()
    
    print(f"📄 File bytes: {len(file_bytes):,} bytes")
    
    # We'll need to mock the Azure OpenAI client for this test
    class MockAzureOpenAI:
        def __init__(self):
            self.embeddings = self
            
        def create(self, input, model):
            # Return mock embedding
            class MockResponse:
                def __init__(self):
                    self.data = [MockEmbedding()]
            
            class MockEmbedding:
                def __init__(self):
                    self.embedding = [0.1] * 3072  # Mock embedding vector
                    
            return MockResponse()
    
    # Import and test chunk_to_docs
    from core.document_processor import chunk_to_docs
    
    mock_client = MockAzureOpenAI()
    
    print("🔄 Calling chunk_to_docs with large file...")
    docs = chunk_to_docs(
        file_name=os.path.basename(temp_file),
        file_bytes=file_bytes,
        file_url="",
        oai_client=mock_client,
        embed_deployment="text-embedding-3-large"
    )
    
    print(f"\n📊 RESULTS:")
    print(f"   📄 Documents created: {len(docs)}")
    
    if len(docs) > 1:
        print("   ✅ SUCCESS: Multiple documents created - chunking is working!")
        
        # Analyze the results
        for i, doc in enumerate(docs[:3], 1):
            content = doc.get('page_chunk', '')
            content_len = len(content)
            
            try:
                content_tokens = len(encoding.encode(content))
                status = "✅ Within limits" if content_tokens <= 8192 else "❌ EXCEEDS LIMIT"
                print(f"   Doc {i}: {content_len:,} chars, {content_tokens:,} tokens - {status}")
            except:
                print(f"   Doc {i}: {content_len:,} chars")
                
        if len(docs) > 3:
            print(f"   ... and {len(docs) - 3} more documents")
            
        print(f"\n🎯 VERIFICATION COMPLETE")
        print(f"✅ Token-aware chunking fix is working correctly!")
        print(f"✅ Large files are now split into {len(docs)} manageable chunks")
        
    else:
        print("   ❌ FAILED: Only 1 document created - chunking may not be working")
        
        # Check if the single document is within limits
        if docs:
            content = docs[0].get('page_chunk', '')
            try:
                content_tokens = len(encoding.encode(content))
                if content_tokens > 8192:
                    print(f"   ❌ Single document has {content_tokens:,} tokens - EXCEEDS LIMIT!")
                else:
                    print(f"   ✅ Single document has {content_tokens:,} tokens - within limits")
            except:
                print(f"   Single document has {len(content):,} chars")

except Exception as e:
    print(f"❌ Error during verification: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Clean up
    if os.path.exists(temp_file):
        os.unlink(temp_file)

print("\n" + "=" * 60)
print("🎯 VERIFICATION SUMMARY")
print("If you see 'Multiple documents created' above, the fix is working!")
print("If you see 'Only 1 document created', there may still be an issue.")
