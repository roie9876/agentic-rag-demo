#!/usr/bin/env python3
"""
Script to delete agent-subnet and hub-pe-subnet along with their private endpoints.
This will clean up the test subnets before running a fresh AI Foundry deployment.
"""

import subprocess
import json
import sys
import time
from typing import List, Dict, Any

class SubnetCleaner:
    def __init__(self, resource_group: str = "private-rg", vnet_name: str = "private-main-vnet"):
        self.resource_group = resource_group
        self.vnet_name = vnet_name
        self.target_subnets = ["agent-subnet", "hub-pe-subnet"]
        
    def run_command(self, command: List[str]) -> tuple[bool, str, str]:
        """Execute a command and return success, stdout, stderr."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr
    
    def get_private_endpoints_in_subnet(self, subnet_name: str) -> List[Dict[str, Any]]:
        """Get all private endpoints in a specific subnet."""
        print(f"🔍 Checking private endpoints in subnet: {subnet_name}")
        
        command = [
            "az", "network", "private-endpoint", "list",
            "--resource-group", self.resource_group,
            "--output", "json"
        ]
        
        success, stdout, stderr = self.run_command(command)
        if not success:
            print(f"❌ Failed to list private endpoints: {stderr}")
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
            print(f"❌ Failed to parse private endpoints JSON")
            return []
    
    def delete_private_endpoint(self, endpoint_name: str) -> bool:
        """Delete a private endpoint."""
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
    
    def delete_subnet(self, subnet_name: str) -> bool:
        """Delete a subnet."""
        print(f"🗑️  Deleting subnet: {subnet_name}")
        
        command = [
            "az", "network", "vnet", "subnet", "delete",
            "--resource-group", self.resource_group,
            "--vnet-name", self.vnet_name,
            "--name", subnet_name
        ]
        
        success, stdout, stderr = self.run_command(command)
        if success:
            print(f"✅ Deleted subnet: {subnet_name}")
            return True
        else:
            print(f"❌ Failed to delete subnet {subnet_name}: {stderr}")
            return False
    
    def check_subnet_exists(self, subnet_name: str) -> bool:
        """Check if a subnet exists."""
        command = [
            "az", "network", "vnet", "subnet", "show",
            "--resource-group", self.resource_group,
            "--vnet-name", self.vnet_name,
            "--name", subnet_name,
            "--output", "json"
        ]
        
        success, stdout, stderr = self.run_command(command)
        return success
    
    def clean_subnets(self):
        """Main cleanup function."""
        print("🧹 Starting subnet cleanup...")
        print(f"Resource Group: {self.resource_group}")
        print(f"VNet: {self.vnet_name}")
        print(f"Target Subnets: {', '.join(self.target_subnets)}")
        print("=" * 60)
        
        success_count = 0
        failed_count = 0
        
        for subnet_name in self.target_subnets:
            print(f"\n🔍 Processing subnet: {subnet_name}")
            
            # Check if subnet exists
            if not self.check_subnet_exists(subnet_name):
                print(f"ℹ️  Subnet {subnet_name} does not exist, skipping...")
                continue
            
            # Get private endpoints in this subnet
            endpoints = self.get_private_endpoints_in_subnet(subnet_name)
            
            if endpoints:
                print(f"📋 Found {len(endpoints)} private endpoint(s) in {subnet_name}:")
                for endpoint in endpoints:
                    print(f"   - {endpoint.get('name', 'Unknown')}")
                
                # Delete private endpoints first
                for endpoint in endpoints:
                    endpoint_name = endpoint.get("name", "")
                    if endpoint_name:
                        if self.delete_private_endpoint(endpoint_name):
                            success_count += 1
                        else:
                            failed_count += 1
                        time.sleep(2)  # Brief pause between deletions
            else:
                print(f"✅ No private endpoints found in {subnet_name}")
            
            # Wait a moment for private endpoint deletions to complete
            if endpoints:
                print("⏱️  Waiting for private endpoint deletions to complete...")
                time.sleep(10)
            
            # Delete the subnet
            if self.delete_subnet(subnet_name):
                success_count += 1
            else:
                failed_count += 1
        
        print(f"\n📊 Cleanup Summary:")
        print(f"  ✅ Successfully deleted: {success_count} resources")
        print(f"  ❌ Failed to delete: {failed_count} resources")
        
        if failed_count == 0:
            print("🎉 All target subnets and private endpoints cleaned up successfully!")
            print("✅ Environment is ready for fresh AI Foundry deployment")
        else:
            print("⚠️  Some resources failed to delete. You may need to clean them up manually.")
        
        # Verify cleanup
        print(f"\n🔍 Verifying cleanup...")
        for subnet_name in self.target_subnets:
            if self.check_subnet_exists(subnet_name):
                print(f"⚠️  Subnet {subnet_name} still exists")
            else:
                print(f"✅ Subnet {subnet_name} successfully deleted")

def main():
    print("🗑️  Subnet and Private Endpoint Cleanup Script")
    print("=" * 50)
    print("This will delete:")
    print("  - agent-subnet (and any private endpoints)")
    print("  - hub-pe-subnet (and any private endpoints)")
    print()
    
    response = input("⚠️  Continue with cleanup? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Cleanup cancelled")
        return 1
    
    cleaner = SubnetCleaner()
    cleaner.clean_subnets()
    return 0

if __name__ == "__main__":
    sys.exit(main())
