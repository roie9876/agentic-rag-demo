#!/usr/bin/env python3
"""
Quick script to list all available indexes and their vectorizer status.
"""
import os
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient

def load_env():
    from dotenv import load_dotenv
    load_dotenv()

def list_indexes():
    print("📋 Available Azure Search Indexes")
    print("=" * 50)
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        indexes = list(index_client.list_indexes())
        
        for index in indexes:
            print(f"\n📊 Index: {index.name}")
            
            # Check if it has vectorizers
            vectorizer_count = 0
            if hasattr(index, 'vector_search') and index.vector_search:
                if hasattr(index.vector_search, 'vectorizers') and index.vector_search.vectorizers:
                    vectorizer_count = len(index.vector_search.vectorizers)
            
            # Check vector fields
            vector_fields = []
            for field in index.fields:
                if hasattr(field, 'vector_search_dimensions'):
                    vector_fields.append(f"{field.name} ({field.vector_search_dimensions}d)")
            
            if vectorizer_count > 0:
                print(f"   ✅ Vectorizers: {vectorizer_count}")
            else:
                print(f"   ❌ Vectorizers: 0")
            
            if vector_fields:
                print(f"   ✅ Vector fields: {', '.join(vector_fields)}")
            else:
                print(f"   ❌ Vector fields: None")
            
            # Get document count
            try:
                from azure.search.documents import SearchClient
                search_client = SearchClient(endpoint=search_endpoint, index_name=index.name, credential=credential)
                results = search_client.search(search_text="*", top=1, include_total_count=True)
                doc_count = results.get_count()
                print(f"   📄 Documents: {doc_count}")
            except:
                print(f"   📄 Documents: Unable to count")
                
        print(f"\n📈 Total indexes: {len(indexes)}")
        
    except Exception as e:
        print(f"❌ Error listing indexes: {str(e)}")

if __name__ == "__main__":
    list_indexes()
