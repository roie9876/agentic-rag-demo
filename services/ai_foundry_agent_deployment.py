#!/usr/bin/env python3
"""
AI Foundry Agent Deployment Service
Handles deployment and management of AI agents to AI Foundry projects using Azure AI SDK.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from azure.identity import DefaultAzureCredential
from datetime import datetime

# Azure AI SDK imports for AI Foundry Projects
try:
    from azure.ai.projects import AIProjectClient
    # Import OpenAPI tool support for more advanced agent configurations
    from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails
    OPENAPI_TOOLS_AVAILABLE = True
    AI_SDK_AVAILABLE = True
except ImportError as e:
    try:
        # Fallback - try just the basic AIProjectClient
        from azure.ai.projects import AIProjectClient
        OPENAPI_TOOLS_AVAILABLE = False
        AI_SDK_AVAILABLE = True
        logging.warning(f"OpenAPI tools not available, using basic function tools: {e}")
    except ImportError as e2:
        OPENAPI_TOOLS_AVAILABLE = False
        AI_SDK_AVAILABLE = False
        logging.warning(f"Azure AI SDK not available: {e2}")

logger = logging.getLogger(__name__)

class AIFoundryAgentDeploymentService:
    """Service for deploying and managing AI agents in AI Foundry projects using Azure AI SDK."""
    
    def __init__(self):
        """Initialize the AI Foundry Agent Deployment Service."""
        # Use lazy initialization for Azure credentials to avoid slow startup
        self._credential = None
        self._project_client = None
        self._project_endpoint = None
    
    @property
    def credential(self):
        """Lazy initialization of Azure credentials."""
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential
    
    def set_project_endpoint(self, project_endpoint: str) -> None:
        """Set the project endpoint and initialize the AI Project client."""
        self._project_endpoint = project_endpoint
        # Reset client to force re-initialization with new endpoint
        self._project_client = None
    
    @property
    def project_client(self) -> Optional[AIProjectClient]:
        """Lazy initialization of AI Project client."""
        if not AI_SDK_AVAILABLE:
            logger.error("Azure AI SDK is not available. Please install azure-ai-projects package.")
            return None
            
        if self._project_client is None and self._project_endpoint:
            try:
                self._project_client = AIProjectClient(
                    endpoint=self._project_endpoint,
                    credential=self.credential
                )
                logger.info(f"✅ Initialized AI Project client for endpoint: {self._project_endpoint}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AI Project client: {e}")
                return None
        return self._project_client
    
    def create_openapi_tool(self, tool_name: str, base_url: str, function_key: str) -> 'OpenApiTool':
        """Create an OpenAPI tool definition for the Azure Function using advanced schema."""
        if not OPENAPI_TOOLS_AVAILABLE:
            raise RuntimeError("OpenAPI tools not available in current Azure AI SDK version")
            
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
            description="Invoke the Azure Function via HTTP POST for factual questions",
            auth=auth,
        )

    def get_agent_system_message(self, base_url: str, function_key: str) -> str:
        """Generate the comprehensive system message for the agent."""
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
        self, 
        project_endpoint: str, 
        agent_name: str, 
        base_url: str, 
        function_key: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create an AI Foundry agent using the Azure AI SDK.
        
        Args:
            project_endpoint: The AI Foundry project endpoint
            agent_name: Name for the new agent
            base_url: Azure Function App base URL
            function_key: Function app host key for authentication
            
        Returns:
            Tuple of (success: bool, message: str, agent_data: Optional[Dict])
        """
        try:
            # Set the project endpoint
            self.set_project_endpoint(project_endpoint)
            
            # Check if SDK is available
            if not AI_SDK_AVAILABLE:
                return False, "❌ Azure AI SDK not available. Please install: pip install azure-ai-projects", None
            
            # Get the project client
            client = self.project_client
            if not client:
                return False, "❌ Failed to initialize AI Project client", None
            
            # Check for required environment variable
            model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")
            if not model_deployment_name:
                return False, "❌ MODEL_DEPLOYMENT_NAME environment variable is required", None
            
            print(f"🚀 Creating agent '{agent_name}' using Azure AI SDK...")
            print(f"📍 Project endpoint: {project_endpoint}")
            print(f"🤖 Model deployment: {model_deployment_name}")
            print(f"⚙️ Function URL: {base_url}")
            print(f"🔧 OpenAPI tools available: {OPENAPI_TOOLS_AVAILABLE}")
            
            # Create tool and instructions based on available capabilities
            if OPENAPI_TOOLS_AVAILABLE:
                # Use advanced OpenAPI tool for the Azure Function
                TOOL_NAME = "Test_askAgentFunction"
                openapi_tool = self.create_openapi_tool(TOOL_NAME, base_url, function_key)
                system_message = self.get_agent_system_message(base_url, function_key)
                tools = openapi_tool.definitions
                
                print(f"✅ Using OpenAPI tool: {TOOL_NAME}")
                print(f"📝 Advanced system message length: {len(system_message)} characters")
                
            else:
                # Fallback to basic function tool
                function_tool = {
                    "type": "function",
                    "function": {
                        "name": "call_azure_function",
                        "description": f"Call the Azure Function at {base_url}",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The user's query or request to process"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
                
                system_message = f"""You are an AI assistant agent that can call Azure Functions to help users.

Your primary tool is an Azure Function deployed at: {base_url}

When users ask questions or need assistance:
1. Use the call_azure_function tool to invoke the function with their query
2. Process and explain the results to the user
3. Provide helpful context and guidance

Always be helpful, accurate, and provide clear explanations of any function results."""
                
                tools = [function_tool]
                
                print(f"⚠️ Using basic function tool (OpenAPI not available)")
            
            # Create the agent using the Azure AI SDK
            agent = client.agents.create_agent(
                model=model_deployment_name,
                name=agent_name,
                description=f"AI Agent powered by Azure Function at {base_url} - Created from Streamlit UI",
                instructions=system_message,
                tools=tools,
                tool_resources=None,  # No file-based tools for now
                metadata={
                    "created_by": "agentic_rag_demo",
                    "function_url": base_url,
                    "creation_time": datetime.now().isoformat(),
                    "agent_type": "azure_function_agent_openapi" if OPENAPI_TOOLS_AVAILABLE else "azure_function_agent_basic",
                    "tool_type": "openapi" if OPENAPI_TOOLS_AVAILABLE else "basic_function"
                }
            )
            
            print(f"✅ Successfully created agent: {agent.id}")
            
            # Convert agent to dictionary for return
            agent_data = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "model": agent.model,
                "instructions": agent.instructions,
                "tools": [tool.model_dump() if hasattr(tool, 'model_dump') else str(tool) for tool in agent.tools] if agent.tools else [],
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "metadata": agent.metadata
            }
            
            return True, f"✅ Successfully created agent '{agent_name}' (ID: {agent.id})", agent_data
            
        except Exception as e:
            error_msg = f"❌ Error creating AI Foundry agent: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return False, error_msg, None
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents in the current project using Azure AI SDK."""
        if not AI_SDK_AVAILABLE:
            logger.error("Azure AI SDK not available")
            return []
            
        client = self.project_client
        if not client:
            logger.error("Project client not initialized")
            return []
        
        try:
            agents = client.agents.list_agents()
            agent_list = []
            
            for agent in agents:
                agent_data = {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "model": agent.model,
                    "created_at": agent.created_at.isoformat() if agent.created_at else None,
                    "metadata": agent.metadata
                }
                agent_list.append(agent_data)
            
            return agent_list
            
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            return []
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific agent using Azure AI SDK."""
        if not AI_SDK_AVAILABLE:
            logger.error("Azure AI SDK not available")
            return None
            
        client = self.project_client
        if not client:
            logger.error("Project client not initialized")
            return None
        
        try:
            agent = client.agents.get_agent(agent_id)
            
            return {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "model": agent.model,
                "instructions": agent.instructions,
                "tools": [tool.model_dump() if hasattr(tool, 'model_dump') else str(tool) for tool in agent.tools] if agent.tools else [],
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "metadata": agent.metadata
            }
            
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e}")
            return None
    
    def delete_agent(self, agent_id: str) -> Tuple[bool, str]:
        """Delete an agent using Azure AI SDK."""
        if not AI_SDK_AVAILABLE:
            return False, "Azure AI SDK not available"
            
        client = self.project_client
        if not client:
            return False, "Project client not initialized"
        
        try:
            client.agents.delete_agent(agent_id)
            return True, f"Successfully deleted agent {agent_id}"
            
        except Exception as e:
            error_msg = f"Error deleting agent {agent_id}: {e}"
            logger.error(error_msg)
            return False, error_msg
            
# Global instance for the service
_agent_deployment_service = None

def get_ai_foundry_agent_deployment_service() -> AIFoundryAgentDeploymentService:
    """Get or create a global instance of the AI Foundry Agent Deployment Service."""
    global _agent_deployment_service
    if _agent_deployment_service is None:
        _agent_deployment_service = AIFoundryAgentDeploymentService()
    return _agent_deployment_service
