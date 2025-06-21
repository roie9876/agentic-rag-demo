#!/usr/bin/env python3
"""
Test GPT-4o multimodal processing with image extraction and captioning.
This script tests the full pipeline: PDF -> image extraction -> blob storage -> GPT-4o captions.
"""

import os
import sys
import base64
import logging
from pathlib import Path

# Add the current directory to the path for imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test imports
try:
    from chunking.multimodal_processor import MultimodalProcessor
    from openai import AzureOpenAI
    logger.info("✅ Successfully imported MultimodalProcessor and AzureOpenAI")
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    sys.exit(1)

def test_environment_setup():
    """Test that all required environment variables are set."""
    logger.info("🔍 Testing environment setup...")
    
    required_vars = [
        "AZURE_OPENAI_ENDPOINT_41",
        "AZURE_OPENAI_KEY_41", 
        "AZURE_OPENAI_DEPLOYMENT_41",
        "DOCUMENT_INTEL_ENDPOINT",
        "DOCUMENT_INTEL_KEY",
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_CONTAINER"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def test_openai_client():
    """Test OpenAI client initialization."""
    logger.info("🔍 Testing OpenAI client...")
    
    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY_41"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION_41", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_41")
        )
        
        # Test a simple completion
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_41"),
            messages=[{"role": "user", "content": "Say 'Hello from GPT-4o!'"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        logger.info(f"✅ OpenAI client working: {result}")
        return client
        
    except Exception as e:
        logger.error(f"❌ OpenAI client error: {e}")
        return None

def test_multimodal_processor():
    """Test MultimodalProcessor initialization."""
    logger.info("🔍 Testing MultimodalProcessor...")
    
    try:
        processor = MultimodalProcessor()
        logger.info("✅ MultimodalProcessor initialized successfully")
        
        # Check if Document Intelligence client is available
        if processor.doc_client:
            logger.info("✅ Document Intelligence client available")
        else:
            logger.warning("⚠️ Document Intelligence client not available")
        
        # Check if blob storage is available
        if processor.container_client:
            logger.info("✅ Blob storage client available")
        else:
            logger.warning("⚠️ Blob storage client not available")
        
        return processor
        
    except Exception as e:
        logger.error(f"❌ MultimodalProcessor error: {e}")
        return None

def create_test_pdf_with_image():
    """Create a simple test PDF with an image for testing."""
    try:
        import fitz  # PyMuPDF
        import io
        from PIL import Image, ImageDraw
        
        # Create a simple test image
        img = Image.new('RGB', (200, 100), color='lightblue')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Test Image", fill='black')
        draw.rectangle([10, 30, 190, 80], outline='red', width=2)
        
        # Save image to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Create PDF with the image
        pdf_doc = fitz.open()
        page = pdf_doc.new_page()
        
        # Add some text
        page.insert_text((50, 50), "This is a test PDF with an image below:")
        
        # Insert the image
        img_rect = fitz.Rect(50, 100, 250, 200)
        page.insert_image(img_rect, stream=img_bytes.getvalue())
        
        # Get PDF bytes
        pdf_bytes = pdf_doc.tobytes()
        pdf_doc.close()
        
        return pdf_bytes
        
    except ImportError:
        logger.warning("⚠️ PyMuPDF not available, cannot create test PDF")
        return None
    except Exception as e:
        logger.error(f"❌ Error creating test PDF: {e}")
        return None

def test_full_pipeline():
    """Test the complete multimodal pipeline."""
    logger.info("🔍 Testing full multimodal pipeline...")
    
    # Create OpenAI client
    openai_client = test_openai_client()
    if not openai_client:
        return False
    
    # Create multimodal processor
    processor = test_multimodal_processor()
    if not processor:
        return False
    
    # Create test PDF
    pdf_bytes = create_test_pdf_with_image()
    if not pdf_bytes:
        logger.warning("⚠️ Could not create test PDF, using existing file if available")
        return False
    
    try:
        # Test the enhanced processing with GPT-4o image captioning
        logger.info("📝 Testing document processing with image extraction and captioning...")
        
        result = processor.process_document_with_images(
            pdf_bytes, 
            "test_multimodal.pdf", 
            openai_client
        )
        
        if result:
            logger.info("✅ Document processing completed successfully")
            
            text_segments = result.get("text_segments", [])
            images = result.get("images", [])
            
            logger.info(f"📄 Extracted {len(text_segments)} text segments")
            logger.info(f"🖼️ Processed {len(images)} images")
            
            for i, img in enumerate(images):
                caption = img.get("caption", "No caption")
                url = img.get("url", "No URL")
                logger.info(f"   Image {i+1}: {caption[:100]}{'...' if len(caption) > 100 else ''}")
                logger.info(f"   URL: {url}")
            
            return True
        else:
            logger.error("❌ Document processing returned no result")
            return False
            
    except Exception as e:
        logger.error(f"❌ Pipeline test error: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🚀 Starting GPT-4o multimodal processing tests...")
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("OpenAI Client", lambda: test_openai_client() is not None),
        ("Multimodal Processor", lambda: test_multimodal_processor() is not None),
        ("Full Pipeline", test_full_pipeline)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            logger.error(f"❌ FAILED: {test_name} - {e}")
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! GPT-4o multimodal processing is ready!")
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")

if __name__ == "__main__":
    main()
