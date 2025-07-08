#!/usr/bin/env python3
"""
Comprehensive cleanup script for debug AI Foundry deployment resources.
This script safely removes debug resources while preserving production resources.
"""

import subprocess
import json
import re
import sys
import time
from typing import List, Dict, Any, Optional

class DebugResourceCleaner:
    def __init__(self, resource_group: str = "private-rg", dry_run: bool = True):
        self.resource_group = resource_group
        self.dry_run = dry_run
        self.debug_patterns = [
            r"debug\d+",
            r"debug-.*",
            r".*debug.*\d{10}.*",  # debug with timestamp
            r".*\d{10}.*debug.*",  # timestamp with debug
        ]
        
        # Resources that should NEVER be deleted (production resources)
        self.preserve_resources = {
            "private-main-vnet",
            "private-ai-search", 
            "private-doc-int",
            "private-openai-agentic",
            "bastion-private",
            "linux-private-vm",
            "win-private-vm",
            "privateblogagenticimages",
            "foundry-private-uami",
            "foundry-private",
            "private-ai-search-private-endpoint",
            "index-ai-search-pe"
        }
        
    def run_az_command(self, command: List[str]) -> Optional[Dict[str, Any]]:
        """Execute an Azure CLI command and return parsed JSON result."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip():
                return json.loads(result.stdout)
            return None
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(command)}")
            print(f"Error: {e.stderr}")
            return None
        except json.JSONDecodeError:
            print(f"⚠️  Non-JSON output from command: {' '.join(command)}")
            return None

    def is_debug_resource(self, resource_name: str) -> bool:
        """Check if a resource name matches debug patterns."""
        if resource_name in self.preserve_resources:
            return False
            
        # Check if resource name matches any debug pattern
        for pattern in self.debug_patterns:
            if re.search(pattern, resource_name, re.IGNORECASE):
                return True
        return False

    def get_all_resources(self) -> List[Dict[str, Any]]:
        """Get all resources in the resource group."""
        command = [
            "az", "resource", "list",
            "--resource-group", self.resource_group,
            "--output", "json"
        ]
        
        resources = self.run_az_command(command)
        return resources if resources else []

    def get_debug_deployments(self) -> List[Dict[str, Any]]:
        """Get all debug deployments."""
        command = [
            "az", "deployment", "group", "list",
            "--resource-group", self.resource_group,
            "--output", "json"
        ]
        
        deployments = self.run_az_command(command)
        if not deployments:
            return []
            
        debug_deployments = []
        for deployment in deployments:
            if self.is_debug_resource(deployment.get("name", "")):
                debug_deployments.append(deployment)
                
        return debug_deployments

    def delete_ai_projects_from_ai_service(self, ai_service_name: str) -> bool:
        """Delete AI projects nested within an AI service account."""
        print(f"🔍 Checking AI projects in AI service: {ai_service_name}")
        
        # List AI projects in the AI service
        command = [
            "az", "rest",
            "--method", "GET",
            "--url", f"https://management.azure.com/subscriptions/{self.get_subscription_id()}/resourceGroups/{self.resource_group}/providers/Microsoft.CognitiveServices/accounts/{ai_service_name}/deployments?api-version=2023-05-01"
        ]
        
        projects_response = self.run_az_command(command)
        if not projects_response or "value" not in projects_response:
            print(f"ℹ️  No AI projects found in {ai_service_name}")
            return True
            
        projects = projects_response["value"]
        print(f"📋 Found {len(projects)} AI projects in {ai_service_name}")
        
        # Delete each AI project
        for project in projects:
            project_name = project.get("name", "")
            if project_name:
                if self.dry_run:
                    print(f"🟡 [DRY RUN] Would delete AI project: {project_name}")
                else:
                    print(f"🗑️  Deleting AI project: {project_name}")
                    delete_command = [
                        "az", "rest",
                        "--method", "DELETE",
                        "--url", f"https://management.azure.com/subscriptions/{self.get_subscription_id()}/resourceGroups/{self.resource_group}/providers/Microsoft.CognitiveServices/accounts/{ai_service_name}/deployments/{project_name}?api-version=2023-05-01"
                    ]
                    
                    result = self.run_az_command(delete_command)
                    if result is not None:
                        print(f"✅ Deleted AI project: {project_name}")
                    else:
                        print(f"❌ Failed to delete AI project: {project_name}")
                        return False
                        
        return True

    def get_subscription_id(self) -> str:
        """Get the current subscription ID."""
        command = ["az", "account", "show", "--query", "id", "-o", "tsv"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def delete_resource(self, resource: Dict[str, Any]) -> bool:
        """Delete a specific resource."""
        resource_name = resource.get("name", "")
        resource_type = resource.get("type", "")
        resource_id = resource.get("id", "")
        
        print(f"🗑️  Deleting {resource_type}: {resource_name}")
        
        if self.dry_run:
            print(f"🟡 [DRY RUN] Would delete: {resource_name} ({resource_type})")
            return True
            
        # Special handling for AI Services accounts with nested projects
        if resource_type == "Microsoft.CognitiveServices/accounts":
            print(f"🔍 AI Service detected, checking for nested projects...")
            if not self.delete_ai_projects_from_ai_service(resource_name):
                print(f"❌ Failed to delete nested projects in {resource_name}")
                return False
            # Wait a bit for nested deletions to complete
            time.sleep(5)
        
        # Delete the resource
        command = [
            "az", "resource", "delete",
            "--id", resource_id,
            "--verbose"
        ]
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            print(f"✅ Deleted: {resource_name}")
            return True
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout deleting {resource_name}, may still be in progress")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to delete {resource_name}: {e.stderr}")
            return False

    def delete_deployment(self, deployment: Dict[str, Any]) -> bool:
        """Delete a deployment."""
        deployment_name = deployment.get("name", "")
        
        if self.dry_run:
            print(f"🟡 [DRY RUN] Would delete deployment: {deployment_name}")
            return True
            
        print(f"🗑️  Deleting deployment: {deployment_name}")
        
        command = [
            "az", "deployment", "group", "delete",
            "--resource-group", self.resource_group,
            "--name", deployment_name
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"✅ Deleted deployment: {deployment_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to delete deployment {deployment_name}: {e.stderr}")
            return False

    def cleanup_debug_resources(self):
        """Main cleanup function."""
        print("🧹 Starting comprehensive debug resource cleanup...")
        print(f"Resource Group: {self.resource_group}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        print("=" * 60)
        
        # Get all resources
        print("📋 Scanning for debug resources...")
        all_resources = self.get_all_resources()
        debug_resources = [r for r in all_resources if self.is_debug_resource(r.get("name", ""))]
        
        print(f"Found {len(debug_resources)} debug resources out of {len(all_resources)} total resources")
        
        if debug_resources:
            print("\n📋 Debug resources found:")
            for resource in debug_resources:
                print(f"  - {resource.get('name')} ({resource.get('type')})")
        
        # Get debug deployments
        debug_deployments = self.get_debug_deployments()
        print(f"\nFound {len(debug_deployments)} debug deployments")
        
        if debug_deployments:
            print("\n📋 Debug deployments found:")
            for deployment in debug_deployments:
                print(f"  - {deployment.get('name')} ({deployment.get('properties', {}).get('provisioningState', 'Unknown')})")
        
        if not debug_resources and not debug_deployments:
            print("✅ No debug resources found to clean up!")
            return
        
        if self.dry_run:
            print(f"\n🟡 DRY RUN MODE: No resources will actually be deleted")
            print(f"Run with --execute to perform actual cleanup")
            return
        
        # Confirm deletion
        total_items = len(debug_resources) + len(debug_deployments)
        response = input(f"\n⚠️  This will delete {total_items} debug resources. Continue? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Cleanup cancelled")
            return
        
        # Delete resources (reverse order to handle dependencies)
        success_count = 0
        failed_count = 0
        
        print("\n🗑️  Deleting debug resources...")
        for resource in reversed(debug_resources):
            if self.delete_resource(resource):
                success_count += 1
            else:
                failed_count += 1
            time.sleep(1)  # Brief pause between deletions
        
        # Delete deployments
        print("\n🗑️  Deleting debug deployments...")
        for deployment in debug_deployments:
            if self.delete_deployment(deployment):
                success_count += 1
            else:
                failed_count += 1
        
        print(f"\n📊 Cleanup Summary:")
        print(f"  ✅ Successfully deleted: {success_count}")
        print(f"  ❌ Failed to delete: {failed_count}")
        
        if failed_count == 0:
            print("🎉 All debug resources cleaned up successfully!")
        else:
            print("⚠️  Some resources failed to delete. You may need to clean them up manually.")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up debug AI Foundry deployment resources")
    parser.add_argument("--resource-group", default="private-rg", 
                      help="Resource group name (default: private-rg)")
    parser.add_argument("--execute", action="store_true", 
                      help="Execute the cleanup (default is dry-run)")
    
    args = parser.parse_args()
    
    cleaner = DebugResourceCleaner(
        resource_group=args.resource_group,
        dry_run=not args.execute
    )
    
    cleaner.cleanup_debug_resources()

if __name__ == "__main__":
    main()
