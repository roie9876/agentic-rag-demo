#!/usr/bin/env python3
"""
AI Foundry Debug Deployment Cleanup Tool

This script identifies and deletes all resources created by the debug AI Foundry deployment script.
It can clean up resources from specific deployments or all debug deployments.
"""

import subprocess
import json
import sys
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

class DebugDeploymentCleaner:
    def __init__(self, resource_group: str = "private-rg"):
        self.resource_group = resource_group
        self.debug_patterns = [
            r"debug\d{8}-\d{6}",  # debug20250704-183045
            r"debug\d{10}",       # debug0704183045 
            r"proj\d{10}",        # proj0704183045
            r".*debug.*",         # anything with debug
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
            "ASP-privaterg-bcc3",
            "blob-images-pe",
            "doc-int-pe",
            "openai-pe",
            "index-ai-search-pe",
            "foundry-fun-in"
        }
        
    def run_command(self, command: List[str]) -> tuple[bool, str, str]:
        """Execute a command and return success, stdout, stderr."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            return True, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
    
    def is_debug_resource(self, resource_name: str) -> bool:
        """Check if a resource name matches debug patterns."""
        if resource_name in self.preserve_resources:
            return False
            
        # Check if resource name matches any debug pattern
        for pattern in self.debug_patterns:
            if re.search(pattern, resource_name, re.IGNORECASE):
                return True
        return False
    
    def is_debug_deployment(self, deployment_name: str) -> bool:
        """Check if a deployment name is a debug deployment."""
        debug_deployment_patterns = [
            r"debug-ai-foundry-\d{8}-\d{6}",
            r"ai-debug\d+.*",
            r"dependencies-debug.*",
            r".*debug.*"
        ]
        
        for pattern in debug_deployment_patterns:
            if re.search(pattern, deployment_name, re.IGNORECASE):
                return True
        return False
    
    def get_debug_deployments(self) -> List[Dict[str, Any]]:
        """Get all debug deployments."""
        print("🔍 Scanning for debug deployments...")
        
        command = [
            "az", "deployment", "group", "list",
            "--resource-group", self.resource_group,
            "--output", "json"
        ]
        
        success, stdout, stderr = self.run_command(command)
        if not success:
            print(f"❌ Failed to list deployments: {stderr}")
            return []
            
        try:
            all_deployments = json.loads(stdout)
            debug_deployments = []
            
            for deployment in all_deployments:
                deployment_name = deployment.get("name", "")
                if self.is_debug_deployment(deployment_name):
                    debug_deployments.append(deployment)
                    
            return debug_deployments
        except json.JSONDecodeError:
            print(f"❌ Failed to parse deployments JSON")
            return []
    
    def get_debug_resources(self) -> List[Dict[str, Any]]:
        """Get all debug resources."""
        print("🔍 Scanning for debug resources...")
        
        command = [
            "az", "resource", "list",
            "--resource-group", self.resource_group,
            "--output", "json"
        ]
        
        success, stdout, stderr = self.run_command(command)
        if not success:
            print(f"❌ Failed to list resources: {stderr}")
            return []
            
        try:
            all_resources = json.loads(stdout)
            debug_resources = []
            
            for resource in all_resources:
                resource_name = resource.get("name", "")
                if self.is_debug_resource(resource_name):
                    debug_resources.append(resource)
                    
            return debug_resources
        except json.JSONDecodeError:
            print(f"❌ Failed to parse resources JSON")
            return []
    
    def get_debug_subnets(self) -> List[Dict[str, Any]]:
        """Get debug subnets that might have been created."""
        print("🔍 Checking for debug subnets...")
        
        command = [
            "az", "network", "vnet", "subnet", "list",
            "--resource-group", self.resource_group,
            "--vnet-name", "private-main-vnet",
            "--output", "json"
        ]
        
        success, stdout, stderr = self.run_command(command)
        if not success:
            print(f"❌ Failed to list subnets: {stderr}")
            return []
            
        try:
            all_subnets = json.loads(stdout)
            debug_subnets = []
            
            for subnet in all_subnets:
                subnet_name = subnet.get("name", "")
                # Look for debug subnet patterns
                if any(pattern in subnet_name.lower() for pattern in ["debug", "agent-subnet", "hub-pe-subnet"]):
                    # But preserve production subnets
                    if subnet_name not in ["default", "AzureBastionSubnet", "foundry-fun-out"]:
                        debug_subnets.append(subnet)
                        
            return debug_subnets
        except json.JSONDecodeError:
            print(f"❌ Failed to parse subnets JSON")
            return []
    
    def get_private_endpoints_in_subnet(self, subnet_name: str) -> List[Dict[str, Any]]:
        """Get private endpoints in a specific subnet."""
        command = [
            "az", "network", "private-endpoint", "list",
            "--resource-group", self.resource_group,
            "--output", "json"
        ]
        
        success, stdout, stderr = self.run_command(command)
        if not success:
            return []
            
        try:
            all_endpoints = json.loads(stdout)
            subnet_endpoints = []
            
            for endpoint in all_endpoints:
                subnet_id = endpoint.get("subnet", {}).get("id", "")
                if subnet_name in subnet_id:
                    subnet_endpoints.append(endpoint)
                    
            return subnet_endpoints
        except json.JSONDecodeError:
            return []
    
    def delete_ai_projects_from_ai_service(self, ai_service_name: str) -> bool:
        """Delete AI projects nested within an AI service account."""
        print(f"🔍 Checking AI projects in AI service: {ai_service_name}")
        
        # Get subscription ID
        sub_command = ["az", "account", "show", "--query", "id", "-o", "tsv"]
        success, sub_id, _ = self.run_command(sub_command)
        if not success:
            return False
        sub_id = sub_id.strip()
        
        # List AI projects in the AI service
        command = [
            "az", "rest",
            "--method", "GET",
            "--url", f"https://management.azure.com/subscriptions/{sub_id}/resourceGroups/{self.resource_group}/providers/Microsoft.CognitiveServices/accounts/{ai_service_name}/projects?api-version=2025-04-01-preview"
        ]
        
        success, stdout, stderr = self.run_command(command)
        if not success:
            print(f"ℹ️  Could not check AI projects in {ai_service_name}")
            return True
        
        try:
            projects_response = json.loads(stdout)
            projects = projects_response.get("value", [])
            
            if not projects:
                print(f"ℹ️  No AI projects found in {ai_service_name}")
                return True
                
            print(f"📋 Found {len(projects)} AI projects in {ai_service_name}")
            
            # Delete each AI project
            for project in projects:
                project_name = project.get("name", "")
                if project_name:
                    print(f"🗑️  Deleting AI project: {project_name}")
                    delete_command = [
                        "az", "resource", "delete",
                        "--id", f"/subscriptions/{sub_id}/resourceGroups/{self.resource_group}/providers/Microsoft.CognitiveServices/accounts/{ai_service_name}/projects/{project_name}"
                    ]
                    
                    delete_success, _, delete_stderr = self.run_command(delete_command)
                    if delete_success:
                        print(f"✅ Deleted AI project: {project_name}")
                    else:
                        print(f"❌ Failed to delete AI project: {project_name}")
                        return False
                        
            return True
        except json.JSONDecodeError:
            return True
    
    def delete_resource(self, resource: Dict[str, Any]) -> bool:
        """Delete a specific resource."""
        resource_name = resource.get("name", "")
        resource_type = resource.get("type", "")
        resource_id = resource.get("id", "")
        
        print(f"🗑️  Deleting {resource_type}: {resource_name}")
        
        # Special handling for AI Services accounts with nested projects
        if resource_type == "Microsoft.CognitiveServices/accounts":
            print(f"🔍 AI Service detected, checking for nested projects...")
            if not self.delete_ai_projects_from_ai_service(resource_name):
                print(f"❌ Failed to delete nested projects in {resource_name}")
                return False
            time.sleep(5)  # Wait for nested deletions
        
        # Delete the resource
        command = [
            "az", "resource", "delete",
            "--id", resource_id,
            "--verbose"
        ]
        
        success, stdout, stderr = self.run_command(command)
        if success:
            print(f"✅ Deleted: {resource_name}")
            return True
        else:
            print(f"❌ Failed to delete {resource_name}: {stderr}")
            return False
    
    def delete_private_endpoint(self, endpoint: Dict[str, Any]) -> bool:
        """Delete a private endpoint."""
        endpoint_name = endpoint.get("name", "")
        print(f"🗑️  Deleting private endpoint: {endpoint_name}")
        
        command = [
            "az", "network", "private-endpoint", "delete",
            "--resource-group", self.resource_group,
            "--name", endpoint_name
        ]
        
        success, stdout, stderr = self.run_command(command)
        if success:
            print(f"✅ Deleted private endpoint: {endpoint_name}")
            return True
        else:
            print(f"❌ Failed to delete private endpoint {endpoint_name}: {stderr}")
            return False
    
    def delete_subnet(self, subnet: Dict[str, Any]) -> bool:
        """Delete a subnet."""
        subnet_name = subnet.get("name", "")
        print(f"🗑️  Deleting subnet: {subnet_name}")
        
        command = [
            "az", "network", "vnet", "subnet", "delete",
            "--resource-group", self.resource_group,
            "--vnet-name", "private-main-vnet",
            "--name", subnet_name
        ]
        
        success, stdout, stderr = self.run_command(command)
        if success:
            print(f"✅ Deleted subnet: {subnet_name}")
            return True
        else:
            print(f"❌ Failed to delete subnet {subnet_name}: {stderr}")
            return False
    
    def delete_deployment(self, deployment: Dict[str, Any]) -> bool:
        """Delete a deployment."""
        deployment_name = deployment.get("name", "")
        print(f"🗑️  Deleting deployment: {deployment_name}")
        
        command = [
            "az", "deployment", "group", "delete",
            "--resource-group", self.resource_group,
            "--name", deployment_name
        ]
        
        success, stdout, stderr = self.run_command(command)
        if success:
            print(f"✅ Deleted deployment: {deployment_name}")
            return True
        else:
            print(f"❌ Failed to delete deployment {deployment_name}: {stderr}")
            return False
    
    def cleanup_debug_deployments(self, deployment_name_filter: Optional[str] = None):
        """Clean up debug deployments and their resources."""
        print("🧹 Starting comprehensive debug deployment cleanup...")
        print(f"Resource Group: {self.resource_group}")
        if deployment_name_filter:
            print(f"Filter: {deployment_name_filter}")
        print("=" * 60)
        
        success_count = 0
        failed_count = 0
        
        # Get all debug items
        debug_deployments = self.get_debug_deployments()
        debug_resources = self.get_debug_resources()
        debug_subnets = self.get_debug_subnets()
        
        # Filter by deployment name if specified
        if deployment_name_filter:
            debug_deployments = [d for d in debug_deployments if deployment_name_filter in d.get("name", "")]
            print(f"🔍 Filtered to deployments containing: {deployment_name_filter}")
        
        print(f"\n📋 Found items to clean up:")
        print(f"  - {len(debug_deployments)} debug deployments")
        print(f"  - {len(debug_resources)} debug resources")
        print(f"  - {len(debug_subnets)} debug subnets")
        
        if not any([debug_deployments, debug_resources, debug_subnets]):
            print("✅ No debug resources found to clean up!")
            return
        
        # Show what will be deleted
        if debug_deployments:
            print(f"\n📋 Debug deployments:")
            for deployment in debug_deployments:
                name = deployment.get("name", "Unknown")
                state = deployment.get("properties", {}).get("provisioningState", "Unknown")
                print(f"  - {name} ({state})")
        
        if debug_resources:
            print(f"\n📋 Debug resources:")
            for resource in debug_resources:
                name = resource.get("name", "Unknown")
                rtype = resource.get("type", "Unknown")
                print(f"  - {name} ({rtype})")
        
        if debug_subnets:
            print(f"\n📋 Debug subnets:")
            for subnet in debug_subnets:
                name = subnet.get("name", "Unknown")
                prefix = subnet.get("addressPrefix", "Unknown")
                print(f"  - {name} ({prefix})")
        
        # Confirm deletion
        total_items = len(debug_deployments) + len(debug_resources) + len(debug_subnets)
        response = input(f"\n⚠️  This will delete {total_items} debug items. Continue? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Cleanup cancelled")
            return
        
        # Delete subnets first (including their private endpoints)
        print(f"\n🗑️  Deleting debug subnets...")
        for subnet in debug_subnets:
            subnet_name = subnet.get("name", "")
            
            # Delete private endpoints in subnet first
            endpoints = self.get_private_endpoints_in_subnet(subnet_name)
            for endpoint in endpoints:
                if self.delete_private_endpoint(endpoint):
                    success_count += 1
                else:
                    failed_count += 1
                time.sleep(2)
            
            # Wait for PE deletions
            if endpoints:
                time.sleep(10)
            
            # Delete subnet
            if self.delete_subnet(subnet):
                success_count += 1
            else:
                failed_count += 1
        
        # Delete resources (reverse order to handle dependencies)
        print(f"\n🗑️  Deleting debug resources...")
        for resource in reversed(debug_resources):
            if self.delete_resource(resource):
                success_count += 1
            else:
                failed_count += 1
            time.sleep(2)
        
        # Delete deployments
        print(f"\n🗑️  Deleting debug deployments...")
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
            print("✅ Environment is ready for fresh deployment")
        else:
            print("⚠️  Some resources failed to delete. You may need to clean them up manually.")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up debug AI Foundry deployment resources")
    parser.add_argument("--resource-group", default="private-rg", 
                      help="Resource group name (default: private-rg)")
    parser.add_argument("--deployment-filter", 
                      help="Only clean up deployments containing this string")
    
    args = parser.parse_args()
    
    print("🗑️  AI Foundry Debug Deployment Cleanup Tool")
    print("=" * 50)
    
    cleaner = DebugDeploymentCleaner(resource_group=args.resource_group)
    cleaner.cleanup_debug_deployments(deployment_name_filter=args.deployment_filter)

if __name__ == "__main__":
    main()
