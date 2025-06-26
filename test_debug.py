#!/usr/bin/env python3
"""
Test the debug functionality of M365 deployment
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import the debug function
from m365_agent_tab import debug_print, DEBUG_M365_DEPLOYMENT

def test_debug():
    """Test the debug functionality"""
    print(f"Debug flag is set to: {DEBUG_M365_DEPLOYMENT}")
    print("Testing debug_print function:")
    debug_print("🔍 This is a test debug message")
    debug_print("🚀 This should appear in terminal if DEBUG_M365_DEPLOYMENT is True")
    print("Debug test completed.")

if __name__ == "__main__":
    test_debug()
