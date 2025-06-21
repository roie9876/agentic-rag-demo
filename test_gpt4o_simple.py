#!/usr/bin/env python3
"""
Simple test to verify GPT-4o image captioning works with Azure Blob Storage.
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
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("dotenv not available, using system environment variables")

def test_environment():
    """Test that environment is set up correctly."""
    logger.info("🔍 Checking environment variables...")
    
    required_vars = [
        "AZURE_OPENAI_ENDPOINT_41",
        "AZURE_OPENAI_KEY_41", 
        "AZURE_OPENAI_DEPLOYMENT_41",
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_CONTAINER"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"❌ Missing: {missing}")
        return False
        
    logger.info("✅ Environment variables OK")
    return True

def test_openai_client():
    """Test OpenAI client for GPT-4o."""
    logger.info("🔍 Testing OpenAI client...")
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY_41"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION_41", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_41")
        )
        
        # Test simple completion
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_41"),
            messages=[{"role": "user", "content": "Hello!"}],
            max_tokens=10
        )
        
        logger.info(f"✅ OpenAI client works: {response.choices[0].message.content}")
        return client
        
    except Exception as e:
        logger.error(f"❌ OpenAI client failed: {e}")
        return None

def test_blob_storage():
    """Test blob storage connectivity."""
    logger.info("🔍 Testing blob storage...")
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        blob_service = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )
        
        container_name = os.getenv("AZURE_STORAGE_CONTAINER")
        container_client = blob_service.get_container_client(container_name)
        
        # Check if container exists, create if not
        if not container_client.exists():
            container_client = blob_service.create_container(container_name)
            logger.info(f"✅ Created container: {container_name}")
        else:
            logger.info(f"✅ Container exists: {container_name}")
            
        return container_client
        
    except Exception as e:
        logger.error(f"❌ Blob storage failed: {e}")
        return None

def create_test_image():
    """Create a simple test image."""
    logger.info("🔍 Creating test image...")
    
    try:
        import io
        from PIL import Image, ImageDraw
        
        # Create test image
        img = Image.new('RGB', (300, 200), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Add some text and shapes
        draw.text((20, 20), "GPT-4o Test Image", fill='black')
        draw.text((20, 50), "This is a test for", fill='blue')
        draw.text((20, 80), "image captioning!", fill='red')
        draw.rectangle([20, 120, 280, 180], outline='green', width=3)
        draw.text((30, 140), "Rectangle with text", fill='green')
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        logger.info("✅ Test image created")
        return img_bytes.getvalue()
        
    except ImportError:
        logger.error("❌ PIL not available")
        return None
    except Exception as e:
        logger.error(f"❌ Image creation failed: {e}")
        return None

def test_gpt4o_image_captioning(client, image_bytes):
    """Test GPT-4o image captioning."""
    logger.info("🔍 Testing GPT-4o image captioning...")
    
    try:
        # Convert to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create message for GPT-4o
        messages = [
            {
                "role": "system", 
                "content": "You are an AI assistant that describes images clearly and accurately."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please describe what you see in this image in detail."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        # Call GPT-4o
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_41"),
            messages=messages,
            max_tokens=200,
            temperature=0.1
        )
        
        caption = response.choices[0].message.content.strip()
        logger.info(f"✅ GPT-4o caption: {caption}")
        return caption
        
    except Exception as e:
        logger.error(f"❌ GPT-4o captioning failed: {e}")
        return None

def test_blob_upload(container_client, image_bytes, image_name):
    """Test uploading image to blob storage."""
    logger.info(f"🔍 Testing blob upload: {image_name}")
    
    try:
        blob_client = container_client.get_blob_client(image_name)
        blob_client.upload_blob(image_bytes, overwrite=True)
        
        url = blob_client.url
        logger.info(f"✅ Image uploaded: {url}")
        return url
        
    except Exception as e:
        logger.error(f"❌ Blob upload failed: {e}")
        return None

def main():
    """Run the complete test."""
    logger.info("🚀 Starting GPT-4o + Blob Storage test...")
    
    # Test environment
    if not test_environment():
        return
        
    # Test OpenAI client
    client = test_openai_client()
    if not client:
        return
        
    # Test blob storage
    container_client = test_blob_storage()
    if not container_client:
        return
        
    # Create test image
    image_bytes = create_test_image()
    if not image_bytes:
        return
        
    # Test GPT-4o captioning
    caption = test_gpt4o_image_captioning(client, image_bytes)
    if not caption:
        return
        
    # Test blob upload
    url = test_blob_upload(container_client, image_bytes, "test_gpt4o_image.png")
    if not url:
        return
        
    logger.info("🎉 All tests passed!")
    logger.info(f"📸 Image URL: {url}")
    logger.info(f"📝 Caption: {caption}")
    logger.info("✅ GPT-4o multimodal pipeline is working!")

if __name__ == "__main__":
    main()
