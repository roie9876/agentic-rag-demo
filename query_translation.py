#!/usr/bin/env python3
"""
Query translation helper for Hebrew to English
"""

def translate_hebrew_to_english(query: str) -> str:
    """
    Simple translation of common Hebrew queries to English for better search results
    """
    
    # Common Hebrew to English translations for technical queries
    translations = {
        # Disk/Storage related
        "דיסק": "disk",
        "דיסקים": "disks", 
        "אחסון": "storage",
        "טבלת השוואה": "comparison table",
        "השוואה": "comparison",
        "סוגי": "types",
        "בין": "between",
        "תכונות": "features",
        "יכולות": "capabilities",
        
        # Azure specific
        "אולטרה": "Ultra",
        "פרמיום": "Premium",
        "סטנדרט": "Standard",
        
        # Actions
        "תערוך": "create",
        "הצג": "show",
        "מצא": "find",
        "חפש": "search",
        
        # Question words
        "מה": "what",
        "איך": "how",
        "מתי": "when",
        "איפה": "where",
        "למה": "why"
    }
    
    # Check for specific common queries
    common_queries = {
        "תערוך טבלת השוואה בין סוגי הדיסקים": "disk types comparison table",
        "מה זה UltraDisk": "what is UltraDisk",
        "תכונות UltraDisk": "UltraDisk features",
        "סוגי דיסקים באזור": "Azure disk types",
        "השוואה בין דיסקים": "disk comparison"
    }
    
    # First check for exact matches
    query_clean = query.strip()
    if query_clean in common_queries:
        return common_queries[query_clean]
    
    # If no exact match, try word-by-word translation
    english_query = query
    for hebrew, english in translations.items():
        english_query = english_query.replace(hebrew, english)
    
    # If the query still contains Hebrew characters, add English keywords
    if any('\u0590' <= char <= '\u05FF' for char in english_query):
        # Query still has Hebrew, add relevant English terms
        english_keywords = []
        
        if "דיסק" in query or "אחסון" in query:
            english_keywords.extend(["disk", "storage", "Azure"])
            
        if "UltraDisk" in query or "אולטרה" in query:
            english_keywords.append("UltraDisk")
            
        if "השוואה" in query or "טבלה" in query:
            english_keywords.extend(["comparison", "features"])
            
        if english_keywords:
            english_query = " ".join(english_keywords)
    
    return english_query.strip()

def should_translate_query(query: str) -> bool:
    """
    Check if a query contains Hebrew characters and should be translated
    """
    return any('\u0590' <= char <= '\u05FF' for char in query)

def get_enhanced_query(original_query: str) -> str:
    """
    Get an enhanced version of the query that's more likely to return results
    """
    if should_translate_query(original_query):
        translated = translate_hebrew_to_english(original_query)
        return translated
    else:
        # For English queries, just return as-is
        return original_query
