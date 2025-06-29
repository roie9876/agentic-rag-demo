#!/usr/bin/env python3
"""
Check if the SharePoint scheduler is actually stopped
"""

import os
import pickle
import threading
from datetime import datetime

def check_scheduler_status():
    print("SharePoint Scheduler Status Check")
    print("=" * 40)
    
    # Check state file
    state_file = "scheduler_state.pkl"
    if os.path.exists(state_file):
        try:
            with open(state_file, 'rb') as f:
                state = pickle.load(f)
            
            print(f"📊 State File Status:")
            print(f"   - Is Running: {state.get('is_running', 'Unknown')}")
            print(f"   - Status: {state.get('current_status', 'Unknown')}")
            print(f"   - Folders: {state.get('selected_folders', [])}")
            print(f"   - Interval: {state.get('interval_minutes', 'Unknown')} minutes")
            print(f"   - Next Run: {state.get('next_run', 'None')}")
            
        except Exception as e:
            print(f"❌ Error reading state file: {e}")
    else:
        print("📂 No state file found")
    
    # Check for any running threads with 'sharepoint' or 'scheduler' in name
    print(f"\n🧵 Active Threads Check:")
    all_threads = threading.enumerate()
    scheduler_threads = []
    
    for thread in all_threads:
        thread_name = thread.name.lower()
        if 'sharepoint' in thread_name or 'scheduler' in thread_name:
            scheduler_threads.append(thread)
            print(f"   - Found: {thread.name} (alive: {thread.is_alive()})")
    
    if not scheduler_threads:
        print("   - No scheduler-related threads found")
    
    # Check for background processes that might be processing files
    print(f"\n📋 Recent Activity Check:")
    reports_dir = "sharepoint_reports"
    if os.path.exists(reports_dir):
        reports = sorted([f for f in os.listdir(reports_dir) if f.endswith('.json')])
        if reports:
            latest_report = reports[-1]
            report_time = latest_report.split('_')[1:3]  # Extract date and time
            if len(report_time) == 2:
                date_str, time_str = report_time
                print(f"   - Latest report: {date_str} at {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}")
            
            # Check if any reports are from the last 5 minutes
            current_time = datetime.now()
            recent_reports = []
            
            for report_file in reports[-10:]:  # Check last 10 reports
                try:
                    # Extract timestamp from filename: report_YYYYMMDD_HHMMSS_type.json
                    parts = report_file.replace('.json', '').split('_')
                    if len(parts) >= 3:
                        date_part = parts[1]  # YYYYMMDD
                        time_part = parts[2]  # HHMMSS
                        
                        # Parse the timestamp
                        year = int(date_part[:4])
                        month = int(date_part[4:6])
                        day = int(date_part[6:8])
                        hour = int(time_part[:2])
                        minute = int(time_part[2:4])
                        second = int(time_part[4:6])
                        
                        report_time = datetime(year, month, day, hour, minute, second)
                        time_diff = (current_time - report_time).total_seconds()
                        
                        if time_diff < 300:  # Last 5 minutes
                            recent_reports.append((report_file, time_diff))
                            
                except Exception:
                    continue
            
            if recent_reports:
                print(f"   - ⚠️ Recent activity detected ({len(recent_reports)} reports in last 5 minutes):")
                for report_file, seconds_ago in recent_reports:
                    print(f"     • {report_file} ({int(seconds_ago)}s ago)")
            else:
                print(f"   - ✅ No recent activity (no reports in last 5 minutes)")
        else:
            print("   - No reports found")
    else:
        print("   - No reports directory found")
    
    # Summary
    print(f"\n🎯 Summary:")
    if os.path.exists(state_file):
        try:
            with open(state_file, 'rb') as f:
                state = pickle.load(f)
            is_running = state.get('is_running', False)
            if is_running:
                print("   ❌ Scheduler shows as RUNNING in state file")
            else:
                print("   ✅ Scheduler shows as STOPPED in state file")
                
            if scheduler_threads:
                print("   ⚠️ Background threads still detected")
            else:
                print("   ✅ No background threads detected")
                
        except Exception:
            print("   ❓ Cannot determine scheduler state")
    else:
        print("   ✅ No state file = scheduler not running")

if __name__ == "__main__":
    check_scheduler_status()
