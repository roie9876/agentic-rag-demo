#!/usr/bin/env python3
"""
AI Foundry Debug Deployment Runner with Automatic Cleanup

This script runs the debug AI Foundry deployment and provides options for cleanup.
"""

import sys
import subprocess
import os
from datetime import datetime

def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n🔧 {description}")
    print(f"Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False

def main():
    print("🚀 AI Foundry Debug Deployment Runner")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    script_dir = "/home/azureuser/agentic-rag-demo"
    debug_script = os.path.join(script_dir, "debug_ai_foundry_deployment.py")
    cleanup_script = os.path.join(script_dir, "cleanup_debug_deployments.py")
    
    # Check if scripts exist
    if not os.path.exists(debug_script):
        print(f"❌ Debug script not found: {debug_script}")
        return 1
    
    if not os.path.exists(cleanup_script):
        print(f"❌ Cleanup script not found: {cleanup_script}")
        return 1
    
    print(f"\n📋 Available operations:")
    print(f"1. Run debug deployment only")
    print(f"2. Run debug deployment with automatic cleanup on failure")
    print(f"3. Clean up existing debug resources")
    print(f"4. Clean up then run fresh deployment")
    
    try:
        choice = input(f"\nSelect operation (1-4): ").strip()
    except KeyboardInterrupt:
        print(f"\n❌ Operation cancelled")
        return 1
    
    if choice == "1":
        # Run debug deployment only
        print(f"\n🚀 Running debug deployment...")
        success = run_command([
            "python3", debug_script
        ], "Debug deployment")
        
        if success:
            print(f"\n🎉 Debug deployment completed successfully!")
        else:
            print(f"\n❌ Debug deployment failed!")
            print(f"💡 You can run cleanup with: python3 {cleanup_script}")
        
        return 0 if success else 1
        
    elif choice == "2":
        # Run debug deployment with cleanup on failure
        print(f"\n🚀 Running debug deployment with automatic cleanup on failure...")
        success = run_command([
            "python3", debug_script
        ], "Debug deployment")
        
        if success:
            print(f"\n🎉 Debug deployment completed successfully!")
            print(f"💡 Resources created by this deployment will remain for analysis.")
            print(f"💡 Run cleanup manually when ready: python3 {cleanup_script}")
        else:
            print(f"\n❌ Debug deployment failed!")
            print(f"\n🧹 Running automatic cleanup...")
            cleanup_success = run_command([
                "python3", cleanup_script
            ], "Automatic cleanup after failure")
            
            if cleanup_success:
                print(f"\n✅ Environment cleaned up and ready for next attempt")
            else:
                print(f"\n⚠️  Some cleanup issues occurred")
        
        return 0 if success else 1
        
    elif choice == "3":
        # Clean up existing debug resources
        print(f"\n🧹 Running cleanup of existing debug resources...")
        success = run_command([
            "python3", cleanup_script
        ], "Debug resource cleanup")
        
        if success:
            print(f"\n✅ Cleanup completed!")
        else:
            print(f"\n⚠️  Some cleanup issues occurred")
            
        return 0 if success else 1
        
    elif choice == "4":
        # Clean up then run fresh deployment
        print(f"\n🧹 Running cleanup before fresh deployment...")
        cleanup_success = run_command([
            "python3", cleanup_script
        ], "Pre-deployment cleanup")
        
        if not cleanup_success:
            print(f"\n❌ Cleanup failed, aborting deployment")
            return 1
        
        print(f"\n🚀 Running fresh debug deployment...")
        deploy_success = run_command([
            "python3", debug_script
        ], "Fresh debug deployment")
        
        if deploy_success:
            print(f"\n🎉 Fresh deployment completed successfully!")
        else:
            print(f"\n❌ Fresh deployment failed!")
            
        return 0 if deploy_success else 1
        
    else:
        print(f"❌ Invalid choice: {choice}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
