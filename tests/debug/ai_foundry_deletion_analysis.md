# Enhanced Resource Group Deletion for debug_ai_foundry_deployment.py

## 🔧 **Proposed Enhancement for cleanup_failed_deployment():**

```python
def cleanup_failed_deployment(self):
    """Clean up resources from failed deployment with proper deletion logic."""
    logger.info("🧹 Starting comprehensive cleanup of failed deployment...")
    
    # Option 1: Delete entire resource group (nuclear option)
    if self.should_delete_entire_rg():
        return self.delete_resource_group_with_sal_handling()
    
    # Option 2: Delete specific deployment resources
    return self.delete_deployment_resources()

def should_delete_entire_rg(self) -> bool:
    """Check if we should delete the entire resource group."""
    try:
        # Get all resources in RG
        result = subprocess.run([
            "az", "resource", "list",
            "--resource-group", self.resource_group,
            "--output", "json"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            resources = json.loads(result.stdout)
            logger.info(f"📊 Found {len(resources)} total resources in RG")
            
            # If it's a test/debug RG with few resources, delete everything
            if len(resources) <= 10:  # Configurable threshold
                logger.info("🎯 Small resource group - recommending full deletion")
                return True
            else:
                logger.info("⚠️ Large resource group - using selective deletion")
                return False
        
    except Exception as e:
        logger.warning(f"⚠️ Error checking RG size: {e}")
        return False

def delete_resource_group_with_sal_handling(self) -> bool:
    """Delete resource group with SAL (Service Association Link) handling."""
    logger.info(f"🗑️ Attempting to delete resource group: {self.resource_group}")
    
    # First, try standard deletion
    success = self.try_standard_rg_deletion()
    if success:
        return True
    
    # If standard deletion fails, check for SALs
    logger.warning("⚠️ Standard deletion failed - checking for Service Association Links...")
    
    sal_names = self.find_service_association_links()
    if sal_names:
        logger.warning(f"🔗 Found {len(sal_names)} Service Association Links blocking deletion")
        
        # Try SAL-aware deletion
        return self.delete_rg_with_sal_cleanup(sal_names)
    else:
        # Some other issue
        logger.error("❌ No SALs found - other deletion blocker present")
        return False

def try_standard_rg_deletion(self) -> bool:
    """Try standard resource group deletion."""
    try:
        result = subprocess.run([
            "az", "group", "delete",
            "--name", self.resource_group,
            "--yes",
            "--no-wait"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✅ Standard resource group deletion initiated")
            # Monitor deletion progress
            return self.monitor_rg_deletion()
        else:
            logger.warning(f"⚠️ Standard deletion failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ Standard deletion exception: {e}")
        return False

def find_service_association_links(self) -> List[str]:
    """Find Service Association Links that might be blocking deletion."""
    sal_names = []
    
    try:
        # Get all VNets in the resource group
        result = subprocess.run([
            "az", "network", "vnet", "list",
            "--resource-group", self.resource_group,
            "--output", "json"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            vnets = json.loads(result.stdout)
            
            for vnet in vnets:
                vnet_name = vnet.get('name', '')
                logger.info(f"🔍 Checking VNet: {vnet_name}")
                
                # Check each subnet for SALs
                subnets = vnet.get('subnets', [])
                for subnet in subnets:
                    subnet_name = subnet.get('name', '')
                    subnet_sals = self.get_subnet_sals(vnet_name, subnet_name)
                    if subnet_sals:
                        logger.warning(f"🔗 Found SALs in {vnet_name}/{subnet_name}: {subnet_sals}")
                        sal_names.extend(subnet_sals)
        
    except Exception as e:
        logger.warning(f"⚠️ Error finding SALs: {e}")
    
    return sal_names

def get_subnet_sals(self, vnet_name: str, subnet_name: str) -> List[str]:
    """Get Service Association Links for a specific subnet."""
    try:
        # Get subscription ID
        sub_result = subprocess.run([
            "az", "account", "show", "--query", "id", "--output", "tsv"
        ], capture_output=True, text=True, timeout=30)
        
        if sub_result.returncode != 0:
            return []
        
        subscription_id = sub_result.stdout.strip()
        
        # Build SAL REST API URL
        sal_url = (
            f"https://management.azure.com/subscriptions/{subscription_id}/"
            f"resourceGroups/{self.resource_group}/providers/Microsoft.Network/"
            f"virtualNetworks/{vnet_name}/subnets/{subnet_name}/"
            f"serviceAssociationLinks?api-version=2024-05-01"
        )
        
        # Call REST API
        result = subprocess.run([
            "az", "rest", "--method", "get", "--url", sal_url,
            "--query", "value[].name", "--output", "json"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            sal_names = json.loads(result.stdout) if result.stdout.strip() else []
            return sal_names
        
    except Exception as e:
        logger.warning(f"⚠️ Error getting SALs for {vnet_name}/{subnet_name}: {e}")
    
    return []

def delete_rg_with_sal_cleanup(self, sal_names: List[str]) -> bool:
    """Attempt resource group deletion with SAL cleanup."""
    logger.info("🎯 Attempting SAL-aware deletion process...")
    
    # Log the blocking SALs
    logger.warning(f"🔗 Blocked by {len(sal_names)} Service Association Links:")
    for sal_name in sal_names:
        logger.warning(f"   - {sal_name}")
    
    # Try direct SAL deletion (will likely fail with UnauthorizedClientApplication)
    for sal_name in sal_names:
        success = self.try_delete_sal(sal_name)
        if not success:
            logger.error(f"❌ Cannot delete SAL '{sal_name}' - requires Microsoft Support")
    
    # Since SAL deletion will fail, provide clear guidance
    logger.error("💔 RESOURCE GROUP DELETION BLOCKED")
    logger.error("🔗 Service Association Links prevent deletion")
    logger.error("📞 SOLUTION: Contact Microsoft Support with this information:")
    logger.error(f"   - Resource Group: {self.resource_group}")
    logger.error(f"   - Blocking SALs: {', '.join(sal_names)}")
    logger.error(f"   - Error: UnauthorizedClientApplication for SAL deletion")
    
    return False

def try_delete_sal(self, sal_name: str) -> bool:
    """Try to delete a Service Association Link (will likely fail)."""
    logger.info(f"🗑️ Attempting to delete SAL: {sal_name}")
    
    try:
        # This will fail with UnauthorizedClientApplication, but we try anyway
        # to generate the exact error for support ticket
        
        # Get subscription ID
        sub_result = subprocess.run([
            "az", "account", "show", "--query", "id", "--output", "tsv"
        ], capture_output=True, text=True, timeout=30)
        
        if sub_result.returncode != 0:
            return False
        
        subscription_id = sub_result.stdout.strip()
        
        # Try to delete the SAL (this will fail)
        sal_delete_url = (
            f"https://management.azure.com/subscriptions/{subscription_id}/"
            f"resourceGroups/{self.resource_group}/providers/Microsoft.Network/"
            f"virtualNetworks/*/subnets/*/serviceAssociationLinks/{sal_name}"
            f"?api-version=2024-05-01"
        )
        
        result = subprocess.run([
            "az", "rest", "--method", "delete", "--url", sal_delete_url
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully deleted SAL: {sal_name}")
            return True
        else:
            logger.error(f"❌ Failed to delete SAL: {sal_name}")
            logger.error(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Exception deleting SAL {sal_name}: {e}")
        return False

def delete_deployment_resources(self) -> bool:
    """Delete specific resources created by the deployment."""
    logger.info("🗑️ Deleting specific deployment resources...")
    
    # Get resources by deployment name (if tagged)
    tagged_resources = self.get_deployment_resources_by_tag()
    
    # Get resources by deployment operations
    operation_resources = self.get_deployment_resources_by_operations()
    
    # Combine and deduplicate
    all_resources = list(set(tagged_resources + operation_resources))
    
    if not all_resources:
        logger.info("ℹ️ No deployment resources found to delete")
        return True
    
    logger.info(f"🗑️ Found {len(all_resources)} resources to delete")
    
    # Delete in reverse dependency order
    return self.delete_resources_in_order(all_resources)

def get_deployment_resources_by_operations(self) -> List[str]:
    """Get resources created by deployment operations."""
    resource_ids = []
    
    try:
        result = subprocess.run([
            "az", "deployment", "operation", "group", "list",
            "--resource-group", self.resource_group,
            "--name", self.deployment_name,
            "--query", "[].properties.targetResource.id",
            "--output", "json"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            ids = json.loads(result.stdout)
            resource_ids = [id for id in ids if id]  # Filter out None values
            logger.info(f"📋 Found {len(resource_ids)} resources from deployment operations")
        
    except Exception as e:
        logger.warning(f"⚠️ Error getting deployment operation resources: {e}")
    
    return resource_ids

def delete_resources_in_order(self, resource_ids: List[str]) -> bool:
    """Delete resources in proper dependency order."""
    logger.info(f"🗑️ Deleting {len(resource_ids)} resources in dependency order...")
    
    # Define deletion order (dependencies first)
    deletion_order = [
        "Microsoft.Network/privateEndpoints",
        "Microsoft.MachineLearningServices/workspaces", 
        "Microsoft.CognitiveServices/accounts",
        "Microsoft.Storage/storageAccounts",
        "Microsoft.DocumentDB/databaseAccounts",
        "Microsoft.Network/networkSecurityGroups",
        "Microsoft.Network/virtualNetworks",
        "*"  # Everything else
    ]
    
    success_count = 0
    
    for resource_type_pattern in deletion_order:
        matching_resources = [
            rid for rid in resource_ids 
            if resource_type_pattern == "*" or resource_type_pattern in rid
        ]
        
        for resource_id in matching_resources:
            if self.delete_single_resource(resource_id):
                success_count += 1
                resource_ids.remove(resource_id)  # Don't try to delete again
    
    logger.info(f"✅ Successfully deleted {success_count} resources")
    
    if resource_ids:
        logger.warning(f"⚠️ Failed to delete {len(resource_ids)} resources:")
        for rid in resource_ids:
            logger.warning(f"   - {rid}")
        return False
    
    return True

def delete_single_resource(self, resource_id: str) -> bool:
    """Delete a single Azure resource."""
    logger.info(f"🗑️ Deleting resource: {resource_id}")
    
    try:
        result = subprocess.run([
            "az", "resource", "delete",
            "--ids", resource_id,
            "--no-wait"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"✅ Deletion initiated for: {resource_id}")
            return True
        else:
            logger.warning(f"⚠️ Failed to delete {resource_id}: {result.stderr}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ Exception deleting {resource_id}: {e}")
        return False
```

## 📋 **Summary of Current vs Enhanced Deletion:**

| **Aspect** | **Current Implementation** | **Enhanced Implementation** |
|---|---|---|
| **Resource Discovery** | ❌ Tag-based only (incomplete) | ✅ Multiple methods (tags + operations) |
| **Actual Deletion** | ❌ Just logging | ✅ Real deletion commands |
| **SAL Handling** | ❌ No awareness | ✅ Detects and attempts SAL cleanup |
| **Dependency Order** | ❌ Random order | ✅ Proper deletion sequence |
| **RG Deletion** | ❌ Not implemented | ✅ Full RG deletion with monitoring |
| **Error Handling** | ❌ Basic try/catch | ✅ Detailed error analysis |
| **Support Guidance** | ❌ None | ✅ Clear escalation path |

**The current implementation is essentially a placeholder that doesn't actually delete anything!**
