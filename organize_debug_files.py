#!/usr/bin/env python3
"""
Organize debug files according to the categorization plan.
This script moves debug, diagnostic, test, and other scripts to appropriate folders.
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
        dst = os.path.join(dst_dir, os.path.basename(src))
        try:
            shutil.move(src, dst)
            print(f"✓ Moved {src} to {dst_dir}/ ({category_name})")
            return True
        except Exception as e:
            print(f"✗ Error moving {src}: {e}")
            return False
    else:
        print(f"? File not found: {src}")
        return False

def main():
    """Main function to organize files."""
    root_dir = "/home/azureuser/agentic-rag-demo"
    os.chdir(root_dir)
    
    print("🗂️  Starting file organization...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # File categories and their target directories
    files_to_move = {
        # Debug files to tests/debug/
        "tests/debug": {
            "Debug Scripts": [
                "debug_knowledge_agent_final.py",
                "debug_pe_suggestions.py", 
                "debug_private_endpoint_detection.py",
                "debug_private_endpoints.py",
                "debug_private_index.py",
                "debug_resource_group_deletion.py",
                "debug_resource_group_issue.py",
                "debug_specific_account.py",
                "debug_subnet_discovery.py",
                "debug_ui_discovery.py",
                "debug_ui_integration.py",
                "debug_comprehensive.py",
                "debug_delete3_direct_api.py",
                "debug_delete3_focused.py",
                "debug_hebrew_issue.py",
                "debug_hebrew_query.py",
            ],
            "Check Scripts": [
                "check_agent_config.py",
                "check_function_settings.py", 
                "check_function_status.py",
                "check_index_config.py",
                "check_index_contents.py",
                "check_project_rbac.py",
                "check_scheduler_status.py",
                "check_rbac_status.sh",
            ],
            "Cleanup Scripts": [
                "cleanup_debug_deployments.py",
                "cleanup_debug_resources.py", 
                "cleanup_subnets.py",
                "comprehensive_cleanup.py",
            ],
            "Creation Scripts": [
                "create_missing_agents.py",
                "create_private_index.py",
                "create_working_private_index.py",
            ],
            "Configuration Scripts": [
                "configure_function_app.py",
                "configure_function_openai.py",
            ],
            "Demo Scripts": [
                "demo_sharepoint_changes.py",
            ],
            "Force/Fix Scripts": [
                "force_delete_stuck_resource_group.py",
                "force_stop_scheduler.py",
                "fix_sal_deadlock.py",
                "fix_search_rbac.py",
                "fix_search_rbac.sh",
                "fix_vectorizer.py",
                "fix_vectorizer_config.py",
                "fix_vectorizer_direct.py", 
                "fix_vectorizer_sdk.py",
            ],
            "Standalone Scripts": [
                "standalone_delete_deployment.py",
                "stop_scheduler_and_diagnose.py",
                "find_azure_content.py",
                "investigate_index.py",
                "list_indexes.py",
                "list_search_indices.py",
                "monitor_deletion.py",
                "quick_agent_check.py",
                "reset_scheduler_state.py",
                "run_debug_deployment.py",
                "run_sharepoint_with_report.py",
                "setup_function_openai_config.py",
                "setup_rbac_permissions.sh",
                "update_agent_auth.py",
                "validate_subnet_dropdown_fix.py",
            ],
        },
        
        # Diagnostic files to tests/diagnostics/
        "tests/diagnostics": {
            "Diagnostic Scripts": [
                "diagnose_agentic_retrieval.py",
                "diagnose_function_app.py",
                "diagnose_private_endpoints.py", 
                "diagnose_search.py",
            ],
        },
        
        # Test files to tests/unit/
        "tests/unit": {
            "Unit Test Scripts": [
                "test_basic_search.py",
                "test_correct_agent.py",
                "test_embedding_connection.py",
                "test_list_indexes.py",
                "test_original_bicep.py",
                "test_project_creation.py",
                "test_response_formatter.py",
                "test_retrieval_enhancement.py",
                "test_streamlit_integration.py",
                "test_tabs_only.py",
                "test_ui_integration.py",
                "test_existing_vnet_new_subnets.py",
                "test_account_discovery.py",
                "test_agent_queries.py",
                "test_agentic_final.py",
                "test_agentic_simple.py",
                "test_ai_foundry_deployment_scenarios.py",
                "test_ai_foundry_fixes.py",
                "test_ai_foundry_parameter_generation.py",
                "test_ai_foundry_tab.py",
                "test_azure_function.py",
                "test_chunking_pipeline.py",
                "test_delete_tab.py",
                "test_delete_tab_import.py",
                "test_direct_api_fix.py",
                "test_document_intelligence_direct.py",
                "test_dynamic_agent_selection.py",
                "test_embedding_auth.py",
                "test_end_to_end.py",
                "test_enhanced_ai_foundry.py",
                "test_enhanced_health_check.py",
                "test_final_fix.py",
                "test_health.py",
                "test_health_check_app.py",
                "test_health_simple.py",
                "test_health_ui_enhancements.py",
                "test_health_ui_integration.py",
                "test_index_content.py",
                "test_minimal_app.py",
                "test_msi_fix.py",
                "test_openai_skip_final_validation.py",
                "test_partial_subnet_overlap.py",
                "test_private_endpoints.py",
                "test_project_endpoint_generation.py",
                "test_rbac_enhancement.py",
                "test_rbac_fix.py",
                "test_rbac_permission_fix.py",
                "test_real_ui_pe_discovery.py",
                "test_resource_discovery.py",
                "test_search_client_fix.py",
                "test_search_queries.py",
                "test_search_rbac.py",
                "test_simple_agent.py",
                "test_simple_ui.py",
                "test_single_document_upload.py",
                "test_specific_queries.py",
                "test_streamlit_app.py",
                "test_streamlit_health_ui.py",
                "test_subnet_dropdown_logic.py",
                "test_subnet_selection_workflow.py",
                "test_subnet_ui_simple.py",
                "test_synthesis_fix.py",
                "test_ui_pe_fix.py",
                "test_ui_structure.py",
                "test_vnet_pe_discovery.py",
                "test_vnet_pe_selection.py",
            ],
        },
    }
    
    # Track statistics
    moved_count = 0
    not_found_count = 0
    error_count = 0
    
    print("\n🚀 Starting file moves...")
    
    # Process each category
    for target_dir, categories in files_to_move.items():
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
    
    # Move JSON parameter files
    print(f"\n📂 Processing JSON parameter files:")
    json_files = [
        "test-existing-vnet-new-subnets-params.json",
        "test-partial-overlap-params.json",
        "ai_foundry_debug_results.json",
    ]
    
    for filename in json_files:
        if move_file_safely(filename, "tests/debug", "JSON Config Files"):
            moved_count += 1
        elif os.path.exists(filename):
            error_count += 1 
        else:
            not_found_count += 1
    
    # Move PowerShell files
    print(f"\n📂 Processing PowerShell files:")
    ps_files = [
        "force_delete_powershell.ps1",
        "powershell_force_delete.ps1",
    ]
    
    for filename in ps_files:
        if move_file_safely(filename, "tests/debug", "PowerShell Scripts"):
            moved_count += 1
        elif os.path.exists(filename):
            error_count += 1
        else:
            not_found_count += 1
    
    # Final summary
    print(f"\n📊 Summary:")
    print(f"✅ Files moved: {moved_count}")
    print(f"❓ Files not found: {not_found_count}")
    print(f"❌ Errors: {error_count}")
    
    if moved_count > 0:
        print(f"\n🎉 Successfully organized {moved_count} files!")
        print("\n📁 New directory structure:")
        for target_dir in files_to_move.keys():
            if os.path.exists(target_dir):
                file_count = len([f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))])
                print(f"  {target_dir}: {file_count} files")
    
    print("\n✨ File organization complete!")

if __name__ == "__main__":
    main()
