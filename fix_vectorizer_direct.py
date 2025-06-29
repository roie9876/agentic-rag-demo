#!/usr/bin/env python3
"""
Direct approach to manually configure the vectorizer for the delete3 index.
This script will forcefully add the vectorizer configuration.
"""
import os
import json
import requests
from azure.identity import DefaultAzureCredential

def load_env():
    """Load environment variables from .env file."""
    from dotenv import load_dotenv
    load_dotenv()

def configure_vectorizer_direct():
    """Directly configure the vectorizer using REST API."""
    print("🔧 Configuring vectorizer directly via REST API...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    embedding_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    
    try:
        credential = DefaultAzureCredential()
        token_response = credential.get_token("https://search.azure.com/.default")
        access_token = token_response.token
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Get current index definition
        get_url = f"{search_endpoint}/indexes/delete3?api-version=2024-07-01"
        response = requests.get(get_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to get index: {response.status_code}")
            print(response.text)
            return False
        
        index_def = response.json()
        print("✅ Retrieved current index definition")
        
        # Add vectorizer configuration
        if "vectorizers" not in index_def:
            index_def["vectorizers"] = []
        
        # Remove any existing vectorizer with the same name
        index_def["vectorizers"] = [v for v in index_def["vectorizers"] if v["name"] != "azure_openai_text_3_large"]
        
        # Add new vectorizer
        vectorizer = {
            "name": "azure_openai_text_3_large",
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": embedding_endpoint,
                "deploymentId": embedding_deployment,
                "modelName": "text-embedding-3-large"
            }
        }
        
        index_def["vectorizers"].append(vectorizer)
        print("✅ Added vectorizer configuration")
        
        # Update vector profile to use the new vectorizer
        if "vectorSearch" in index_def and "profiles" in index_def["vectorSearch"]:
            for profile in index_def["vectorSearch"]["profiles"]:
                if profile["name"] == "hnsw_text_3_large":
                    profile["vectorizer"] = "azure_openai_text_3_large"
                    print(f"✅ Updated vector profile '{profile['name']}'")
        
        # Add vector field if it doesn't exist
        has_vector_field = any(field["name"] == "contentVector" for field in index_def["fields"])
        if not has_vector_field:
            vector_field = {
                "name": "contentVector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "dimensions": 3072,
                "vectorSearchProfile": "hnsw_text_3_large"
            }
            index_def["fields"].append(vector_field)
            print("✅ Added contentVector field")
        
        # Update the index
        put_url = f"{search_endpoint}/indexes/delete3?api-version=2024-07-01"
        response = requests.put(put_url, headers=headers, json=index_def)
        
        if response.status_code in [200, 201]:
            print("✅ Successfully updated index with vectorizer")
            return True
        else:
            print(f"❌ Failed to update index: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error configuring vectorizer: {str(e)}")
        return False

def check_vectorizer_status():
    """Check if the vectorizer is now configured."""
    print("\n🔍 Checking vectorizer status...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        token_response = credential.get_token("https://search.azure.com/.default")
        access_token = token_response.token
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        get_url = f"{search_endpoint}/indexes/delete3?api-version=2024-07-01"
        response = requests.get(get_url, headers=headers)
        
        if response.status_code == 200:
            index_def = response.json()
            
            # Check vectorizers
            vectorizers = index_def.get("vectorizers", [])
            if vectorizers:
                print(f"✅ Found {len(vectorizers)} vectorizer(s):")
                for v in vectorizers:
                    print(f"   - {v['name']} ({v['kind']})")
            else:
                print("❌ No vectorizers found")
            
            # Check vector fields
            vector_fields = [f for f in index_def["fields"] if f.get("dimensions")]
            if vector_fields:
                print(f"✅ Found {len(vector_fields)} vector field(s):")
                for f in vector_fields:
                    print(f"   - {f['name']} ({f.get('dimensions')} dimensions)")
            else:
                print("❌ No vector fields found")
            
            return len(vectorizers) > 0 and len(vector_fields) > 0
        else:
            print(f"❌ Failed to check status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking status: {str(e)}")
        return False

def trigger_reindexing():
    """Try to trigger reindexing to generate vectors."""
    print("\n🔄 Attempting to trigger reindexing...")
    
    load_env()
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    
    try:
        credential = DefaultAzureCredential()
        token_response = credential.get_token("https://search.azure.com/.default")
        access_token = token_response.token
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # List indexers
        indexers_url = f"{search_endpoint}/indexers?api-version=2024-07-01"
        response = requests.get(indexers_url, headers=headers)
        
        if response.status_code == 200:
            indexers = response.json()["value"]
            print(f"✅ Found {len(indexers)} indexer(s)")
            
            # Look for indexers targeting delete3
            target_indexers = [idx for idx in indexers if idx.get("targetIndexName") == "delete3"]
            
            if target_indexers:
                for indexer in target_indexers:
                    run_url = f"{search_endpoint}/indexers/{indexer['name']}/run?api-version=2024-07-01"
                    run_response = requests.post(run_url, headers=headers)
                    
                    if run_response.status_code in [202, 204]:
                        print(f"✅ Started indexer: {indexer['name']}")
                    else:
                        print(f"⚠️  Failed to start indexer {indexer['name']}: {run_response.status_code}")
            else:
                print("⚠️  No indexers found for delete3 index")
                print("ℹ️  You may need to manually re-upload documents in Azure Portal")
        else:
            print(f"❌ Failed to list indexers: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error triggering reindexing: {str(e)}")

def main():
    """Main function to fix vectorizer configuration."""
    print("🔧 Direct Vectorizer Configuration Fix")
    print("=" * 50)
    
    # Step 1: Configure vectorizer
    success = configure_vectorizer_direct()
    
    if success:
        # Step 2: Check status
        status_ok = check_vectorizer_status()
        
        if status_ok:
            # Step 3: Trigger reindexing
            trigger_reindexing()
            
            print("\n" + "=" * 50)
            print("✅ VECTORIZER CONFIGURATION COMPLETED!")
            print("=" * 50)
            print("🎯 Next Steps:")
            print("1. ⏱️  Wait 5-10 minutes for reindexing to complete")
            print("2. 🔄 Test agentic retrieval again")
            print("3. 📊 Check Azure Portal → Search → delete3 → Vectorizers")
            print("4. 🧪 Run python diagnose_agentic_retrieval.py to verify")
        else:
            print("\n❌ Vectorizer configuration verification failed")
    else:
        print("\n❌ Failed to configure vectorizer")

if __name__ == "__main__":
    main()
