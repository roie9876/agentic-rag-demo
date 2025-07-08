#!/usr/bin/env python3
"""
Check index configuration and Azure Search setup
"""
import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

def main():
    # Load environment variables
    load_dotenv()
    
    print("=== Index Configuration Check ===")
    
    # Check environment variables
    index_name = os.getenv('INDEX_NAME')
    sharepoint_index_name = os.getenv('AZURE_SEARCH_SHAREPOINT_INDEX_NAME')
    search_endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
    search_key = os.getenv('AZURE_SEARCH_KEY')
    
    print(f"INDEX_NAME: {index_name}")
    print(f"AZURE_SEARCH_SHAREPOINT_INDEX_NAME: {sharepoint_index_name}")
    print(f"AZURE_SEARCH_ENDPOINT: {search_endpoint}")
    print(f"AZURE_SEARCH_KEY: {'[SET]' if search_key else '[NOT SET - using RBAC]'}")
    
    if not search_endpoint:
        print("❌ AZURE_SEARCH_ENDPOINT not set!")
        return
    
    if not index_name:
        print("❌ INDEX_NAME not set!")
        return
    
    # Test connection to Azure Search
    try:
        print(f"\n=== Testing connection to index: {index_name} ===")
        
        # Use RBAC authentication
        credential = DefaultAzureCredential()
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential
        )
        
        # Get document count
        results = search_client.search("*", include_total_count=True)
        doc_count = results.get_count()
        print(f"✅ Successfully connected to index '{index_name}'")
        print(f"📊 Document count: {doc_count}")
        
    except Exception as e:
        print(f"❌ Error connecting to index '{index_name}': {e}")
    
    # Test SharePoint index if different
    if sharepoint_index_name and sharepoint_index_name != index_name:
        try:
            print(f"\n=== Testing connection to SharePoint index: {sharepoint_index_name} ===")
            
            search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=sharepoint_index_name,
                credential=credential
            )
            
            # Get document count
            results = search_client.search("*", include_total_count=True)
            doc_count = results.get_count()
            print(f"✅ Successfully connected to SharePoint index '{sharepoint_index_name}'")
            print(f"📊 Document count: {doc_count}")
            
        except Exception as e:
            print(f"❌ Error connecting to SharePoint index '{sharepoint_index_name}': {e}")

if __name__ == "__main__":
    main()
