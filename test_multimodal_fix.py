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
                # Handle variable expansion like ${OTHER_VAR}
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

print("🧪 Testing MultimodalProcessor with fixed Document Intelligence client...")

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent))

try:
    from chunking.multimodal_processor import MultimodalProcessor
    print("✅ MultimodalProcessor imported successfully")
    
    # Initialize processor
    processor = MultimodalProcessor()
    print("✅ MultimodalProcessor initialized")
    
    # Test with Hebrew PDF
    pdf_path = "/Users/robenhai/Downloads/תעשייה אווירית – ויקיפדיה.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            file_bytes = f.read()
        
        print(f"📄 Testing with {os.path.basename(pdf_path)} ({len(file_bytes):,} bytes)")
        
        # Process the document
        result = processor.process_document(file_bytes, os.path.basename(pdf_path))
        
        if result:
            print("✅ Document processed successfully!")
            print(f"📝 Text segments: {len(result.get('text_segments', []))}")
            print(f"🖼️  Images found: {len(result.get('images', []))}")
            
            # Show preview of first text segment
            if result.get('text_segments'):
                first_segment = result['text_segments'][0]
                preview = first_segment['content'][:100] + "..." if len(first_segment['content']) > 100 else first_segment['content']
                print(f"📖 First segment preview: {repr(preview)}")
        else:
            print("❌ Document processing failed")
    else:
        print("❌ Test PDF not found")
        
except Exception as e:
    print(f"💥 Error: {e}")
    import traceback
    traceback.print_exc()
