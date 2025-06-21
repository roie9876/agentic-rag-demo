#!/usr/bin/env python3
"""
Test the enhanced multimodal processor with problematic files
"""

import os
import sys
import logging

# Add the project root to Python path
sys.path.append('/Users/robenhai/agentic-rag-demo')

from chunking.multimodal_processor import MultimodalProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_enhanced_processor():
    """Test the enhanced multimodal processor with various problematic files"""
    
    # Initialize the processor
    processor = MultimodalProcessor()
    
    if not processor.doc_client:
        print("❌ Document Intelligence client not initialized")
        return
    
    # Test case 1: HTML content with .pdf extension (like user's problematic file)
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Important Document</title>
</head>
<body>
    <h1>Company Report</h1>
    <p>This document contains important business information.</p>
    <div>
        <h2>Financial Summary</h2>
        <p>Revenue increased by 15% this quarter.</p>
        <p>New product lines are performing well.</p>
    </div>
    <div>
        <h2>Market Analysis</h2>
        <p>The market shows strong growth potential.</p>
        <ul>
            <li>Customer satisfaction: 92%</li>
            <li>Market share: 25%</li>
            <li>Brand recognition: 85%</li>
        </ul>
    </div>
</body>
</html>"""
    
    print("🔄 Testing HTML content with .pdf extension")
    print(f"Content size: {len(html_content)} characters")
    print()
    
    try:
        result = processor.process_document(html_content.encode(), "business_report.pdf")
        if result:
            print("✅ Success! Document processed successfully")
            print(f"Text segments found: {len(result.get('text_segments', []))}")
            print(f"Images found: {len(result.get('images', []))}")
            
            # Show some extracted content
            if result.get('text_segments'):
                print("Sample extracted text:")
                for i, segment in enumerate(result['text_segments'][:3]):
                    print(f"  Segment {i+1}: {segment['content'][:100]}...")
        else:
            print("❌ No result returned")
            
    except Exception as e:
        print(f"❌ Processing failed: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test case 2: Plain text with .pdf extension
    text_content = """
    BUSINESS MEMO
    
    To: All Staff
    From: Management
    Date: Today
    Subject: Important Updates
    
    Please note the following updates:
    
    1. New office hours: 9 AM - 6 PM
    2. Parking changes take effect next week
    3. Holiday schedule has been updated
    
    Thank you for your attention.
    """
    
    print("🔄 Testing plain text content with .pdf extension")
    print(f"Content size: {len(text_content)} characters")
    print()
    
    try:
        result = processor.process_document(text_content.encode(), "memo.pdf")
        if result:
            print("✅ Success! Document processed successfully")
            print(f"Text segments found: {len(result.get('text_segments', []))}")
            
            # Show some extracted content
            if result.get('text_segments'):
                print("Sample extracted text:")
                for i, segment in enumerate(result['text_segments'][:2]):
                    print(f"  Segment {i+1}: {segment['content'][:100]}...")
        else:
            print("❌ No result returned")
            
    except Exception as e:
        print(f"❌ Processing failed: {e}")

if __name__ == "__main__":
    test_enhanced_processor()
