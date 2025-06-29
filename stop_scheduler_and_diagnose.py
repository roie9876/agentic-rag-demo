#!/usr/bin/env python3
"""
Stop the SharePoint scheduler and diagnose the repeated processing issue
"""

import os
import sys
import pickle
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("SharePoint Scheduler Diagnostic Tool")
    print("=" * 50)
    
    # Check if scheduler state file exists
    state_file = "scheduler_state.pkl"
    if os.path.exists(state_file):
        try:
            with open(state_file, 'rb') as f:
                state = pickle.load(f)
            
            print(f"📊 Scheduler State Found:")
            print(f"   - Running: {state.get('is_running', 'Unknown')}")
            print(f"   - Selected Folders: {state.get('selected_folders', 'Unknown')}")
            print(f"   - Interval: {state.get('interval_minutes', 'Unknown')} minutes")
            print(f"   - Next Run: {state.get('next_run', 'Unknown')}")
            print(f"   - Status: {state.get('current_status', 'Unknown')}")
            
            # Show tracked files
            tracked_files = state.get('tracked_files', {})
            if tracked_files:
                print(f"\n📁 Tracked Files ({len(tracked_files)}):")
                for file_key, file_info in tracked_files.items():
                    print(f"   - {file_info.get('file_name', 'Unknown')}")
                    print(f"     Last Modified: {file_info.get('last_modified', 'Unknown')}")
                    print(f"     Last Indexed: {file_info.get('last_indexed', 'Never')}")
                    print(f"     ETag: {file_info.get('etag', 'None')}")
                    print()
            
            # Offer to stop the scheduler
            if state.get('is_running', False):
                response = input("\n❓ Scheduler is running. Stop it? (y/N): ").strip().lower()
                if response == 'y':
                    state['is_running'] = False
                    state['current_status'] = 'Manually stopped'
                    
                    with open(state_file, 'wb') as f:
                        pickle.dump(state, f)
                    
                    print("✅ Scheduler stopped successfully!")
                    print("   You can now safely restart it from the UI with new settings.")
                else:
                    print("⏭️  Scheduler left running.")
            else:
                print("✅ Scheduler is not running.")
                
        except Exception as e:
            print(f"❌ Error reading scheduler state: {e}")
    else:
        print("📂 No scheduler state file found - scheduler is not running.")
    
    # Check recent reports
    print(f"\n📋 Recent Processing Activity:")
    reports_dir = "sharepoint_reports"
    if os.path.exists(reports_dir):
        reports = sorted([f for f in os.listdir(reports_dir) if f.endswith('.json')])
        recent_reports = reports[-5:] if len(reports) > 5 else reports
        
        for report_file in recent_reports:
            report_path = os.path.join(reports_dir, report_file)
            try:
                import json
                with open(report_path) as f:
                    report_data = json.load(f)
                
                start_time = report_data.get('start_time', '').split('T')[1][:8] if 'T' in report_data.get('start_time', '') else 'Unknown'
                files_processed = report_data.get('files_processed', 0)
                print(f"   - {start_time}: {files_processed} files processed")
                
            except Exception as e:
                print(f"   - {report_file}: Error reading ({e})")
    
    print(f"\n💡 Next Steps:")
    print("   1. If scheduler was stopped, restart it from the SharePoint tab in the UI")
    print("   2. Check that your SharePoint folder '/ppt' contains only the files you want to index")
    print("   3. Consider clearing the file tracking state if files keep getting reprocessed")

if __name__ == "__main__":
    main()
