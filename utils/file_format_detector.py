"""
File format detection utility that analyzes file headers to determine the real file format.
Supports common formats that Document Intelligence can process.
"""

import logging
from typing import Tuple, Optional


class FileFormatDetector:
    """Detects file format based on file headers/magic bytes."""
    
    # Magic bytes for different file formats that Document Intelligence supports
    FORMAT_SIGNATURES = {
        # PDF formats
        'pdf': [
            b'%PDF-',
        ],
        # Microsoft Office formats (modern XML-based)
        'docx': [
            b'PK\x03\x04',  # ZIP header (DOCX is a ZIP file)
        ],
        'xlsx': [
            b'PK\x03\x04',  # ZIP header (XLSX is a ZIP file)
        ],
        'pptx': [
            b'PK\x03\x04',  # ZIP header (PPTX is a ZIP file)
        ],
        # Legacy Microsoft Office formats
        'doc': [
            b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',  # OLE2 signature
        ],
        'xls': [
            b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',  # OLE2 signature
        ],
        'ppt': [
            b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',  # OLE2 signature
        ],
        # Image formats
        'png': [
            b'\x89PNG\r\n\x1a\n',
        ],
        'jpeg': [
            b'\xff\xd8\xff\xe0',
            b'\xff\xd8\xff\xe1',
            b'\xff\xd8\xff\xe2',
            b'\xff\xd8\xff\xe3',
            b'\xff\xd8\xff\xe8',
            b'\xff\xd8\xff\xdb',
        ],
        'jpg': [
            b'\xff\xd8\xff\xe0',
            b'\xff\xd8\xff\xe1',
            b'\xff\xd8\xff\xe2',
            b'\xff\xd8\xff\xe3',
            b'\xff\xd8\xff\xe8',
            b'\xff\xd8\xff\xdb',
        ],
        'tiff': [
            b'II*\x00',  # Little-endian TIFF
            b'MM\x00*',  # Big-endian TIFF
        ],
        'tif': [
            b'II*\x00',  # Little-endian TIFF
            b'MM\x00*',  # Big-endian TIFF
        ],
        'bmp': [
            b'BM',
        ],
        # HTML/XML formats
        'html': [
            b'<!DOCTYPE html',
            b'<html',
            b'<HTML',
        ],
        'xml': [
            b'<?xml',
        ],
        # RTF format
        'rtf': [
            b'{\\rtf',
        ],
        # Plain text (no specific signature, detected by absence of other formats)
        'txt': [],
    }
    
    # Content types for Document Intelligence API
    CONTENT_TYPE_MAPPING = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'doc': 'application/msword',
        'xls': 'application/vnd.ms-excel',
        'ppt': 'application/vnd.ms-powerpoint',
        'png': 'image/png',
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'tiff': 'image/tiff',
        'tif': 'image/tiff',
        'bmp': 'image/bmp',
        'html': 'text/html',
        'xml': 'application/xml',
        'rtf': 'application/rtf',
        'txt': 'text/plain',
    }
    
    @classmethod
    def detect_format(cls, file_bytes: bytes, filename: str = "") -> Tuple[Optional[str], str]:
        """
        Detect the real file format based on file headers.
        
        Args:
            file_bytes: Binary content of the file
            filename: Original filename (for logging and fallback)
            
        Returns:
            tuple: (detected_format, confidence_reason)
                   detected_format is None if no format could be detected
        """
        if not file_bytes:
            return None, "File is empty"
        
        # Check if file is too small for meaningful detection
        if len(file_bytes) < 4:
            return None, f"File too small ({len(file_bytes)} bytes)"
        
        # Get first 32 bytes for header analysis (most signatures are within first 32 bytes)
        header = file_bytes[:32]
        
        # Special handling for ZIP-based formats (Office documents)
        if header.startswith(b'PK\x03\x04'):
            return cls._detect_office_format(file_bytes, filename)
        
        # Check for other format signatures
        for format_name, signatures in cls.FORMAT_SIGNATURES.items():
            if format_name in ['docx', 'xlsx', 'pptx']:  # Skip ZIP-based formats (handled above)
                continue
                
            for signature in signatures:
                if header.startswith(signature):
                    return format_name, f"Detected by header signature: {signature.hex()}"
        
        # Enhanced HTML detection - check for HTML tags anywhere in the first 2KB
        first_2kb = file_bytes[:2048].lower()
        
        # More comprehensive HTML pattern matching
        html_patterns = [
            b'<!doctype html',
            b'<html',
            b'<head>',
            b'<body>',
            b'<meta',
            b'<title>',
            b'<div',
            b'<p>',
            b'<script',
            b'<style',
            b'href=',
            b'src=',
            b'xmlns=',
            b'<br',
            b'<span',
            b'<a ',
            b'<h1>',
            b'<h2>',
            b'<h3>',
        ]
        
        html_score = sum(1 for pattern in html_patterns if pattern in first_2kb)
        
        # If we find multiple HTML indicators, it's likely HTML
        if html_score >= 2:
            return 'html', f"Detected HTML tags in content (score: {html_score})"
        
        # Check for XML content
        if b'<?xml' in first_2kb or (b'<' in first_2kb and b'xmlns' in first_2kb):
            return 'xml', "Detected XML content"
        
        # Check for JSON content
        stripped = file_bytes.strip()
        if (stripped.startswith(b'{') and stripped.endswith(b'}')) or (stripped.startswith(b'[') and stripped.endswith(b']')):
            return 'json', "Detected JSON structure"
        
        # Check if it's likely plain text by examining character distribution
        if cls._is_likely_text(file_bytes):
            # For small files with some HTML-like content, prefer HTML
            if len(file_bytes) < 5000 and (b'<' in file_bytes and b'>' in file_bytes):
                return 'html', "Small file with HTML-like tags"
            else:
                return 'txt', "Appears to be plain text based on character analysis"
        
        return None, "No recognizable format signature found"
    
    @classmethod
    def _detect_office_format(cls, file_bytes: bytes, filename: str) -> Tuple[Optional[str], str]:
        """
        Detect specific Office format for ZIP-based files.
        
        Args:
            file_bytes: Binary content of the file
            filename: Original filename for hint
            
        Returns:
            tuple: (detected_format, confidence_reason)
        """
        try:
            # Look for Office-specific content in the ZIP structure
            # We'll examine the first few KB for Office-specific patterns
            first_2kb = file_bytes[:2048]
            
            # Look for Office XML namespace patterns
            if b'word/' in first_2kb or b'wordprocessingml' in first_2kb:
                return 'docx', "Found Word XML namespace in ZIP content"
            elif b'xl/' in first_2kb or b'spreadsheetml' in first_2kb:
                return 'xlsx', "Found Excel XML namespace in ZIP content"
            elif b'ppt/' in first_2kb or b'presentationml' in first_2kb:
                return 'pptx', "Found PowerPoint XML namespace in ZIP content"
            
            # Fallback to filename extension for ZIP files
            filename_lower = filename.lower()
            if filename_lower.endswith('.docx'):
                return 'docx', "ZIP file with .docx extension"
            elif filename_lower.endswith('.xlsx'):
                return 'xlsx', "ZIP file with .xlsx extension"
            elif filename_lower.endswith('.pptx'):
                return 'pptx', "ZIP file with .pptx extension"
            
            # Generic ZIP file - default to DOCX as it's most common
            return 'docx', "Generic ZIP file, defaulting to DOCX"
            
        except Exception as e:
            logging.warning(f"Error analyzing Office format: {e}")
            return None, f"Error analyzing ZIP content: {e}"
    
    @classmethod
    def _is_likely_text(cls, file_bytes: bytes) -> bool:
        """
        Determine if file content is likely plain text.
        
        Args:
            file_bytes: Binary content to analyze
            
        Returns:
            bool: True if content appears to be text
        """
        if not file_bytes:
            return False
        
        # Sample first 1KB for analysis
        sample = file_bytes[:1024]
        
        try:
            # Try to decode as UTF-8
            text = sample.decode('utf-8')
            
            # Count printable characters
            printable_chars = sum(1 for c in text if c.isprintable() or c.isspace())
            ratio = printable_chars / len(text) if text else 0
            
            # If more than 95% printable characters, likely text
            return ratio > 0.95
            
        except UnicodeDecodeError:
            # If can't decode as UTF-8, probably not text
            return False
    
    @classmethod
    def get_content_type(cls, format_name: str) -> str:
        """
        Get the appropriate content-type for Document Intelligence API.
        
        Args:
            format_name: Detected format name
            
        Returns:
            str: Content-type string for API request
        """
        return cls.CONTENT_TYPE_MAPPING.get(format_name, 'application/octet-stream')
    
    @classmethod
    def get_supported_formats(cls) -> list:
        """Get list of supported format names."""
        return list(cls.FORMAT_SIGNATURES.keys())
    
    @classmethod
    def is_format_supported_by_document_intelligence(cls, format_name: str) -> bool:
        """
        Check if a format is supported by Document Intelligence.
        
        Args:
            format_name: Format name to check
            
        Returns:
            bool: True if supported
        """
        # Document Intelligence supported formats
        supported = {
            'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt',
            'png', 'jpeg', 'jpg', 'tiff', 'tif', 'bmp',
            'html', 'txt'
        }
        return format_name in supported
    
    @classmethod
    def enhanced_detect_format(cls, file_bytes: bytes, filename: str = "") -> Tuple[Optional[str], str]:
        """
        Enhanced format detection with more aggressive pattern matching for edge cases.
        This is used as a fallback when the standard detection fails.
        
        Args:
            file_bytes: Binary content of the file
            filename: Original filename (for logging and fallback)
            
        Returns:
            tuple: (detected_format, confidence_reason)
        """
        if not file_bytes or len(file_bytes) < 4:
            return None, "File too small or empty"
        
        # Sample first 2KB for analysis
        first_2kb = file_bytes[:2048].lower()
        
        # Very aggressive HTML detection
        html_indicators = [
            b'<!doctype',
            b'<html',
            b'<head',
            b'<body',
            b'<meta',
            b'<title',
            b'<div',
            b'<p>',
            b'<script',
            b'<style',
            b'href=',
            b'src=',
            b'xmlns',
            b'<br',
            b'<span',
            b'<a ',
            b'javascript',
            b'function(',
            b'var ',
            b'class=',
            b'id=',
        ]
        
        html_count = sum(1 for indicator in html_indicators if indicator in first_2kb)
        
        # Lower threshold for HTML detection in enhanced mode
        if html_count >= 2:
            return 'html', f"Enhanced HTML detection (indicators: {html_count})"
        
        # Check for XML patterns
        if b'<?xml' in first_2kb or b'<xml' in first_2kb:
            return 'xml', "Enhanced XML detection"
        
        # Check for JSON patterns
        stripped = file_bytes.strip()
        if stripped.startswith(b'{') or stripped.startswith(b'['):
            try:
                # Try to find JSON-like patterns
                content_str = stripped.decode('utf-8', errors='ignore')
                if ('{' in content_str and '}' in content_str) or ('"' in content_str and ':' in content_str):
                    return 'json', "Enhanced JSON detection"
            except:
                pass
        
        # Very permissive text detection
        try:
            decoded = file_bytes.decode('utf-8', errors='ignore')
            if len(decoded.strip()) > 0:
                printable_count = sum(1 for c in decoded if c.isprintable() or c.isspace())
                printable_ratio = printable_count / len(decoded)
                
                # Lower threshold for text detection in enhanced mode
                if printable_ratio > 0.7:
                    # Check for HTML-like content in text
                    if '<' in decoded and '>' in decoded and printable_ratio > 0.8:
                        return 'html', f"Enhanced HTML detection in text (printable: {printable_ratio:.2f})"
                    else:
                        return 'txt', f"Enhanced text detection (printable: {printable_ratio:.2f})"
        except:
            pass
        
        # For very small files, make educated guesses
        if len(file_bytes) < 1000:
            if b'<' in file_bytes and b'>' in file_bytes:
                return 'html', "Small file with angle brackets"
            elif any(c < 32 and c not in [9, 10, 13] for c in file_bytes):
                return None, "Small binary file"
            else:
                return 'txt', "Small text file"
        
        return None, "Enhanced detection failed"
