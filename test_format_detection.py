#!/usr/bin/env python3
"""
Test script to verify file format detection and dynamic content-type selection.
Tests both real PDFs and files with misleading extensions.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Test with our file format detector
from utils.file_format_detector import FileFormatDetector
from chunking.multimodal_processor import MultimodalProcessor

def create_test_files():
    """Create test files with misleading extensions."""
    test_files = {}
    
    # HTML content with .pdf extension
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Document</title>
</head>
<body>
    <h1>This is HTML content</h1>
    <p>Even though it has a .pdf extension!</p>
</body>
</html>"""
    
    # Create test HTML file with PDF extension
    html_as_pdf_path = project_root / "test_html_as_pdf.pdf"
    with open(html_as_pdf_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    test_files['html_as_pdf'] = html_as_pdf_path
    
    # Plain text with .pdf extension
    text_content = """This is plain text content.
It has multiple lines.
And should be detected as text, not PDF.
Even though the filename suggests it's a PDF!"""
    
    text_as_pdf_path = project_root / "test_text_as_pdf.pdf"
    with open(text_as_pdf_path, 'w', encoding='utf-8') as f:
        f.write(text_content)
    test_files['text_as_pdf'] = text_as_pdf_path
    
    return test_files

def test_format_detection():
    """Test file format detection with various scenarios."""
    print("="*60)
    print("TESTING FILE FORMAT DETECTION")
    print("="*60)
    
    # Create test files
    test_files = create_test_files()
    
    for test_name, file_path in test_files.items():
        print(f"\nTesting {test_name}: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Test format detection
            detected_format, reason = FileFormatDetector.detect_format(file_bytes, str(file_path))
            content_type = FileFormatDetector.get_content_type(detected_format) if detected_format else "unknown"
            supported = FileFormatDetector.is_format_supported_by_document_intelligence(detected_format) if detected_format else False
            
            print(f"  File size: {len(file_bytes)} bytes")
            print(f"  Detected format: {detected_format}")
            print(f"  Detection reason: {reason}")
            print(f"  Content-type: {content_type}")
            print(f"  Supported by Document Intelligence: {supported}")
            
            # Show first 100 bytes
            print(f"  First 100 bytes: {file_bytes[:100]}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Clean up test files
    for file_path in test_files.values():
        try:
            file_path.unlink()
            print(f"Cleaned up: {file_path}")
        except Exception as e:
            print(f"Warning: Could not clean up {file_path}: {e}")

def test_multimodal_processor():
    """Test the multimodal processor with format detection."""
    print("\n" + "="*60)
    print("TESTING MULTIMODAL PROCESSOR WITH FORMAT DETECTION")
    print("="*60)
    
    try:
        # Initialize processor
        processor = MultimodalProcessor()
        
        if not processor.doc_client:
            print("WARNING: Document Intelligence client not available - creating test files only")
            return
        
        # Create test files
        test_files = create_test_files()
        
        for test_name, file_path in test_files.items():
            print(f"\nTesting multimodal processing for {test_name}: {file_path}")
            
            try:
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                
                # Test processing
                result = processor.process_document(file_bytes, str(file_path))
                
                if result:
                    print(f"  SUCCESS: Document processed successfully")
                    print(f"  Text segments: {len(result.get('text_segments', []))}")
                    print(f"  Images: {len(result.get('images', []))}")
                else:
                    print(f"  No result returned")
                
            except Exception as e:
                print(f"  Expected error (format not supported): {e}")
        
        # Clean up test files
        for file_path in test_files.values():
            try:
                file_path.unlink()
            except Exception:
                pass
                
    except Exception as e:
        print(f"Error testing multimodal processor: {e}")

def test_pdf_header_scenarios():
    """Test various PDF header scenarios."""
    print("\n" + "="*60)
    print("TESTING PDF HEADER SCENARIOS")
    print("="*60)
    
    # Test scenarios
    scenarios = [
        ("Standard PDF", b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"),
        ("PDF with extra content", b"Some junk%PDF-1.4\n"),
        ("HTML pretending to be PDF", b"<!DOCTYPE html><html><body>Fake PDF</body></html>"),
        ("Binary junk", b"\x00\x01\x02\x03\x04\x05\x06\x07"),
        ("Empty file", b""),
        ("Very small file", b"%PDF"),
    ]
    
    for scenario_name, content in scenarios:
        print(f"\nTesting: {scenario_name}")
        detected_format, reason = FileFormatDetector.detect_format(content, f"test_{scenario_name.lower().replace(' ', '_')}.pdf")
        content_type = FileFormatDetector.get_content_type(detected_format) if detected_format else "unknown"
        
        print(f"  Content: {content[:50]}...")
        print(f"  Detected format: {detected_format}")
        print(f"  Reason: {reason}")
        print(f"  Content-type: {content_type}")

if __name__ == "__main__":
    print("Testing file format detection and dynamic content-type selection...")
    
    # Test format detection
    test_format_detection()
    
    # Test PDF header scenarios
    test_pdf_header_scenarios()
    
    # Test multimodal processor
    test_multimodal_processor()
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
