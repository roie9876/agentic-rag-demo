#!/usr/bin/env python3
"""Test script to list all available search indexes"""

import os
from azure.search.documents.indexes import SearchIndexClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

def list_search_indexes():
    """List all available search indexes"""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    print(f"Listing indexes from: {endpoint}")
    print("-" * 50)
    
    try:
        client = SearchIndexClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential()
        )
        
        indexes = client.list_indexes()
        index_list = list(indexes)
        
        print(f"Found {len(index_list)} indexes:")
        for i, index in enumerate(index_list, 1):
            print(f"  {i}. {index.name}")
            
        return [index.name for index in index_list]
        
    except Exception as e:
        print(f"❌ Error listing indexes: {e}")
        return []

if __name__ == "__main__":
    available_indexes = list_search_indexes()
    print(f"\nAvailable indexes: {available_indexes}")
