#!/usr/bin/env python3
"""
List all available search indices.
"""

import asyncio
import logging
import sys
import os

# Add the project root to Python path
sys.path.append('/Users/robenhai/agentic-rag-demo')

from tools import AISearchClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def list_indices():
    """List all available search indices."""
    
    print("=== Listing Available Search Indices ===")
    
    client = AISearchClient()
    try:
        indices = await client.list_indices()
        
        print(f"\nFound {len(indices)} indices:")
        for i, idx_name in enumerate(indices, 1):
            print(f"  {i}. {idx_name}")
            
        if not indices:
            print("  No indices found!")
            
        return indices
        
    except Exception as e:
        print(f"Error listing indices: {e}")
        logging.error(f"Error listing indices: {e}")
        return []
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(list_indices())
