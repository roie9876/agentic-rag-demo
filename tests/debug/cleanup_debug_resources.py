#!/usr/bin/env python3
"""
Debug Resources Cleanup Script

This script safely removes incomplete deployments and resources created by debug scripts,
while preserving existing important resources like 'private-ai-search' and production resources.
"""

import os
import json
import subprocess
import logging
import sys
import re
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class DebugResourcesCleaner:
    """Safely clean up debug resources while preserving production resources."""
    
    def __init__(self):
        """Initialize the cleaner."""
        self.resource_group = "private-rg"
        self.dry_run = True  # Start with dry run for safety
        
        # Patterns to identify debug resources (SAFE TO DELETE)
        self.debug_patterns = [
            r"debug\d+",           # debug07041639, debug070417525ulr, etc.
            r"proj\d+",            # proj07041639, proj070417525ulr, etc.
            r"debug-ai-foundry-",  # deployment names
            r"ai-debug\d+",        # AI service deployment names
            r"ai-proj\d+",         # AI project deployment names
        ]
        
        # PROTECTED resources (NEVER DELETE)
        self.protected_resources = [
            "private-ai-search",
            "private-main-vnet",
            "hub-pe-subnet",
            "agent-subnet", 
            "default",
            "AzureBastionSubnet",
            "foundry-fun-out",
            "private-rg",
        ]
    
    def is_debug_resource(self, resource_name: str) -> bool:
        """Check if a resource is a debug resource that can be safely deleted."""
        if not resource_name:
            return False
            
        # Never delete protected resources
        if resource_name in self.protected_resources:
            return False
            
        # Check if matches debug patterns
        for pattern in self.debug_patterns:
            if re.search(pattern, resource_name, re.IGNORECASE):
                return True
                
        return False
    
    def list_incomplete_deployments(self) -> List[str]:
        """List all incomplete/failed deployments related to debug scripts."""
        logger.info("🔍 Finding incomplete debug deployments...")
        
        incomplete_deployments = []
        
        try:
            result = subprocess.run([
                "az", "deployment", "group", "list",
                "--resource-group", self.resource_group,
                "--query", "[?properties.provisioningState!='Succeeded'].{Name:name, State:properties.provisioningState}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                deployments = json.loads(result.stdout)
                logger.info(f"📋 Found {len(deployments)} incomplete deployments:")
                
                for deployment in deployments:
                    name = deployment.get('Name', '')
                    state = deployment.get('State', '')
                    
                    if self.is_debug_resource(name):
                        logger.info(f"   🗑️ DEBUG: {name} ({state}) - WILL BE DELETED")
                        incomplete_deployments.append(name)
                    else:
                        logger.info(f"   🔒 PROTECTED: {name} ({state}) - PRESERVED")
                        
        except Exception as e:
            logger.error(f"❌ Error listing deployments: {e}")
            
        return incomplete_deployments
    
    def list_debug_cognitive_services(self) -> List[Dict[str, str]]:
        """List AI Services accounts created by debug scripts."""
        logger.info("🔍 Finding debug AI Services accounts...")
        
        debug_accounts = []
        
        try:
            result = subprocess.run([
                "az", "cognitiveservices", "account", "list",
                "--resource-group", self.resource_group,
                "--query", "[].{Name:name, State:properties.provisioningState}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                accounts = json.loads(result.stdout)
                logger.info(f"📋 Found {len(accounts)} AI Services accounts:")
                
                for account in accounts:
                    name = account.get('Name', '')
                    state = account.get('State', '')
                    
                    if self.is_debug_resource(name):
                        logger.info(f"   🗑️ DEBUG: {name} ({state}) - WILL BE DELETED")
                        debug_accounts.append(account)
                    else:
                        logger.info(f"   🔒 PROTECTED: {name} ({state}) - PRESERVED")
                        
        except Exception as e:
            logger.error(f"❌ Error listing AI Services: {e}")
            
        return debug_accounts
    
    def list_debug_storage_accounts(self) -> List[Dict[str, str]]:
        """List storage accounts created by debug scripts."""
        logger.info("🔍 Finding debug storage accounts...")
        
        debug_storage = []
        
        try:
            result = subprocess.run([
                "az", "storage", "account", "list",
                "--resource-group", self.resource_group,
                "--query", "[].{Name:name, State:properties.provisioningState}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                accounts = json.loads(result.stdout)
                logger.info(f"📋 Found {len(accounts)} storage accounts:")
                
                for account in accounts:
                    name = account.get('Name', '')
                    state = account.get('State', '')
                    
                    if self.is_debug_resource(name):
                        logger.info(f"   🗑️ DEBUG: {name} ({state}) - WILL BE DELETED")
                        debug_storage.append(account)
                    else:
                        logger.info(f"   🔒 PROTECTED: {name} ({state}) - PRESERVED")
                        
        except Exception as e:
            logger.error(f"❌ Error listing storage accounts: {e}")
            
        return debug_storage
    
    def list_debug_cosmos_accounts(self) -> List[Dict[str, str]]:
        """List Cosmos DB accounts created by debug scripts."""
        logger.info("🔍 Finding debug Cosmos DB accounts...")
        
        debug_cosmos = []
        
        try:
            result = subprocess.run([
                "az", "cosmosdb", "list",
                "--resource-group", self.resource_group,
                "--query", "[].{Name:name, State:properties.provisioningState}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                accounts = json.loads(result.stdout)
                logger.info(f"📋 Found {len(accounts)} Cosmos DB accounts:")
                
                for account in accounts:
                    name = account.get('Name', '')
                    state = account.get('State', '')
                    
                    if self.is_debug_resource(name):
                        logger.info(f"   🗑️ DEBUG: {name} ({state}) - WILL BE DELETED")
                        debug_cosmos.append(account)
                    else:
                        logger.info(f"   🔒 PROTECTED: {name} ({state}) - PRESERVED")
                        
        except Exception as e:
            logger.error(f"❌ Error listing Cosmos DB accounts: {e}")
            
        return debug_cosmos
    
    def list_debug_private_endpoints(self) -> List[Dict[str, str]]:
        """List private endpoints created by debug scripts."""
        logger.info("🔍 Finding debug private endpoints...")
        
        debug_endpoints = []
        
        try:
            result = subprocess.run([
                "az", "network", "private-endpoint", "list",
                "--resource-group", self.resource_group,
                "--query", "[].{Name:name, State:provisioningState}",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                endpoints = json.loads(result.stdout)
                logger.info(f"📋 Found {len(endpoints)} private endpoints:")
                
                for endpoint in endpoints:
                    name = endpoint.get('Name', '')
                    state = endpoint.get('State', '')
                    
                    if self.is_debug_resource(name):
                        logger.info(f"   🗑️ DEBUG: {name} ({state}) - WILL BE DELETED")
                        debug_endpoints.append(endpoint)
                    else:
                        logger.info(f"   🔒 PROTECTED: {name} ({state}) - PRESERVED")
                        
        except Exception as e:
            logger.error(f"❌ Error listing private endpoints: {e}")
            
        return debug_endpoints
    
    def cancel_running_deployments(self, deployment_names: List[str]):
        """Cancel running deployments."""
        logger.info("🛑 Canceling running debug deployments...")
        
        for deployment_name in deployment_names:
            try:
                logger.info(f"🛑 Canceling deployment: {deployment_name}")
                
                if not self.dry_run:
                    result = subprocess.run([
                        "az", "deployment", "group", "cancel",
                        "--resource-group", self.resource_group,
                        "--name", deployment_name
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Canceled: {deployment_name}")
                    else:
                        logger.warning(f"⚠️ Could not cancel {deployment_name}: {result.stderr}")
                else:
                    logger.info(f"   [DRY RUN] Would cancel: {deployment_name}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error canceling {deployment_name}: {e}")
    
    def delete_resources(self, resource_type: str, resources: List[Dict[str, str]], delete_command_template: List[str]):
        """Delete resources of a specific type."""
        logger.info(f"🗑️ Deleting debug {resource_type}...")
        
        for resource in resources:
            name = resource.get('Name', '')
            
            try:
                # Build delete command
                delete_cmd = []
                for part in delete_command_template:
                    if "{name}" in part:
                        delete_cmd.append(part.replace("{name}", name))
                    elif "{resource_group}" in part:
                        delete_cmd.append(part.replace("{resource_group}", self.resource_group))
                    else:
                        delete_cmd.append(part)
                
                logger.info(f"🗑️ Deleting {resource_type}: {name}")
                
                if not self.dry_run:
                    result = subprocess.run(delete_cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Deleted: {name}")
                    else:
                        logger.warning(f"⚠️ Could not delete {name}: {result.stderr}")
                else:
                    logger.info(f"   [DRY RUN] Would delete: {name}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error deleting {name}: {e}")
    
    def cleanup_debug_resources(self, dry_run: bool = True):
        """Main cleanup function."""
        self.dry_run = dry_run
        
        logger.info("🧹 STARTING DEBUG RESOURCES CLEANUP")
        logger.info("=" * 50)
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No resources will be deleted")
        else:
            logger.info("⚠️ LIVE MODE - Resources WILL BE DELETED!")
            
        logger.info(f"📋 Resource Group: {self.resource_group}")
        logger.info("🔒 Protected resources will be preserved")
        logger.info("🗑️ Debug resources will be removed")
        
        # Step 1: List all debug resources
        incomplete_deployments = self.list_incomplete_deployments()
        debug_cognitive = self.list_debug_cognitive_services()
        debug_storage = self.list_debug_storage_accounts()
        debug_cosmos = self.list_debug_cosmos_accounts()
        debug_endpoints = self.list_debug_private_endpoints()
        
        # Summary
        total_resources = (len(incomplete_deployments) + len(debug_cognitive) + 
                          len(debug_storage) + len(debug_cosmos) + len(debug_endpoints))
        
        logger.info(f"\n📊 CLEANUP SUMMARY:")
        logger.info(f"   Incomplete deployments: {len(incomplete_deployments)}")
        logger.info(f"   AI Services accounts: {len(debug_cognitive)}")
        logger.info(f"   Storage accounts: {len(debug_storage)}")
        logger.info(f"   Cosmos DB accounts: {len(debug_cosmos)}")
        logger.info(f"   Private endpoints: {len(debug_endpoints)}")
        logger.info(f"   TOTAL DEBUG RESOURCES: {total_resources}")
        
        if total_resources == 0:
            logger.info("✅ No debug resources found to clean up!")
            return True
        
        # Step 2: Cancel running deployments
        if incomplete_deployments:
            self.cancel_running_deployments(incomplete_deployments)
        
        # Step 3: Delete resources (in correct order to avoid dependency issues)
        
        # Delete private endpoints first (they depend on other resources)
        if debug_endpoints:
            self.delete_resources("private endpoints", debug_endpoints, [
                "az", "network", "private-endpoint", "delete",
                "--resource-group", "{resource_group}",
                "--name", "{name}",
                "--yes"
            ])
        
        # Delete AI Services accounts (may have projects)
        if debug_cognitive:
            self.delete_resources("AI Services accounts", debug_cognitive, [
                "az", "cognitiveservices", "account", "delete",
                "--resource-group", "{resource_group}",
                "--name", "{name}",
                "--yes"
            ])
        
        # Delete storage accounts
        if debug_storage:
            self.delete_resources("storage accounts", debug_storage, [
                "az", "storage", "account", "delete",
                "--resource-group", "{resource_group}",
                "--name", "{name}",
                "--yes"
            ])
        
        # Delete Cosmos DB accounts
        if debug_cosmos:
            self.delete_resources("Cosmos DB accounts", debug_cosmos, [
                "az", "cosmosdb", "delete",
                "--resource-group", "{resource_group}",
                "--name", "{name}",
                "--yes"
            ])
        
        logger.info("\n✅ DEBUG RESOURCES CLEANUP COMPLETED!")
        
        if dry_run:
            logger.info("ℹ️ This was a DRY RUN - no actual deletions occurred")
            logger.info("ℹ️ Run with --execute to perform actual cleanup")
        else:
            logger.info("🗑️ All debug resources have been removed")
            logger.info("🔒 Protected resources remain intact")
        
        return True

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up debug resources from failed deployments')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute actual cleanup (default is dry-run)')
    parser.add_argument('--list-only', action='store_true',
                       help='Only list resources, do not delete anything')
    
    args = parser.parse_args()
    
    print("🧹 Debug Resources Cleanup Tool")
    print("=" * 40)
    
    cleaner = DebugResourcesCleaner()
    
    if args.list_only:
        print("📋 LIST-ONLY MODE - Showing resources that would be cleaned")
        cleaner.cleanup_debug_resources(dry_run=True)
    elif args.execute:
        print("⚠️ EXECUTE MODE - Resources will be deleted!")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() == 'yes':
            cleaner.cleanup_debug_resources(dry_run=False)
        else:
            print("❌ Cleanup cancelled")
            return 1
    else:
        print("🔍 DRY-RUN MODE - Showing what would be cleaned")
        cleaner.cleanup_debug_resources(dry_run=True)
        print("\nℹ️ Use --execute to perform actual cleanup")
        print("ℹ️ Use --list-only to just see the resources")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
