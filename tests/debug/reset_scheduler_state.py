#!/usr/bin/env python3
"""
Clear SharePoint scheduler state to prevent auto-starting with old folders
"""

import os
import pickle
from datetime import datetime

def clear_scheduler_state():
    state_file = "scheduler_state.pkl"
    
    if os.path.exists(state_file):
        try:
            print(f"🗑️  Clearing scheduler state file: {state_file}")
            
            # Create fresh state
            fresh_state = {
                'is_running': False,
                'current_status': 'Stopped',
                'interval_minutes': 15,  # Set a reasonable default (15 minutes instead of 1)
                'last_run': None,
                'next_run': None,
                'selected_folders': [],  # Clear any previously selected folders
                'config': {},
                'max_parallel_files': 3
            }
            
            # Save the fresh state
            with open(state_file, 'wb') as f:
                pickle.dump(fresh_state, f)
            
            print("✅ Scheduler state cleared successfully!")
            print("📋 New defaults:")
            print("   - Status: Stopped")
            print("   - Interval: 15 minutes (was 1 minute)")
            print("   - Selected folders: Empty (user must select)")
            print("   - Auto-resume: Disabled")
            return True
            
        except Exception as e:
            print(f"❌ Error clearing scheduler state: {e}")
            return False
    else:
        print("📂 No scheduler state file found.")
        return True

def clear_old_reports():
    """Clear old processing reports"""
    reports_dir = "sharepoint_reports"
    if os.path.exists(reports_dir):
        try:
            reports = [f for f in os.listdir(reports_dir) if f.endswith('.json')]
            if reports:
                response = input(f"\n❓ Found {len(reports)} old reports. Clear them? (y/N): ").strip().lower()
                if response == 'y':
                    for report_file in reports:
                        os.remove(os.path.join(reports_dir, report_file))
                    print(f"✅ Cleared {len(reports)} old reports.")
                else:
                    print("⏭️  Keeping old reports.")
            else:
                print("📁 No old reports found.")
        except Exception as e:
            print(f"❌ Error clearing reports: {e}")

if __name__ == "__main__":
    print("SharePoint Scheduler State Reset Tool")
    print("=" * 45)
    
    clear_scheduler_state()
    clear_old_reports()
    
    print(f"\n💡 Next Steps:")
    print("   1. Start your app: streamlit run agentic-rag-demo.py")
    print("   2. Go to SharePoint tab")
    print("   3. Select the folders you want to monitor")
    print("   4. Start the scheduler manually with your chosen settings")
