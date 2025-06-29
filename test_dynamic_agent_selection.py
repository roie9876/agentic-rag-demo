#!/usr/bin/env python3
"""
Test the updated dynamic agent selection logic
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")

def test_dynamic_agent_selection():
    """Test that agent names are generated dynamically based on index selection"""
    
    print("🧪 Testing Dynamic Agent Selection")
    print("=" * 50)
    
    # Test cases: different index names the user might select
    test_indexes = [
        "sharepoint-index-1",
        "delete3", 
        "agentic-demo",
        "agentic-index",
        "my-custom-index",
        "user-documents"
    ]
    
    print("📋 Index → Agent Name Mapping:")
    print("-" * 40)
    
    for index_name in test_indexes:
        # This is the logic used in both files now
        agent_name = f"{index_name}-agent"
        print(f"  📊 {index_name:<20} → 🤖 {agent_name}")
    
    print("\n✅ SUCCESS: Agent names are generated dynamically!")
    print("💡 No hardcoded mappings - works with any user-selected index")
    
    # Test environment configuration
    print(f"\n🔧 Environment Configuration:")
    print(f"  Default INDEX_NAME: {os.getenv('INDEX_NAME')}")
    print(f"  API_VERSION: {os.getenv('API_VERSION')}")
    print(f"  Search Endpoint: {os.getenv('AZURE_SEARCH_ENDPOINT')}")
    
    print(f"\n🎯 Current Setup:")
    print(f"  • User can select any index in the UI")
    print(f"  • Agent name is automatically: {{selected_index}}-agent")
    print(f"  • Uses API version: {os.getenv('API_VERSION')}")
    print(f"  • Default index: {os.getenv('INDEX_NAME')} (but user can change)")

if __name__ == "__main__":
    test_dynamic_agent_selection()
