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

from azure.identity import DefaultAzureCredential
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
        wcli = WebSiteManagementClient(DefaultAzureCredential(), subscription_id)
        for site in wcli.web_apps.list():
            # Filter only Function Apps (kind contains "functionapp")
            if site.kind and "functionapp" in site.kind:
                label = f"{site.name}  ({site.resource_group})"
                func_choices.append(label)
                # Include the actual hostname/domain from Azure
                hostname = getattr(site, 'default_host_name', f"{site.name}.azurewebsites.net")
                func_map[label] = (site.name, site.resource_group, hostname)
    except Exception:
        pass  # Silently fail, UI will show warning
        
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
    env_vars: Dict[str, str]
) -> Tuple[bool, Optional[pd.DataFrame], Dict, str]:
    """
    Load Function App settings and merge with .env values.
    
    Returns:
        Tuple of (success: bool, dataframe: Optional[pd.DataFrame], raw_settings: Dict, error_msg: str)
    """
    if not all((subscription_id, resource_group, function_name)):
        return False, None, {}, "Missing required parameters"
        
    try:
        wcli = WebSiteManagementClient(DefaultAzureCredential(), subscription_id)
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
                if func_key == "SERVICE_NAME" and env_vars[env_key]:
                    # Extract service name from AZURE_SEARCH_ENDPOINT
                    import re
                    match = re.search(r'https://([^.]+)\.search\.windows\.net', env_vars[env_key])
                    if match:
                        param_vals[func_key] = match.group(1)
                        print(f"DEBUG: Mapped {env_key} -> {func_key}: {match.group(1)}")
                else:
                    # Update if:
                    # 1. Key doesn't exist in function app
                    # 2. Key exists but is empty/None in function app
                    # 3. This is a _41 variant (preferred)
                    current_value = param_vals.get(func_key, "")
                    should_update = (
                        func_key not in param_vals or 
                        not current_value or 
                        current_value.strip() == "" or
                        env_key.endswith('_41')
                    )
                    
                    if should_update:
                        param_vals[func_key] = env_vars[env_key]
                        print(f"DEBUG: Mapped {env_key} -> {func_key}: {env_vars[env_key][:20]}... (was: '{current_value}')")
        
        # Apply direct env_vars that are already in function format (passed from UI)
        for key, value in env_vars.items():
            if key not in env_to_function_mapping.values() and value:
                current_value = param_vals.get(key, "")
                # Override if empty or doesn't exist
                if not current_value or current_value.strip() == "":
                    param_vals[key] = value
                    print(f"DEBUG: Direct mapping: {key}: {value[:20]}... (was: '{current_value}')")
        
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
        wcli = WebSiteManagementClient(DefaultAzureCredential(), subscription_id)
        
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
            
            cmd = [
                "az", "functionapp", "deployment", "source", "config-zip",
                "-g", resource_group,
                "-n", function_name,
                "--src", str(zip_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)  # 5 minutes for deployment
            return True, "Deployment completed", result.stdout.strip()
            
    except subprocess.TimeoutExpired:
        return False, "Deployment timed out after 5 minutes", None
    except subprocess.CalledProcessError as cerr:
        return False, f"az CLI deployment failed: {cerr.stderr}", None
    except subprocess.TimeoutExpired:
        return False, "Deployment timed out after 5 minutes", None
    except Exception as ex:
        return False, f"Failed to deploy: {ex}", None
