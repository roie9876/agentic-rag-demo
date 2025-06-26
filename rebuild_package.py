#!/usr/bin/env python3
"""
Rebuild M365 package with corrected manifest format
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from m365_agent_tab import M365AgentManager

def rebuild_package():
    """Rebuild the M365 package with the corrected manifest"""
    print("🔧 Rebuilding M365 package with corrected manifest...")
    
    manager = M365AgentManager()
    
    # Use a test function URL for now
    test_func_url = "https://your-function-app.azurewebsites.net/api/AgentFunction"
    
    # Build the package
    success, message, zip_path = manager.build_package(test_func_url)
    
    if success:
        print(f"✅ {message}")
        print("📦 Package contents updated with compatible manifest format")
        print("🚀 Ready to test with PowerShell deployment!")
    else:
        print(f"❌ {message}")

if __name__ == "__main__":
    rebuild_package()
