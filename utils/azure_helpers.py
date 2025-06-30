"""Azure-specific helper functions extracted from main app"""
import os
import subprocess
import json
import httpx
import streamlit as st
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

def get_search_credential():
    """
    Return Azure credential based on env:
    • If AZURE_SEARCH_KEY is set → key auth
    • else → DefaultAzureCredential (AAD)
    """
    key = os.getenv("AZURE_SEARCH_KEY", "").strip()
    if key:
        return AzureKeyCredential(key)
    return DefaultAzureCredential()

def rbac_enabled(service_url: str) -> bool:
    """
    Quick probe: return True if Role‑based access control is enabled on the
    Search service (Authentication mode = RBAC).
    """
    try:
        url = f"{service_url.rstrip('/')}/?api-version=2023-11-01"
        r = httpx.get(url, timeout=3)
        # When RBAC is ON the payload includes "RoleBasedAccessControl"
        return "RoleBasedAccessControl" in r.text
    except Exception:
        return False

def get_az_logged_user() -> tuple[str | None, str | None]:
    """Return (UPN/email, subscription-id) of the signed‑in az cli user, or (None,None)."""
    try:
        out = subprocess.check_output(
            ["az", "account", "show", "--output", "json"], text=True, timeout=10
        )
        data = json.loads(out)
        return data["user"]["name"], data["id"]
    except Exception:
        return None, None

def grant_search_role(service_name: str, subscription_id: str, resource_group: str, principal: str, role: str) -> tuple[bool, str]:
    """
    Grant the specified *role* to *principal* on the given service.
    Returns (success, message).
    """
    try:
        scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Search/searchServices/{service_name}"
        subprocess.check_call(
            [
                "az", "role", "assignment", "create",
                "--role", role,
                "--assignee", principal,
                "--scope", scope
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        return True, "Role granted successfully"
    except subprocess.CalledProcessError as e:
        return False, f"az cli error: {e}"
    except Exception as ex:
        return False, str(ex)

def grant_openai_role(account_name: str, subscription_id: str, resource_group: str,
                      principal: str, role: str = "Cognitive Services OpenAI User") -> tuple[bool, str]:
    """
    Grant *role* (default: Cognitive Services OpenAI User) on the Azure OpenAI
    account to *principal*.
    """
    try:
        scope = (
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
        )
        subprocess.check_call(
            [
                "az", "role", "assignment", "create",
                "--role", role,
                "--assignee", principal,
                "--scope", scope,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        return True, "Role granted successfully"
    except subprocess.CalledProcessError as e:
        return False, f"az cli error: {e}"
    except Exception as ex:
        return False, str(ex)

def reload_env_and_restart():
    """
    Reload the .env file (override existing variables), clear cached clients,
    and rerun the Streamlit script so the new values take effect.
    """
    # Import here to avoid circular import
    try:
        from core.azure_clients import init_openai, init_search_client, init_agent_client
        
        env_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(env_path, override=True)

        # Clear Streamlit caches for resource‑building functions
        for fn in (init_openai, init_search_client, init_agent_client):
            if hasattr(fn, "clear"):
                fn.clear()

        st.toast("✅ .env reloaded – restarting app…", icon="🔄")
        if hasattr(st, "rerun"):
            st.rerun()
        else:  # fallback for older versions
            st.experimental_rerun()
    except ImportError:
        # Fallback during initial setup
        st.error("Please restart the app manually")

def env(var: str) -> str:
    """Fetch env var or exit with error."""
    v = os.getenv(var)
    if not v:
        import sys
        sys.exit(f"❌ Missing env var: {var}")
    return v
