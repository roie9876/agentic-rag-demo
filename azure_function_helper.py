"""
Azure Function Helper Module
---------------------------
Contains functionality for managing Azure Functions configuration and deployment.
"""

import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import re

from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.mgmt.web import WebSiteManagementClient
from dotenv import dotenv_values


def load_env_vars() -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_file_path = Path(__file__).resolve().parent / ".env"
    return dotenv_values(env_file_path) if env_file_path.exists() else {}


def get_azure_subscription() -> str:
    """Try to get Azure subscription ID from az CLI."""
    try:
        out = subprocess.check_output(
            ["az", "account", "show", "-o", "json"], 
            text=True, 
            timeout=3
        )
        data = json.loads(out)
        return data.get("id", "")
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        # Return empty string if Azure CLI fails, times out, or is not available
        return ""


def get_available_subscriptions() -> Tuple[List[str], Dict[str, str]]:
    """
    Get list of available Azure subscriptions using Azure CLI.
    
    Returns:
        Tuple of (subscription_choices: List[str], subscription_map: Dict[str, str])
        where subscription_map maps "display_name (subscription_id)" -> subscription_id
    """
    subscription_choices = []
    subscription_map = {}
    
    try:
        # Get list of all accessible subscriptions
        out = subprocess.check_output(
            ["az", "account", "list", "-o", "json"], 
            text=True, 
            timeout=10
        )
        subscriptions = json.loads(out)
        
        for sub in subscriptions:
            if sub.get("state") == "Enabled":
                sub_id = sub.get("id", "")
                sub_name = sub.get("name", "Unknown")
                
                if sub_id:
                    # Create display label with name and subscription ID
                    label = f"{sub_name} ({sub_id})"
                    subscription_choices.append(label)
                    subscription_map[label] = sub_id
                    
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        # Return empty lists if Azure CLI fails
        pass
        
    return subscription_choices, subscription_map


def list_function_apps(subscription_id: str) -> Tuple[List[str], Dict[str, Tuple[str, str, str]]]:
    """
    List all Function Apps in the subscription.
    
    Returns:
        Tuple of (func_choices: List[str], func_map: Dict[str, Tuple[str, str, str]])
        where func_map maps "app (rg)" -> (name, resource_group, default_hostname)
    """
    func_choices = []
    func_map = {}
    
    if not subscription_id:
        return func_choices, func_map
        
    try:
        # Set the subscription context first
        import subprocess
        subprocess.run(["az", "account", "set", "--subscription", subscription_id], 
                      capture_output=True, timeout=10)
        
        # Use Azure CLI credential to match the same authentication context as discovery service
        wcli = WebSiteManagementClient(AzureCliCredential(), subscription_id)
        for site in wcli.web_apps.list():
            # Filter only Function Apps (kind contains "functionapp")
            if site.kind and "functionapp" in site.kind:
                label = f"{site.name}  ({site.resource_group})"
                func_choices.append(label)
                # Include the actual hostname/domain from Azure
                hostname = getattr(site, 'default_host_name', f"{site.name}.azurewebsites.net")
                func_map[label] = (site.name, site.resource_group, hostname)
                
    except Exception as e:
        # Try fallback with Azure CLI
        try:
            import subprocess
            result = subprocess.run([
                "az", "functionapp", "list", 
                "--subscription", subscription_id,
                "--query", "[].{name:name, resourceGroup:resourceGroup, kind:kind, defaultHostName:defaultHostName}",
                "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                apps = json.loads(result.stdout)
                for app in apps:
                    if app.get("kind") and "functionapp" in app.get("kind", ""):
                        name = app.get("name", "")
                        rg = app.get("resourceGroup", "")
                        hostname = app.get("defaultHostName", f"{name}.azurewebsites.net")
                        
                        if name and rg:
                            label = f"{name}  ({rg})"
                            func_choices.append(label)
                            func_map[label] = (name, rg, hostname)
        except Exception:
            pass  # Final fallback - return empty lists
        
    return func_choices, func_map


def mask_sensitive_value(value: str) -> str:
    """Mask sensitive values like keys and secrets."""
    # Convert value to string first to handle any type
    value_str = str(value)
    
    # Check for KeyVault references or sensitive patterns
    if (value_str.startswith("@Microsoft.KeyVault(") or 
        re.search(r"(key|secret|token|pass)", value_str, re.I)):
        return "••••••"
    return value_str


def load_function_settings(
    resource_group: str, 
    function_name: str, 
    subscription_id: str,
    env_vars: Dict[str, str],
    ui_overrides: Dict[str, str] = None
) -> Tuple[bool, Optional[pd.DataFrame], Dict, str]:
    """
    Load Function App settings and merge with .env values.
    
    Args:
        resource_group: Azure resource group name
        function_name: Azure Function App name
        subscription_id: Azure subscription ID
        env_vars: Environment variables from .env file
        ui_overrides: Dict of values from UI that should always override Function App settings
        
    Returns:
        Tuple of (success: bool, dataframe: Optional[pd.DataFrame], raw_settings: Dict, error_msg: str)
    """
    if ui_overrides is None:
        ui_overrides = {}
        
    if not all((subscription_id, resource_group, function_name)):
        return False, None, {}, "Missing required parameters"
        
    try:
        wcli = WebSiteManagementClient(AzureCliCredential(), subscription_id)
        cfg = wcli.web_apps.list_application_settings(resource_group, function_name)
        raw = cfg.properties or {}
        
        # Debug: Show what we loaded from Azure
        print(f"DEBUG: Loaded {len(raw)} settings from Azure Function App")
        
        # Merge precedence: Function settings ← .env values (1‑to‑1)
        param_vals = raw.copy()
        
        # Map .env values to Function App setting names
        env_to_function_mapping = {
            "INDEX_NAME": "INDEX_NAME",
            "AGENT_NAME": "AGENT_NAME",
            "AZURE_SEARCH_ENDPOINT": "SERVICE_NAME",  # Special handling needed
            "AZURE_OPENAI_ENDPOINT": "OPENAI_ENDPOINT",
            "AZURE_OPENAI_ENDPOINT_41": "OPENAI_ENDPOINT",  # Support _41 suffix (preferred)
            "AZURE_OPENAI_DEPLOYMENT": "OPENAI_DEPLOYMENT", 
            "AZURE_OPENAI_DEPLOYMENT_41": "OPENAI_DEPLOYMENT",  # Support _41 suffix (preferred)
            "AZURE_OPENAI_CHAT_DEPLOYMENT": "OPENAI_DEPLOYMENT",  # Fallback for compatibility
            # API_VERSION removed - should be empty when loading settings
            "MAX_OUTPUT_SIZE": "MAX_OUTPUT_SIZE",
            "RERANKER_THRESHOLD": "RERANKER_THRESHOLD", 
            "TOP_K": "TOP_K",
            "debug": "debug",
            "includesrc": "includesrc",
            # Legacy keys (optional for fallback compatibility)
            "AZURE_OPENAI_KEY": "OPENAI_KEY",
            "AZURE_OPENAI_KEY_41": "OPENAI_KEY",  # Support _41 suffix
            "AZURE_SEARCH_KEY": "SEARCH_API_KEY"
        }
        
        # Apply .env values to function settings (prioritize _41 variants and override empty values)
        for env_key, func_key in env_to_function_mapping.items():
            if env_key in env_vars and env_vars[env_key]:
                current_value = param_vals.get(func_key, "")
                
                if func_key == "SERVICE_NAME" and env_vars[env_key]:
                    # Extract service name from AZURE_SEARCH_ENDPOINT
                    import re
                    match = re.search(r'https://([^.]+)\.search\.windows\.net', env_vars[env_key])
                    if match:
                        param_vals[func_key] = match.group(1)
                        print(f"DEBUG: Mapped {env_key} -> {func_key}: {match.group(1)} (was: '{current_value}')")
                    else:
                        print(f"DEBUG: Failed to extract service name from: {env_vars[env_key]}")
                else:
                    # Update if:
                    # 1. Key doesn't exist in function app
                    # 2. Key exists but is empty/None in function app  
                    # 3. This is a _41 variant (preferred - these always override)
                    should_update = (
                        func_key not in param_vals or 
                        not current_value or 
                        current_value.strip() == "" or
                        env_key.endswith('_41')
                    )
                    
                    if should_update:
                        param_vals[func_key] = env_vars[env_key]
                        print(f"DEBUG: Mapped {env_key} -> {func_key}: {env_vars[env_key][:20]}... (was: '{current_value}')")
                    else:
                        print(f"DEBUG: Skipped {env_key} -> {func_key}: Function App has existing value '{current_value}'")
        
        # Apply direct env_vars that are already in function format (passed from UI)
        for key, value in env_vars.items():
            if key not in env_to_function_mapping.values() and value:
                current_value = param_vals.get(key, "")
                # Override if empty or doesn't exist
                if not current_value or current_value.strip() == "":
                    param_vals[key] = value
                    print(f"DEBUG: Direct mapping: {key}: {value[:20]}... (was: '{current_value}')")
        
        # Apply UI overrides - these ALWAYS take precedence over Function App settings
        for key, value in ui_overrides.items():
            if value:  # Only apply if value is not empty
                current_value = param_vals.get(key, "")
                param_vals[key] = value
                print(f"DEBUG: UI Override: {key}: {value[:20]}... (was: '{current_value}')")
        
        # Debug: Show final merged values
        print(f"DEBUG: Final merged settings count: {len(param_vals)}")
        print(f"DEBUG: Key presence check - SERVICE_NAME: {'SERVICE_NAME' in param_vals}, INDEX_NAME: {'INDEX_NAME' in param_vals}")
        print(f"DEBUG: Key presence check - OPENAI_DEPLOYMENT: {'OPENAI_DEPLOYMENT' in param_vals}, OPENAI_ENDPOINT: {'OPENAI_ENDPOINT' in param_vals}")
        
        REQUIRED_KEYS = [
            # Core function settings (managed identity)
            "SERVICE_NAME", "AGENT_NAME", "INDEX_NAME", 
            "OPENAI_ENDPOINT", "OPENAI_DEPLOYMENT", 
            "API_VERSION", "RERANKER_THRESHOLD", "MAX_OUTPUT_SIZE",
            
            # Optional function settings
            "includesrc", "debug", "TOP_K",
            
            # Azure Functions infrastructure
            "APPLICATIONINSIGHTS_CONNECTION_STRING", "AzureWebJobsStorage",
            "DEPLOYMENT_STORAGE_CONNECTION_STRING",
            
            # Optional legacy keys for fallback compatibility
            "OPENAI_KEY", "SEARCH_API_KEY",
            
            # Function-specific key
            "AGENT_FUNC_KEY"
        ]
        
        # Ensure all required keys exist (set empty if missing)
        for k in REQUIRED_KEYS:
            param_vals.setdefault(k, "")
        
        # Create DataFrame with ALL param_vals keys (prioritize required keys first)
        all_keys = list(REQUIRED_KEYS)
        
        # Add any additional keys from param_vals that aren't in REQUIRED_KEYS
        for key in sorted(param_vals.keys()):
            if key not in all_keys:
                all_keys.append(key)
        
        # Create rows for all keys
        rows = [{"key": k, "value": mask_sensitive_value(str(param_vals[k]))} for k in all_keys]
        df = pd.DataFrame(rows)
        
        print(f"DEBUG: Created DataFrame with {len(rows)} rows")
        print(f"DEBUG: Keys in DataFrame: {[row['key'] for row in rows[:10]]}")  # Show first 10
        
        # Debug: Show specific key values we care about
        for key in ['SERVICE_NAME', 'OPENAI_ENDPOINT', 'OPENAI_DEPLOYMENT', 'API_VERSION']:
            if key in param_vals:
                original_value = param_vals[key]
                masked_value = mask_sensitive_value(str(original_value))
                print(f"DEBUG: {key}: '{original_value}' -> masked: '{masked_value}'")
        
        return True, df, raw, ""
    except Exception as err:
        return False, None, {}, str(err)


def push_function_settings(
    resource_group: str,
    function_name: str,
    subscription_id: str,
    edited_df: pd.DataFrame,
    original_raw: Dict
) -> Tuple[bool, str]:
    """
    Push edited settings back to the Function App.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not all((subscription_id, resource_group, function_name)):
        return False, "Missing required parameters"
        
    if edited_df.empty:
        return False, "No settings to push"
        
    try:
        wcli = WebSiteManagementClient(AzureCliCredential(), subscription_id)
        
        # Build new property map – start with original raw to preserve hidden keys
        new_props = dict(original_raw)
        
        # Overwrite with rows from the edited table
        for _, row in edited_df.iterrows():
            k = str(row["key"]).strip()
            v = str(row["value"]).strip()
            # If the cell still shows masked dots, keep original
            if v == "••••••" and k in original_raw:
                continue
            new_props[k] = v
        
        # Ensure required settings are present for managed identity
        required_for_function = {
            "SERVICE_NAME": "",
            "AGENT_NAME": "",
            "OPENAI_ENDPOINT": "",
            "OPENAI_DEPLOYMENT": "",
            "API_VERSION": "2025-05-01-preview",
            "INDEX_NAME": "",
            "RERANKER_THRESHOLD": "2.0",
            "MAX_OUTPUT_SIZE": "16000",
            "includesrc": "true",
            "debug": "false"
        }
        
        # Add any missing required settings with defaults
        for key, default_value in required_for_function.items():
            if key not in new_props:
                new_props[key] = default_value
            
        # Update in Azure
        wcli.web_apps.update_application_settings(
            resource_group,
            function_name,
            {"properties": new_props}
        )
        
        return True, f"Updated {len(new_props)} settings"
    except Exception as err:
        return False, f"Failed to update: {err}"


def zip_function_folder(func_dir: Path, zip_path: Path) -> None:
    """Zip the function folder for deployment, respecting .funcignore."""
    
    # Read .funcignore patterns
    funcignore_path = func_dir / ".funcignore"
    ignore_patterns = []
    if funcignore_path.exists():
        with open(funcignore_path, 'r') as f:
            ignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"DEBUG: .funcignore patterns: {ignore_patterns}")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in func_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(func_dir)
                relative_str = str(relative_path).replace('\\', '/')  # Normalize path separators
                
                # Check if file should be ignored
                should_ignore = False
                for pattern in ignore_patterns:
                    if pattern.endswith('/'):
                        # Directory pattern
                        if relative_str.startswith(pattern) or f"/{pattern}" in f"/{relative_str}":
                            should_ignore = True
                            break
                    else:
                        # File pattern
                        if relative_str == pattern or relative_str.endswith(pattern):
                            should_ignore = True
                            break
                
                if not should_ignore:
                    zf.write(item, relative_path)
                    print(f"DEBUG: Added to ZIP: {relative_path}")
                else:
                    print(f"DEBUG: Ignored: {relative_path}")
    
    # Debug: List ZIP contents to verify structure
    print(f"DEBUG: ZIP file created at: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zip_contents = zf.namelist()
        print(f"DEBUG: ZIP contains {len(zip_contents)} files:")
        for name in sorted(zip_contents):
            print(f"DEBUG:   {name}")
        
        # Check specifically for host.json at root
        if "host.json" in zip_contents:
            print("DEBUG: ✅ host.json found at root level")
        else:
            print("DEBUG: ❌ host.json NOT found at root level")
            root_files = [name for name in zip_contents if "/" not in name]
            print(f"DEBUG: Root level files: {root_files}")


def deploy_function_code(
    resource_group: str,
    function_name: str,
    subscription_id: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Deploy local ./function code to the Function App.
    
    Returns:
        Tuple of (success: bool, message: str, stdout: Optional[str])
    """
    if not all((subscription_id, resource_group, function_name)):
        return False, "Missing required parameters", None
        
    func_dir = Path.cwd() / "function"
    if not func_dir.exists():
        return False, f"Local 'function' folder not found: {func_dir}", None
        
    try:
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "function.zip"
            zip_function_folder(func_dir, zip_path)
            
            # First, try normal deployment
            cmd = [
                "az", "functionapp", "deployment", "source", "config-zip",
                "-g", resource_group,
                "-n", function_name,
                "--src", str(zip_path)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)  # 5 minutes for deployment
                return True, "Deployment completed", result.stdout.strip()
            except subprocess.CalledProcessError as cerr:
                error_msg = cerr.stderr.lower()
                
                # Check if it's an SSL certificate error
                if any(ssl_term in error_msg for ssl_term in ['ssl', 'certificate', 'tls', 'hostname']):
                    print("⚠️ SSL certificate error detected, attempting deployment with bypass...")
                    
                    # Try with Azure CLI configuration to handle SSL issues
                    # Set environment variables to bypass SSL verification if needed
                    env = os.environ.copy()
                    env['AZURE_CLI_DISABLE_CONNECTION_VERIFICATION'] = '1'
                    env['PYTHONHTTPSVERIFY'] = '0'
                    
                    # Retry with modified environment
                    try:
                        result_retry = subprocess.run(
                            cmd, 
                            capture_output=True, 
                            text=True, 
                            check=True, 
                            timeout=300,
                            env=env
                        )
                        return True, "Deployment completed (SSL bypass)", result_retry.stdout.strip()
                    except subprocess.CalledProcessError as cerr2:
                        # If still failing, try alternative deployment method
                        return _try_alternative_deployment(resource_group, function_name, zip_path)
                else:
                    # Not an SSL error, return original error
                    return False, f"az CLI deployment failed: {cerr.stderr}", None
            
    except subprocess.TimeoutExpired:
        return False, "Deployment timed out after 5 minutes", None
    except Exception as ex:
        return False, f"Failed to deploy: {ex}", None


def _try_alternative_deployment(
    resource_group: str,
    function_name: str,
    zip_path: Path
) -> Tuple[bool, str, Optional[str]]:
    """
    Alternative deployment method using REST API approach.
    """
    try:
        # Try using the REST API approach with requests (if available)
        # First, get the publishing credentials
        cred_cmd = [
            "az", "functionapp", "deployment", "list-publishing-profiles",
            "-g", resource_group,
            "-n", function_name,
            "--xml"
        ]
        
        cred_result = subprocess.run(cred_cmd, capture_output=True, text=True, check=True)
        
        # For now, return a more informative error message
        return False, (
            "SSL certificate verification failed. This often happens in private network setups. "
            "Possible solutions:\n"
            "1. Configure your network/proxy to use proper certificates\n"
            "2. Deploy using Azure Portal or Visual Studio Code\n"
            "3. Contact your network administrator about certificate trust\n"
            f"Original error: Certificate hostname mismatch"
        ), None
        
    except Exception as ex:
        return False, f"Alternative deployment also failed: {ex}", None


def assign_search_rbac_roles(
    subscription_id: str,
    function_app_name: str,
    resource_group: str,
    search_service_name: str
) -> Tuple[bool, str]:
    """
    Assign required RBAC roles to Function App managed identity for Azure AI Search access.
    
    Args:
        subscription_id: Azure subscription ID
        function_app_name: Name of the Function App
        resource_group: Resource group name
        search_service_name: Name of the Azure AI Search service
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Step 1: Enable managed identity if not already enabled
        enable_identity_cmd = [
            "az", "functionapp", "identity", "assign",
            "--name", function_app_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id
        ]
        
        identity_result = subprocess.run(
            enable_identity_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if identity_result.returncode != 0:
            return False, f"Failed to enable managed identity: {identity_result.stderr}"
        
        # Step 2: Get the principal ID of the Function App
        get_principal_cmd = [
            "az", "functionapp", "identity", "show",
            "--name", function_app_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id,
            "--query", "principalId",
            "-o", "tsv"
        ]
        
        principal_result = subprocess.run(
            get_principal_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if principal_result.returncode != 0:
            return False, f"Failed to get principal ID: {principal_result.stderr}"
        
        principal_id = principal_result.stdout.strip()
        if not principal_id:
            return False, "Could not retrieve Function App principal ID"
        
        # Step 3: Get the Azure AI Search service resource ID
        get_search_id_cmd = [
            "az", "search", "service", "show",
            "--name", search_service_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id,
            "--query", "id",
            "-o", "tsv"
        ]
        
        search_result = subprocess.run(
            get_search_id_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if search_result.returncode != 0:
            return False, f"Failed to get Azure AI Search service ID: {search_result.stderr}"
        
        search_resource_id = search_result.stdout.strip()
        if not search_resource_id:
            return False, f"Could not find Azure AI Search service: {search_service_name}"
        
        # Step 4: Assign Search Index Data Contributor role
        assign_index_role_cmd = [
            "az", "role", "assignment", "create",
            "--assignee", principal_id,
            "--role", "Search Index Data Contributor",
            "--scope", search_resource_id,
            "--subscription", subscription_id
        ]
        
        index_role_result = subprocess.run(
            assign_index_role_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        # Step 5: Assign Search Service Contributor role
        assign_service_role_cmd = [
            "az", "role", "assignment", "create",
            "--assignee", principal_id,
            "--role", "Search Service Contributor",
            "--scope", search_resource_id,
            "--subscription", subscription_id
        ]
        
        service_role_result = subprocess.run(
            assign_service_role_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        # Check results
        roles_assigned = []
        errors = []
        
        if index_role_result.returncode == 0:
            roles_assigned.append("Search Index Data Contributor")
        else:
            # Check if role already exists (this is not necessarily an error)
            if "already exists" in index_role_result.stderr.lower():
                roles_assigned.append("Search Index Data Contributor (already assigned)")
            else:
                errors.append(f"Index role assignment failed: {index_role_result.stderr}")
        
        if service_role_result.returncode == 0:
            roles_assigned.append("Search Service Contributor")
        else:
            # Check if role already exists (this is not necessarily an error)
            if "already exists" in service_role_result.stderr.lower():
                roles_assigned.append("Search Service Contributor (already assigned)")
            else:
                errors.append(f"Service role assignment failed: {service_role_result.stderr}")
        
        if roles_assigned and not errors:
            return True, f"Successfully assigned RBAC roles: {', '.join(roles_assigned)}"
        elif roles_assigned and errors:
            return True, f"Partially successful - Assigned: {', '.join(roles_assigned)}. Errors: {'; '.join(errors)}"
        else:
            return False, f"Failed to assign roles: {'; '.join(errors)}"
            
    except subprocess.TimeoutExpired:
        return False, "Operation timed out. Please try again or assign roles manually."
    except Exception as ex:
        return False, f"Unexpected error during RBAC assignment: {ex}"


def assign_openai_rbac_roles(
    subscription_id: str,
    function_app_name: str,
    resource_group: str,
    openai_service_name: str,
    openai_resource_group: str = None
) -> Tuple[bool, str]:
    """
    Assign required RBAC roles to Function App managed identity for Azure OpenAI access.
    
    Args:
        subscription_id: Azure subscription ID
        function_app_name: Name of the Function App
        resource_group: Function App resource group name
        openai_service_name: Name of the Azure OpenAI service
        openai_resource_group: OpenAI service resource group (defaults to function_app resource_group)
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if openai_resource_group is None:
        openai_resource_group = resource_group
        
    try:
        # Step 1: Enable managed identity if not already enabled
        enable_identity_cmd = [
            "az", "functionapp", "identity", "assign",
            "--name", function_app_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id
        ]
        
        identity_result = subprocess.run(
            enable_identity_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if identity_result.returncode != 0:
            return False, f"Failed to enable managed identity: {identity_result.stderr}"
        
        # Step 2: Get the principal ID of the Function App
        get_principal_cmd = [
            "az", "functionapp", "identity", "show",
            "--name", function_app_name,
            "--resource-group", resource_group,
            "--subscription", subscription_id,
            "--query", "principalId",
            "-o", "tsv"
        ]
        
        principal_result = subprocess.run(
            get_principal_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if principal_result.returncode != 0:
            return False, f"Failed to get principal ID: {principal_result.stderr}"
        
        principal_id = principal_result.stdout.strip()
        if not principal_id:
            return False, "Could not retrieve Function App principal ID"
        
        # Step 3: Get the Azure OpenAI service resource ID
        get_openai_id_cmd = [
            "az", "cognitiveservices", "account", "show",
            "--name", openai_service_name,
            "--resource-group", openai_resource_group,
            "--subscription", subscription_id,
            "--query", "id",
            "-o", "tsv"
        ]
        
        openai_result = subprocess.run(
            get_openai_id_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if openai_result.returncode != 0:
            return False, f"Failed to get Azure OpenAI service ID: {openai_result.stderr}"
        
        openai_resource_id = openai_result.stdout.strip()
        if not openai_resource_id:
            return False, f"Could not find Azure OpenAI service: {openai_service_name}"
        
        # Step 4: Assign Cognitive Services OpenAI User role
        assign_openai_role_cmd = [
            "az", "role", "assignment", "create",
            "--assignee", principal_id,
            "--role", "Cognitive Services OpenAI User",
            "--scope", openai_resource_id,
            "--subscription", subscription_id
        ]
        
        openai_role_result = subprocess.run(
            assign_openai_role_cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        # Check results
        roles_assigned = []
        errors = []
        
        if openai_role_result.returncode == 0:
            roles_assigned.append("Cognitive Services OpenAI User")
        else:
            # Check if role already exists (this is not necessarily an error)
            if "already exists" in openai_role_result.stderr.lower():
                roles_assigned.append("Cognitive Services OpenAI User (already assigned)")
            else:
                errors.append(f"OpenAI role assignment failed: {openai_role_result.stderr}")
        
        if roles_assigned and not errors:
            return True, f"Successfully assigned Azure OpenAI RBAC role: {', '.join(roles_assigned)}"
        elif roles_assigned and errors:
            return True, f"Partially successful - Assigned: {', '.join(roles_assigned)}. Errors: {'; '.join(errors)}"
        else:
            return False, f"Failed to assign Azure OpenAI role: {'; '.join(errors)}"
            
    except subprocess.TimeoutExpired:
        return False, "Operation timed out. Please try again or assign roles manually."
    except Exception as ex:
        return False, f"Unexpected error during Azure OpenAI RBAC assignment: {ex}"


def assign_all_rbac_roles(
    subscription_id: str,
    function_app_name: str,
    resource_group: str,
    search_service_name: str,
    openai_service_name: str,
    openai_resource_group: str = None
) -> Tuple[bool, str]:
    """
    Assign all required RBAC roles for both Azure AI Search and Azure OpenAI.
    
    Args:
        subscription_id: Azure subscription ID
        function_app_name: Name of the Function App
        resource_group: Function App resource group name
        search_service_name: Name of the Azure AI Search service
        openai_service_name: Name of the Azure OpenAI service  
        openai_resource_group: OpenAI service resource group (defaults to function_app resource_group)
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    messages = []
    overall_success = True
    
    # Assign Azure AI Search roles
    search_success, search_message = assign_search_rbac_roles(
        subscription_id=subscription_id,
        function_app_name=function_app_name,
        resource_group=resource_group,
        search_service_name=search_service_name
    )
    
    messages.append(f"🔍 Azure AI Search: {search_message}")
    if not search_success:
        overall_success = False
    
    # Assign Azure OpenAI roles
    openai_success, openai_message = assign_openai_rbac_roles(
        subscription_id=subscription_id,
        function_app_name=function_app_name,
        resource_group=resource_group,
        openai_service_name=openai_service_name,
        openai_resource_group=openai_resource_group
    )
    
    messages.append(f"🤖 Azure OpenAI: {openai_message}")
    if not openai_success:
        overall_success = False
    
    combined_message = "\n".join(messages)
    
    if overall_success:
        return True, f"✅ Successfully configured all RBAC roles:\n{combined_message}"
    else:
        return False, f"⚠️ Partial success or failure:\n{combined_message}"


def get_function_url_and_key(
    subscription_id: str,
    resource_group: str,
    function_app_name: str,
    function_name: str = "AgentFunction"
) -> Tuple[bool, str, str, str]:
    """
    Get the actual Function URL and key from Azure.
    
    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        function_app_name: Function App name
        function_name: Function name (default: "AgentFunction")
    
    Returns:
        Tuple of (success: bool, function_url: str, function_key: str, error_msg: str)
    """
    if not all((subscription_id, resource_group, function_app_name)):
        return False, "", "", "Missing required parameters"
    
    try:
        wcli = WebSiteManagementClient(AzureCliCredential(), subscription_id)
        
        # Step 1: Get the Function App details to get the correct hostname
        try:
            site = wcli.web_apps.get(resource_group, function_app_name)
            if not site:
                return False, "", "", f"Function App {function_app_name} not found"
            
            # Get the actual hostname from Azure
            hostname = getattr(site, 'default_host_name', f"{function_app_name}.azurewebsites.net")
            print(f"DEBUG: Found Function App hostname: {hostname}")
            
        except Exception as e:
            print(f"DEBUG: Failed to get Function App details: {e}")
            # Fallback to simple hostname
            hostname = f"{function_app_name}.azurewebsites.net"
        
        # Step 2: Try to get function keys using Azure CLI (more reliable)
        function_key = ""
        try:
            # Get function keys using Azure CLI
            get_keys_cmd = [
                "az", "functionapp", "function", "keys", "list",
                "--function-name", function_name,
                "--name", function_app_name,
                "--resource-group", resource_group,
                "--subscription", subscription_id,
                "--query", "default",
                "-o", "tsv"
            ]
            
            keys_result = subprocess.run(
                get_keys_cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if keys_result.returncode == 0 and keys_result.stdout.strip():
                function_key = keys_result.stdout.strip()
                print(f"DEBUG: Retrieved function key from Azure CLI")
            else:
                print(f"DEBUG: Failed to get function key via Azure CLI: {keys_result.stderr}")
                
        except Exception as e:
            print(f"DEBUG: Azure CLI function key retrieval failed: {e}")
        
        # Step 3: If Azure CLI failed, try using Management API
        if not function_key:
            try:
                # Try to get function keys via Management API
                # Note: This requires elevated permissions
                function_keys = wcli.web_apps.list_function_keys(
                    resource_group, function_app_name, function_name
                )
                if function_keys and hasattr(function_keys, 'default'):
                    function_key = function_keys.default
                    print(f"DEBUG: Retrieved function key from Management API")
                    
            except Exception as e:
                print(f"DEBUG: Management API function key retrieval failed: {e}")
        
        # Step 4: Build the function URL
        function_url = f"https://{hostname}/api/{function_name}"
        
        return True, function_url, function_key, ""
        
    except Exception as ex:
        return False, "", "", f"Failed to get function details: {ex}"


def generate_test_function_url(
    subscription_id: str,
    resource_group: str,
    function_app_name: str,
    test_message: str,
    function_name: str = "AgentFunction",
    fallback_function_key: str = ""
) -> Tuple[bool, str, str]:
    """
    Generate a complete test URL for the Azure Function with proper hostname and function key.
    
    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        function_app_name: Function App name
        test_message: Message to encode in the URL
        function_name: Function name (default: "AgentFunction")
        fallback_function_key: Function key from .env file as fallback
    
    Returns:
        Tuple of (success: bool, test_url: str, error_msg: str)
    """
    import urllib.parse
    
    # Get the actual function URL and key from Azure
    success, function_url, function_key, error_msg = get_function_url_and_key(
        subscription_id, resource_group, function_app_name, function_name
    )
    
    if not success:
        return False, "", f"Failed to get function details: {error_msg}"
    
    # Use Azure-retrieved key, or fallback to provided key
    if not function_key and fallback_function_key:
        function_key = fallback_function_key
        print(f"DEBUG: Using fallback function key from .env")
    elif function_key:
        print(f"DEBUG: Using function key retrieved from Azure")
    else:
        print(f"DEBUG: No function key available - URL may not work without authentication")
    
    # Encode the test message for URL
    encoded_message = urllib.parse.quote(test_message, safe="")
    
    # Build the complete URL
    test_url = f"{function_url}/{encoded_message}"
    
    # Add query parameters
    query_params = []
    
    # Add function key if available
    if function_key:
        query_params.append(f"code={function_key}")
    
    # Always add includesrc=true
    query_params.append("includesrc=true")
    
    # Combine query parameters
    if query_params:
        test_url += "?" + "&".join(query_params)
    
    return True, test_url, ""
