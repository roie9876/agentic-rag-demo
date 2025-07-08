#!/usr/bin/env python3
"""Check which indexes have content"""

import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.identity import DefaultAzureCredential
import streamlit as st

def get_search_client(index_name=None):
    """Get search client using managed identity"""
    try:
        credential = DefaultAzureCredential()
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        
        if not endpoint:
            print("❌ AZURE_SEARCH_ENDPOINT not set")
            return None
            
        if index_name:
            return SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
        else:
            return SearchIndexClient(endpoint=endpoint, credential=credential)
    except Exception as e:
        print(f"Failed to initialize search client: {e}")
        return None

def check_index_contents():
    """Check document counts in all indexes"""
    print("🔍 Checking Index Contents")
    print("=" * 50)
    
    # Get index client
    index_client = get_search_client()
    if not index_client:
        print("❌ Failed to get index client")
        return
    
    try:
        indexes = index_client.list_indexes()
        index_names = [idx.name for idx in indexes]
        print(f"📋 Found {len(index_names)} indexes")
        
        for index_name in index_names:
            try:
                search_client = get_search_client(index_name)
                if search_client:
                    # Get document count
                    results = search_client.search("*", select="", top=0, include_total_count=True)
                    count = results.get_count()
                    print(f"   📊 {index_name}: {count} documents")
                    
                    # Show a sample document if available
                    if count > 0:
                        sample_results = search_client.search("*", top=1)
                        for doc in sample_results:
                            sample_fields = list(doc.keys())[:5]  # Show first 5 fields
                            print(f"      🔎 Sample fields: {sample_fields}")
                            break
                else:
                    print(f"   ❌ {index_name}: Failed to get search client")
                    
            except Exception as e:
                print(f"   ❌ {index_name}: Error - {e}")
                
    except Exception as e:
        print(f"❌ Failed to list indexes: {e}")

if __name__ == "__main__":
    check_index_contents()
