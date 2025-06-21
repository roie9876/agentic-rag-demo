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
            timeout=10
        )
        data = json.loads(out)
        return data.get("id", "")
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        # Return empty string if Azure CLI fails, times out, or is not available
        return ""


def list_function_apps(subscription_id: str) -> Tuple[List[str], Dict[str, Tuple[str, str]]]:
    """
    List all Function Apps in the subscription.
    
    Returns:
        Tuple of (func_choices: List[str], func_map: Dict[str, Tuple[str, str]])
        where func_map maps "app (rg)" -> (name, resource_group)
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
                func_map[label] = (site.name, site.resource_group)
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
        
        # Merge precedence: Function settings ← .env values (1‑to‑1)
        param_vals = raw.copy()
        param_vals.update(env_vars)
        
        REQUIRED_KEYS = [
            "AGENT_FUNC_KEY", "AGENT_NAME", "API_VERSION",
            "APPLICATIONINSIGHTS_CONNECTION_STRING",
            "AZURE_OPENAI_API_VERSION", "AzureWebJobsStorage", "debug",
            "DEPLOYMENT_STORAGE_CONNECTION_STRING", "includesrc",
            "INDEX_NAME", "MAX_OUTPUT_SIZE",
            "OPENAI_DEPLOYMENT", "OPENAI_ENDPOINT", "OPENAI_KEY",
            "RERANKER_THRESHOLD", "SEARCH_API_KEY",
            "SERVICE_NAME"
        ]
        
        for k in REQUIRED_KEYS:
            param_vals.setdefault(k, "")
            
        rows = [{"key": k, "value": mask_sensitive_value(str(param_vals[k]))} for k in REQUIRED_KEYS]
        df = pd.DataFrame(rows)
        
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
            if v == "••••••" and k in new_props:
                continue
            new_props[k] = v
            
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
    """Zip the function folder for deployment."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in func_dir.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(func_dir))


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
    except Exception as ex:
        return False, f"Failed to deploy: {ex}", None
