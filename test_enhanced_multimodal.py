#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Load environment manually
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                while '${' in value and '}' in value:
                    start = value.find('${')
                    end = value.find('}', start)
                    if start != -1 and end != -1:
                        var_name = value[start+2:end]
                        var_value = os.environ.get(var_name, '')
                        value = value[:start] + var_value + value[end+1:]
                    else:
                        break
                os.environ[key] = value

print("🧪 Testing Enhanced Multimodal Processing with GPT-4o Image Descriptions...")

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent))

try:
    from chunking.multimodal_processor import MultimodalProcessor
    from openai import AzureOpenAI
    
    print("✅ Imports successful")
    
    # Initialize OpenAI client for image descriptions
    openai_client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY_41"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_41"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION_41")
    )
    print("✅ OpenAI client initialized")
    
    # Initialize enhanced multimodal processor
    processor = MultimodalProcessor()
    print("✅ MultimodalProcessor initialized")
    
    # Test with Hebrew PDF
    pdf_path = "/Users/robenhai/Downloads/תעשייה אווירית – ויקיפדיה.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            file_bytes = f.read()
        
        print(f"📄 Testing with {os.path.basename(pdf_path)} ({len(file_bytes):,} bytes)")
        
        # Test enhanced processing with image descriptions
        result = processor.process_document_with_images(
            file_bytes, 
            os.path.basename(pdf_path), 
            openai_client
        )
        
        if result:
            print("✅ Enhanced document processing successful!")
            print(f"📝 Text segments: {len(result.get('text_segments', []))}")
            print(f"🖼️  Images with descriptions: {len(result.get('images', []))}")
            
            # Show image descriptions
            for i, image in enumerate(result.get('images', [])[:2]):  # Show first 2 images
                print(f"\n🎨 Image {i+1}:")
                print(f"  📄 Page: {image.get('page_number')}")
                print(f"  📐 Size: {image.get('width')}x{image.get('height')}")
                print(f"  🔗 URL: {image.get('url', 'N/A')[:50]}...")
                print(f"  💬 Description: {image.get('caption', 'No description')[:150]}...")
                
        else:
            print("❌ Enhanced processing failed")
    else:
        print("❌ Test PDF not found")
        
except Exception as e:
    print(f"💥 Error: {e}")
    import traceback
    traceback.print_exc()
