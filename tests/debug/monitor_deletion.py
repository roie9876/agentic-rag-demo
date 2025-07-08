#!/usr/bin/env python3
"""
Resource Group Deletion Monitor
Monitors the stuck resource group and checks for completion periodically.
"""

import subprocess
import json
import time
import sys
from datetime import datetime, timedelta


def check_resource_group_status(rg_name):
    """Check if resource group still exists and its status."""
    try:
        result = subprocess.run(
            ["az", "group", "show", "--name", rg_name, "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            rg_info = json.loads(result.stdout)
            state = rg_info.get('properties', {}).get('provisioningState', 'Unknown')
            return True, state
        else:
            return False, "NotFound"
            
    except Exception as e:
        print(f"Error checking status: {e}")
        return None, "Error"


def monitor_deletion(rg_name, check_interval_minutes=30, max_hours=48):
    """Monitor resource group deletion over time."""
    print(f"🔍 MONITORING RESOURCE GROUP DELETION")
    print(f"Resource Group: {rg_name}")
    print(f"Check Interval: {check_interval_minutes} minutes")
    print(f"Max Duration: {max_hours} hours")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=max_hours)
    check_count = 0
    
    while datetime.now() < end_time:
        check_count += 1
        current_time = datetime.now()
        elapsed = current_time - start_time
        
        print(f"\n📊 Check #{check_count} - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ Elapsed: {elapsed}")
        
        exists, state = check_resource_group_status(rg_name)
        
        if exists is None:
            print(f"❌ Error checking status")
        elif not exists:
            print(f"🎉 SUCCESS: Resource group '{rg_name}' has been deleted!")
            print(f"🕐 Total time: {elapsed}")
            return True
        else:
            print(f"⏳ Status: {state}")
            
            if state == "Deleting":
                print(f"🔄 Deletion in progress...")
            elif state == "Succeeded":
                print(f"⚠️ Deletion was cancelled/reverted - still exists")
            else:
                print(f"❓ Unknown state: {state}")
        
        # Wait for next check
        print(f"⏰ Next check in {check_interval_minutes} minutes...")
        time.sleep(check_interval_minutes * 60)
    
    print(f"\n⏰ Monitoring period ended after {max_hours} hours")
    print(f"❌ Resource group '{rg_name}' still exists")
    return False


def main():
    """Main monitoring function."""
    rg_name = "bciep-test-8"
    
    print("⏰ AZURE RESOURCE GROUP DELETION MONITOR")
    print("=" * 60)
    
    try:
        # Check initial status
        exists, state = check_resource_group_status(rg_name)
        
        if not exists:
            print(f"✅ Resource group '{rg_name}' is already deleted!")
            return 0
        
        print(f"📋 Initial status: {state}")
        
        if state != "Deleting":
            print(f"⚠️ Resource group is not in 'Deleting' state")
            print(f"ℹ️ You may need to initiate deletion first")
            
            choice = input("Start deletion monitoring anyway? (y/n): ").strip().lower()
            if choice != 'y':
                print("❌ Monitoring cancelled")
                return 1
        
        # Start monitoring
        success = monitor_deletion(rg_name)
        
        if success:
            print(f"\n🎉 DELETION COMPLETED SUCCESSFULLY!")
            return 0
        else:
            print(f"\n💔 DELETION STILL PENDING - CONSIDER OPENING SUPPORT TICKET")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n❌ Monitoring interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
