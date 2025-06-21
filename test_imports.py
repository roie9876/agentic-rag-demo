#!/usr/bin/env python3
"""
Test if the main agentic-rag-demo.py can import all required classes
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test if all the imports from agentic-rag-demo.py work"""
    
    print("🔍 TESTING IMPORTS FROM MAIN CODE")
    print("=" * 60)
    
    try:
        print("Testing basic Azure Search imports...")
        
        from azure.search.documents.indexes.models import (
            SearchIndex,
            SimpleField,
            SearchFieldDataType,
            SearchableField,
            SearchField,
            VectorSearch,
            HnswAlgorithmConfiguration,
            VectorSearchProfile,
            SemanticConfiguration,
            SemanticField,
            SemanticPrioritizedFields,
            SemanticSearch,
            AzureOpenAIVectorizer,
            AzureOpenAIVectorizerParameters,
        )
        print("✅ Basic search index classes imported successfully")
        
        print("\nTesting agent-related imports...")
        
        try:
            from azure.search.documents.indexes.models import (
                KnowledgeAgent,
                KnowledgeAgentAzureOpenAIModel,
                KnowledgeAgentTargetIndex
            )
            print("✅ Agent classes imported successfully")
            agent_imports_ok = True
            
        except ImportError as e:
            print(f"❌ Agent classes import failed: {str(e)}")
            agent_imports_ok = False
            
        print("\nTesting agent client imports...")
        
        try:
            from azure.search.documents.agent import KnowledgeAgentRetrievalClient
            print("✅ Agent client imported successfully")
            agent_client_ok = True
            
        except ImportError as e:
            print(f"❌ Agent client import failed: {str(e)}")
            agent_client_ok = False
            
        print("\nTesting agent models imports...")
        
        try:
            from azure.search.documents.agent.models import (
                KnowledgeAgentRetrievalRequest,
                KnowledgeAgentMessage,
                KnowledgeAgentMessageTextContent,
                KnowledgeAgentIndexParams,
            )
            print("✅ Agent models imported successfully")
            agent_models_ok = True
            
        except ImportError as e:
            print(f"❌ Agent models import failed: {str(e)}")
            agent_models_ok = False
            
        return agent_imports_ok, agent_client_ok, agent_models_ok
        
    except Exception as e:
        print(f"❌ Error during import testing: {str(e)}")
        return False, False, False

def analyze_situation():
    """Analyze what's working and what's not"""
    
    agent_imports_ok, agent_client_ok, agent_models_ok = test_imports()
    
    print("\n" + "=" * 60)
    print("🎯 IMPORT ANALYSIS:")
    
    print(f"\n📋 Results:")
    print(f"   Agent creation classes: {'✅' if agent_imports_ok else '❌'}")
    print(f"   Agent retrieval client: {'✅' if agent_client_ok else '❌'}")
    print(f"   Agent models/requests:  {'✅' if agent_models_ok else '❌'}")
    
    if not agent_imports_ok:
        print(f"\n❌ CRITICAL ISSUE: Agent creation classes not available")
        print(f"   This means agents are NEVER created when you create indexes")
        print(f"   Even though the main code tries to create them, it fails silently")
        
    if agent_client_ok and agent_models_ok:
        print(f"\n✅ Agent retrieval infrastructure is available")
        print(f"   This means the code can TRY to use agents for queries")
        print(f"   But if no agents exist, queries will return empty results")
        
    print(f"\n💡 ROOT CAUSE IDENTIFIED:")
    if not agent_imports_ok and agent_client_ok:
        print(f"   1. ❌ Agents cannot be created (missing KnowledgeAgent classes)")
        print(f"   2. ✅ But agent queries are attempted (KnowledgeAgentRetrievalClient exists)")
        print(f"   3. 🎯 Result: Queries try to use non-existent agents → empty results")
        
    print(f"\n🛠️ SOLUTIONS:")
    print(f"   1. Upgrade Azure Search SDK to version with agent creation support")
    print(f"   2. Create agents manually using Azure Portal/REST API") 
    print(f"   3. Use direct search instead of agent-based retrieval as fallback")

if __name__ == "__main__":
    analyze_situation()
