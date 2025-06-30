"""
Document Processing Information Display Module

This module provides UI components for displaying document processing information
to help users understand what tools and methods are being used for extraction.
"""

import streamlit as st
from typing import Optional


def display_processing_info(
    file_name: str, 
    file_ext: str, 
    chunker_type: Optional[str] = None, 
    show_capabilities: bool = True
) -> None:
    """
    Display processing information for a file to help users understand 
    what tools and methods are being used for extraction.
    
    Args:
        file_name: The name of the file being processed
        file_ext: The file extension (with or without leading dot)
        chunker_type: Optional chunker type (e.g., "MultimodalChunker")
        show_capabilities: Whether to show processing capabilities
    """
    # Normalize extension to include leading dot
    ext = file_ext.lower()
    if not ext.startswith('.'):
        ext = f'.{ext}'
    
    # File type mapping
    file_type_map = {
        '.pdf': '📄 PDF Document',
        '.docx': '📝 Word Document', 
        '.pptx': '📊 PowerPoint Presentation',
        '.xlsx': '📈 Excel Spreadsheet',
        '.xls': '📈 Excel Spreadsheet',
        '.csv': '📈 CSV Data',
        '.png': '🖼️ PNG Image',
        '.jpg': '🖼️ JPEG Image',
        '.jpeg': '🖼️ JPEG Image',
        '.bmp': '🖼️ BMP Image',
        '.tiff': '🖼️ TIFF Image',
        '.txt': '📝 Text File',
        '.md': '📝 Markdown File',
        '.json': '🔧 JSON Data',
        '.html': '🌐 HTML Document',
        '.vtt': '🎬 Video Transcript'
    }
    
    # Processing method mapping
    processing_map = {
        '.pdf': ('🔍 Azure Document Intelligence', 'Advanced OCR, layout analysis, table extraction'),
        '.docx': ('🔍 Azure Document Intelligence', 'Layout analysis, text extraction, formatting preservation'),
        '.pptx': ('🔍 Azure Document Intelligence', 'Slide analysis, text extraction, layout understanding'),
        '.xlsx': ('🐼 Pandas Parser', 'Structured spreadsheet data extraction'),
        '.xls': ('🐼 Pandas Parser', 'Legacy Excel format processing'),
        '.csv': ('🐼 Pandas Parser', 'Comma-separated values processing'),
        '.png': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.jpg': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.jpeg': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.bmp': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.tiff': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.txt': ('📝 Simple Text Parser', 'Direct text content extraction'),
        '.md': ('📝 Markdown Parser', 'Markdown formatting with text extraction'),
        '.json': ('🔧 JSON Parser', 'Structured JSON data processing'),
        '.html': ('🔍 Azure Document Intelligence', 'HTML structure and content analysis'),
        '.vtt': ('🎬 Transcript Processor', 'Video subtitle and timing extraction')
    }
    
    file_type = file_type_map.get(ext, f'📄 {ext.upper()} File')
    method, capabilities = processing_map.get(ext, ('🔗 LangChain Chunker', 'General purpose text processing'))
    
    info_container = st.container()
    with info_container:
        col1, col2, col3 = st.columns([2, 3, 3])
        
        with col1:
            st.markdown(f"**File:** {file_type}")
            st.markdown(f"📋 `{file_name}`")
            
        with col2:
            st.markdown(f"**Processing Tool:** {method}")
            if show_capabilities:
                st.markdown(f"⚙️ {capabilities}")
                
        with col3:
            if ext in ['.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.html']:
                st.markdown("🎯 **Advanced Features:**")
                features = ["✅ Layout Analysis", "✅ Smart Text Extraction", "✅ OCR Processing"]
                if chunker_type == "MultimodalChunker":
                    features.extend(["✅ Figure Detection", "✅ AI Image Captions", "✅ Multimodal Processing"])
                for feature in features:
                    st.markdown(f"   {feature}")


def get_processing_method_info(file_ext: str) -> tuple[str, str]:
    """
    Get processing method information for a file extension.
    
    Args:
        file_ext: File extension (with or without leading dot)
        
    Returns:
        Tuple of (method_name, capabilities_description)
    """
    # Normalize extension
    ext = file_ext.lower()
    if not ext.startswith('.'):
        ext = f'.{ext}'
    
    processing_map = {
        '.pdf': ('🔍 Azure Document Intelligence', 'Advanced OCR, layout analysis, table extraction'),
        '.docx': ('🔍 Azure Document Intelligence', 'Layout analysis, text extraction, formatting preservation'),
        '.pptx': ('🔍 Azure Document Intelligence', 'Slide analysis, text extraction, layout understanding'),
        '.xlsx': ('🐼 Pandas Parser', 'Structured spreadsheet data extraction'),
        '.xls': ('🐼 Pandas Parser', 'Legacy Excel format processing'),
        '.csv': ('🐼 Pandas Parser', 'Comma-separated values processing'),
        '.png': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.jpg': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.jpeg': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.bmp': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.tiff': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.txt': ('📝 Simple Text Parser', 'Direct text content extraction'),
        '.md': ('📝 Markdown Parser', 'Markdown formatting with text extraction'),
        '.json': ('🔧 JSON Parser', 'Structured JSON data processing'),
        '.html': ('🔍 Azure Document Intelligence', 'HTML structure and content analysis'),
        '.vtt': ('🎬 Transcript Processor', 'Video subtitle and timing extraction')
    }
    
    return processing_map.get(ext, ('🔗 LangChain Chunker', 'General purpose text processing'))


def get_file_type_display(file_ext: str) -> str:
    """
    Get display-friendly file type string.
    
    Args:
        file_ext: File extension (with or without leading dot)
        
    Returns:
        Display string for the file type
    """
    # Normalize extension
    ext = file_ext.lower()
    if not ext.startswith('.'):
        ext = f'.{ext}'
    
    file_type_map = {
        '.pdf': '📄 PDF Document',
        '.docx': '📝 Word Document', 
        '.pptx': '📊 PowerPoint Presentation',
        '.xlsx': '📈 Excel Spreadsheet',
        '.xls': '📈 Excel Spreadsheet',
        '.csv': '📈 CSV Data',
        '.png': '🖼️ PNG Image',
        '.jpg': '🖼️ JPEG Image',
        '.jpeg': '🖼️ JPEG Image',
        '.bmp': '🖼️ BMP Image',
        '.tiff': '🖼️ TIFF Image',
        '.txt': '📝 Text File',
        '.md': '📝 Markdown File',
        '.json': '🔧 JSON Data',
        '.html': '🌐 HTML Document',
        '.vtt': '🎬 Video Transcript'
    }
    
    return file_type_map.get(ext, f'📄 {ext.upper()} File')
