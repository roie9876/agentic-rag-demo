#!/usr/bin/env python3
"""
Force stop the SharePoint scheduler
"""

import os
import pickle
from datetime import datetime

def stop_scheduler():
    state_file = "scheduler_state.pkl"
    
    if os.path.exists(state_file):
        try:
            # Load current state
            with open(state_file, 'rb') as f:
                state = pickle.load(f)
            
            print(f"Current scheduler status: {state.get('current_status', 'Unknown')}")
            print(f"Is running: {state.get('is_running', False)}")
            
            # Stop the scheduler
            state['is_running'] = False
            state['current_status'] = 'Manually stopped'
            
            # Save the updated state
            with open(state_file, 'wb') as f:
                pickle.dump(state, f)
            
            print("✅ Scheduler stopped successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping scheduler: {e}")
            return False
    else:
        print("📂 No scheduler state file found - scheduler is not running.")
        return False

if __name__ == "__main__":
    stop_scheduler()
