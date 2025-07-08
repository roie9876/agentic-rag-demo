#!/usr/bin/env python3
"""
Organize documentation files according to the updated copilot-instructions.md guidelines.
This script moves status/implementation MD files to appropriate docs subdirectories.
"""

import os
import shutil
import sys
from pathlib import Path

def ensure_dir_exists(path):
    """Ensure directory exists, create if it doesn't."""
    Path(path).mkdir(parents=True, exist_ok=True)

def move_file_safely(src, dst_dir, category_name):
    """Move file safely with error handling."""
    if os.path.exists(src):
        ensure_dir_exists(dst_dir)
        dst = os.path.join(dst_dir, os.path.basename(src).lower())
        try:
            shutil.move(src, dst)
            print(f"✓ Moved {src} to {dst}")
            return True
        except Exception as e:
            print(f"✗ Error moving {src}: {e}")
            return False
    else:
        print(f"? File not found: {src}")
        return False

def main():
    """Main function to organize documentation files."""
    root_dir = "/home/azureuser/agentic-rag-demo"
    os.chdir(root_dir)
    
    print("📄 Starting documentation organization...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Documentation files and their target directories
    docs_to_move = {
        "docs/status": {
            "Implementation Status Files": [
                "AI_FOUNDRY_CAPABILITY_HOST_DNS_FIXES.md",
                "AI_FOUNDRY_DEPLOYMENT_SUCCESS_SUMMARY.md", 
                "AI_FOUNDRY_IMPLEMENTATION_FINAL_SUMMARY.md",
                "AI_FOUNDRY_UI_STATUS_DNS_ZONE_FIXES.md",
                "DELETE_DEPLOYMENT_INTEGRATION_FIXED.md",
                "DELETE_DEPLOYMENT_SERVICE_LINKS_FIX.md",
                "DELETE_DEPLOYMENT_TAB_INTEGRATION_COMPLETE.md",
                "DNS_ZONE_RESOURCE_GROUP_FIX_COMPLETE.md",
                "ENHANCED_DELETE_DEPLOYMENT_LEGIONSERVICELINK_FIX.md",
            ]
        }
    }
    
    # Track statistics
    moved_count = 0
    not_found_count = 0
    error_count = 0
    
    print("\n🚀 Starting documentation moves...")
    
    # Process each category
    for target_dir, categories in docs_to_move.items():
        print(f"\n📂 Processing {target_dir}:")
        
        for category_name, files in categories.items():
            print(f"\n  📋 {category_name}:")
            
            for filename in files:
                if move_file_safely(filename, target_dir, category_name):
                    moved_count += 1
                elif os.path.exists(filename):
                    error_count += 1
                else:
                    not_found_count += 1
    
    # Final summary
    print(f"\n📊 Documentation Organization Summary:")
    print(f"✅ Files moved: {moved_count}")
    print(f"❓ Files not found: {not_found_count}")
    print(f"❌ Errors: {error_count}")
    
    if moved_count > 0:
        print(f"\n🎉 Successfully organized {moved_count} documentation files!")
        print("\n📁 New documentation structure:")
        for target_dir in docs_to_move.keys():
            if os.path.exists(target_dir):
                file_count = len([f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))])
                print(f"  {target_dir}: {file_count} files")
    
    # Show what remains in root
    print(f"\n📄 Remaining MD files in root (should be core docs only):")
    root_md_files = [f for f in os.listdir('.') if f.endswith('.md')]
    if root_md_files:
        for md_file in root_md_files:
            print(f"  • {md_file}")
    else:
        print("  (no .md files in root)")
    
    print("\n✨ Documentation organization complete!")

if __name__ == "__main__":
    main()
