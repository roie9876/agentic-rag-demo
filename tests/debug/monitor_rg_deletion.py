#!/usr/bin/env python3
"""
Monitor stuck resource group deletion status
Created: 2025-07-08
Location: tests/debug/ (following new organization policy)
"""

import subprocess
import time
import sys
from datetime import datetime

def check_rg_status(rg_name):
    """Check if resource group still exists"""
    try:
        result = subprocess.run(
            ["az", "group", "show", "--name", rg_name],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except:
        return False

def monitor_deletion(rg_name, check_interval=300):  # 5 minutes
    """Monitor resource group deletion status"""
    print(f"🔍 Monitoring resource group: {rg_name}")
    print(f"⏰ Check interval: {check_interval} seconds")
    print("=" * 60)
    
    check_count = 0
    while True:
        check_count += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if check_rg_status(rg_name):
            print(f"[{timestamp}] Check #{check_count}: Resource group still exists")
        else:
            print(f"[{timestamp}] Check #{check_count}: ✅ Resource group deleted!")
            return True
        
        print(f"⏳ Waiting {check_interval} seconds...")
        time.sleep(check_interval)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        rg_name = sys.argv[1]
    else:
        rg_name = "bciep-test-8"
    
    print(f"🔄 RESOURCE GROUP DELETION MONITOR")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target: {rg_name}")
    print("=" * 60)
    
    try:
        monitor_deletion(rg_name)
    except KeyboardInterrupt:
        print(f"\n❌ Monitoring stopped by user")
    except Exception as e:
        print(f"\n💥 Error: {e}")
