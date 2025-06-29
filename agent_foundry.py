"""
AI Foundry Agent Helper Module
-----------------------------
Contains functionality for creating and managing AI Foundry agents.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional, Union

from azure.identity import AzureCliCredential, DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Support multiple SDK generations where the tool classes moved packages/names
try:
    # GA / recent preview: everything under azure.ai.agents
    from azure.ai.agents import FunctionTool, FunctionDefinition
except ImportError:
    # Older builds may expose FunctionTool and/or FunctionDefinition
    # under azure.ai.agents.models
    try:
        from azure.ai.agents import FunctionTool  # type: ignore
    except ImportError:
        FunctionTool = None  # type: ignore
    try:
        from azure.ai.agents.models import FunctionTool as _FTModel, FunctionDefinition  # type: ignore
        if FunctionTool is None:  # fallback when only the models version exists
            FunctionTool = _FTModel  # type: ignore
    except ImportError:
        FunctionDefinition = None  # type: ignore

# OpenAPI tool helper (available in azure‑ai‑agents ≥ 1.0.0b2)
from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails

def check_azure_cli_login() -> Tuple[bool, Union[Dict, None]]:
    """
    Return (logged_in, account_json_or_None) by running `az account show`.
    """
    try:
        out = subprocess.check_output(
            ["az", "account", "show", "--output", "json"],
            text=True,
            timeout=10,  # Increased timeout to 10 seconds
        )
        return True, json.loads(out)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False, None
    except Exception:
        return False, None


def check_and_install_ai_extension() -> bool:
    """Check if Azure AI CLI extension is installed and install if needed."""
    try:
        # Check if extension is already installed
        out = subprocess.check_output(
            ["az", "extension", "list", "--output", "json"], 
            text=True,
            timeout=10  # Increased timeout to 10 seconds
        )
        extensions = json.loads(out)
        
        # Look for AI extension
        for ext in extensions:
            if ext.get("name") == "ai":
                return True
                
        # If not found, install it
        import logging
        logging.info("Azure AI CLI extension not found, installing...")
        subprocess.check_call(
            ["az", "extension", "add", "--name", "ai", "--yes"],
            timeout=30
        )
        logging.info("Azure AI CLI extension installed successfully")
        return True
    except Exception as err:
        import logging
        logging.warning(f"Failed to check/install Azure AI CLI extension: {err}")
        return False

def get_ai_foundry_projects(cred: AzureCliCredential) -> List[Dict]:
    """
    Return a list of Foundry projects visible to the signed‑in CLI user via
    `az ai project list`. Each item includes:
        {name, location, endpoint, resource_group, hub_name}
    """
    projects = []
    
    # First try to get projects from environment variable as a fallback
    if os.getenv("PROJECT_ENDPOINT"):
        ep = os.getenv("PROJECT_ENDPOINT").strip()
        projects.append({
            "name": ep.split('/')[-1][:30] or "env-project",
            "location": "env",
            "endpoint": ep,
            "resource_group": "env",
            "hub_name": "env",
        })
        return projects
    
    # Ensure AI extension is installed
    check_and_install_ai_extension()
    
    # Then try Azure CLI
    try:
        out = subprocess.check_output(
            ["az", "ai", "project", "list", "--output", "json"],
            text=True,
            timeout=15,  # Increased timeout to 15 seconds for project listing
        )
        data = json.loads(out)
        
        # Check if we got any projects
        if not data:
            import logging
            logging.warning("No AI Foundry projects returned from az ai project list")
            return projects
            
        for p in data:
            # Ensure we have all required fields with proper error handling
            try:
                projects.append({
                    "name": p["name"],
                    "location": p.get("location", "unknown"),
                    "endpoint": p["properties"]["endpoint"],
                    "resource_group": p.get("resourceGroup", "unknown"),
                    "hub_name": p["properties"].get("hubName", ""),
                })
            except KeyError as key_err:
                import logging
                logging.warning(f"Missing key in project data: {key_err} - Skipping project")
                continue
                
        return projects
    except subprocess.CalledProcessError as e:
        import logging
        logging.warning(f"Azure CLI error when listing projects: {e.stderr if hasattr(e, 'stderr') else str(e)}")
        return projects
    except json.JSONDecodeError:
        import logging
        logging.warning("Invalid JSON returned from az ai project list")
        return projects
    except Exception as err:
        import logging
        logging.warning(f"Failed to list AI Foundry projects: {str(err)}")
        return projects

def create_openapi_tool(tool_name: str, base_url: str, function_key: str) -> OpenApiTool:
    """Create an OpenAPI tool definition for the Azure Function."""
    tool_schema = {
        "openapi": "3.0.1",
        "info": {
            "title": "AgentFunction",
            "version": "1.0.0"
        },
        # Base URL for the Function App (no query‑string here!)
        "servers": [
            {
                "url": base_url
            }
        ],
        "paths": {
            "/AgentFunction/{question}": {
                "post": {
                    "operationId": "askAgentFunction",
                    "summary": "Ask the Azure Function",
                    "parameters": [
                        {
                            "name": "question",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "code",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "default": function_key
                            },
                            "description": "Function host key (taken from env‑var AGENT_FUNC_KEY)"
                        },
                        {
                            "name": "includesrc",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "boolean",
                                "default": True
                            },
                            "description": "Include sources in the Function response"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Plain‑text answer",
                            "content": {
                                "text/plain": {
                                    "schema": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    auth = OpenApiAnonymousAuthDetails()  # public endpoint – no key required
    return OpenApiTool(
        name=tool_name,
        spec=tool_schema,
        description="Invoke the Azure Function via HTTP POST",
        auth=auth,
    )


def get_agent_system_message(base_url: str, function_key: str) -> str:
    """Generate the system message for the agent."""
    return (
        "You have one action called Test_askAgentFunction.\n"
        "Call it **every time** the user asks a factual question.\n"
        "Send the whole question unchanged as the {question} path parameter **and** include the two query parameters exactly as shown below:\n"
        f"  • code={function_key}\n"
        "  • includesrc=true\n"
        "Example URL you must generate (line breaks added for clarity):\n"
        f"POST {base_url}/AgentFunction/{{question}}?code={function_key}&includesrc=true\n"
        "Return the Function's plain‑text response **verbatim and in full**, including any inline citations such as [my_document.pdf].\n"
        "Do **NOT** add, remove, reorder, or paraphrase content, and do **NOT** drop those citation markers.\n"
        "If the action fails, reply exactly with: I don't know\n"
        "Do **NOT** answer from your own internal knowledge and do **NOT** answer questions unrelated to the Function.\n"
        "\n"
        "### How to respond\n"
        "1. Parse the JSON the Function returns.\n"
        '2. Reply with the **exact value of "answer"** – do NOT change it.\n'
        '3. After that, print a short "Sources:" list. For each object in "sources" show its **source_file**, and – if "url" is present and not empty – append " – <url>". If source_file is empty, show the url instead; if both are missing, use the placeholder doc#.\n'
        "   Example:\n"
        "   Sources:\n"
        "   • המב 50.02.pdf\n"
        "   • מס 40.021.pdf\n"
    )


def create_ai_foundry_agent(
    project_endpoint: str, 
    agent_name: str, 
    base_url: str, 
    function_key: str
) -> Tuple[bool, str, Any]:
    """
    Create an AI Foundry agent that connects to the specified Azure Function.
    
    Returns:
        Tuple of (success: bool, message: str, agent: Optional[Any])
    """
    try:
        TOOL_NAME = "Test_askAgentFunction"
        openapi_tool = create_openapi_tool(TOOL_NAME, base_url, function_key)
        system_message = get_agent_system_message(base_url, function_key)
        
        proj_client = AIProjectClient(project_endpoint, DefaultAzureCredential())
        with proj_client:
            agent = proj_client.agents.create_agent(
                name=agent_name,
                model="gpt-4.1",  # make sure this deployment exists
                instructions=system_message,
                description="Assistant created from Streamlit UI",
                tools=openapi_tool.definitions,  # <-- note: *definitions*
            )
        return True, f"Agent {agent_name} created successfully (ID: {agent.id})", agent
    except Exception as err:
        return False, f"Failed to create agent: {str(err)}", None
