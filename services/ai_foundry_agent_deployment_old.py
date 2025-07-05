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
    from azure.ai.projects.models import (
        Agent,
        CodeInterpreterTool,
        FileSearchTool,
        FunctionTool
    )
    AI_SDK_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Azure AI SDK not available: {e}")
    AI_SDK_AVAILABLE = False

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
                f"{self._project_endpoint}/agents/{agent_name}?api-version={self._api_version}"
            ]
            
            for endpoint in agent_endpoints:
                try:
                    response = requests.get(endpoint, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 404:
                        return None
                        
                except requests.RequestException:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting agent {agent_name}: {e}")
            return None
    
    def create_agent(self, agent_config: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Create a new agent in the project."""
        if not self._project_endpoint:
            print("🔍 DEBUG: Project endpoint not set")
            return False, "Project endpoint not set", None
        
        try:
            headers = self.get_auth_headers()
            agent_name = agent_config.get('name', 'unnamed-agent')
            
            print(f"🔍 DEBUG: Creating agent '{agent_name}' at project endpoint: {self._project_endpoint}")
            print(f"🔍 DEBUG: Headers available: {list(headers.keys()) if headers else 'None'}")
            
            # Validate required fields
            required_fields = ['name', 'instructions', 'model']
            for field in required_fields:
                if field not in agent_config:
                    print(f"🔍 DEBUG: Missing required field: {field}")
                    return False, f"Missing required field: {field}", None
            
            # Prepare the agent payload
            agent_payload = {
                "name": agent_config['name'],
                "instructions": agent_config['instructions'],
                "model": agent_config.get('model', 'gpt-4'),
                "tools": agent_config.get('tools', []),
                "metadata": agent_config.get('metadata', {}),
                "temperature": agent_config.get('temperature', 0.7),
                "top_p": agent_config.get('top_p', 1.0),
                "max_tokens": agent_config.get('max_tokens', 4096)
            }
            
            print(f"🔍 DEBUG: Agent payload prepared with {len(agent_payload.get('tools', []))} tools")
            
            # Add agent-specific configuration
            if 'tool_resources' in agent_config:
                agent_payload['tool_resources'] = agent_config['tool_resources']
            
            # Try different endpoints for creating agents
            create_endpoints = [
                f"{self._project_endpoint}/agents",
                f"{self._project_endpoint}/api/agents",
                f"{self._project_endpoint}/agents?api-version={self._api_version}"
            ]
            
            print(f"🔍 DEBUG: Trying {len(create_endpoints)} endpoints...")
            
            for i, endpoint in enumerate(create_endpoints):
                print(f"🔍 DEBUG: Trying endpoint {i+1}/{len(create_endpoints)}: {endpoint}")
                try:
                    response = requests.post(
                        endpoint, 
                        headers=headers, 
                        json=agent_payload,
                        timeout=60
                    )
                    
                    print(f"🔍 DEBUG: Response status: {response.status_code}")
                    print(f"🔍 DEBUG: Response headers: {dict(response.headers)}")
                    print(f"🔍 DEBUG: Response content: {response.text[:500]}...")
                    
                    if response.status_code in [200, 201]:
                        created_agent = response.json()
                        print(f"🔍 DEBUG: ✅ Agent created successfully!")
                        return True, f"Agent '{agent_name}' created successfully", created_agent
                    elif response.status_code == 409:
                        print(f"🔍 DEBUG: ❌ Agent already exists")
                        return False, f"Agent '{agent_name}' already exists", None
                    elif response.status_code == 400:
                        error_detail = response.json().get('message', response.text)
                        print(f"🔍 DEBUG: ❌ Bad request: {error_detail}")
                        return False, f"Invalid agent configuration: {error_detail}", None
                    else:
                        print(f"🔍 DEBUG: ❌ Endpoint failed with status {response.status_code}")
                        logger.warning(f"Endpoint {endpoint} returned {response.status_code}")
                        continue
                        
                except requests.RequestException as e:
                    print(f"🔍 DEBUG: ❌ Request exception for endpoint {endpoint}: {str(e)}")
                    logger.warning(f"Request failed for endpoint {endpoint}: {e}")
                    continue
            
            print(f"🔍 DEBUG: ❌ All endpoints failed!")
            return False, "Failed to create agent on any endpoint", None
            
        except Exception as e:
            print(f"🔍 DEBUG: ❌ General exception in create_agent: {str(e)}")
            logger.error(f"Error creating agent: {e}")
            return False, f"Error creating agent: {str(e)}", None
    
    def update_agent(self, agent_name: str, agent_config: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Update an existing agent."""
        if not self._project_endpoint:
            return False, "Project endpoint not set", None
        
        try:
            headers = self.get_auth_headers()
            
            # Check if agent exists first
            existing_agent = self.get_agent(agent_name)
            if not existing_agent:
                return False, f"Agent '{agent_name}' not found", None
            
            # Prepare the update payload
            update_payload = {
                "instructions": agent_config.get('instructions', existing_agent.get('instructions')),
                "model": agent_config.get('model', existing_agent.get('model')),
                "tools": agent_config.get('tools', existing_agent.get('tools', [])),
                "metadata": agent_config.get('metadata', existing_agent.get('metadata', {})),
                "temperature": agent_config.get('temperature', existing_agent.get('temperature', 0.7)),
                "top_p": agent_config.get('top_p', existing_agent.get('top_p', 1.0)),
                "max_tokens": agent_config.get('max_tokens', existing_agent.get('max_tokens', 4096))
            }
            
            # Add tool resources if provided
            if 'tool_resources' in agent_config:
                update_payload['tool_resources'] = agent_config['tool_resources']
            
            # Try different endpoints for updating agents
            update_endpoints = [
                f"{self._project_endpoint}/agents/{agent_name}",
                f"{self._project_endpoint}/api/agents/{agent_name}",
                f"{self._project_endpoint}/agents/{agent_name}?api-version={self._api_version}"
            ]
            
            for endpoint in update_endpoints:
                try:
                    response = requests.patch(
                        endpoint, 
                        headers=headers, 
                        json=update_payload,
                        timeout=60
                    )
                    
                    if response.status_code in [200, 204]:
                        updated_agent = response.json() if response.content else existing_agent
                        return True, f"Agent '{agent_name}' updated successfully", updated_agent
                    elif response.status_code == 404:
                        return False, f"Agent '{agent_name}' not found", None
                    else:
                        logger.warning(f"Endpoint {endpoint} returned {response.status_code}")
                        continue
                        
                except requests.RequestException as e:
                    logger.warning(f"Request failed for endpoint {endpoint}: {e}")
                    continue
            
            return False, "Failed to update agent on any endpoint", None
            
        except Exception as e:
            logger.error(f"Error updating agent: {e}")
            return False, f"Error updating agent: {str(e)}", None
    
    def delete_agent(self, agent_name: str) -> Tuple[bool, str]:
        """Delete an agent from the project."""
        if not self._project_endpoint:
            return False, "Project endpoint not set"
        
        try:
            headers = self.get_auth_headers()
            
            # Try different endpoints for deleting agents
            delete_endpoints = [
                f"{self._project_endpoint}/agents/{agent_name}",
                f"{self._project_endpoint}/api/agents/{agent_name}",
                f"{self._project_endpoint}/agents/{agent_name}?api-version={self._api_version}"
            ]
            
            for endpoint in delete_endpoints:
                try:
                    response = requests.delete(endpoint, headers=headers, timeout=30)
                    
                    if response.status_code in [200, 204]:
                        return True, f"Agent '{agent_name}' deleted successfully"
                    elif response.status_code == 404:
                        return False, f"Agent '{agent_name}' not found"
                    else:
                        logger.warning(f"Endpoint {endpoint} returned {response.status_code}")
                        continue
                        
                except requests.RequestException as e:
                    logger.warning(f"Request failed for endpoint {endpoint}: {e}")
                    continue
            
            return False, "Failed to delete agent on any endpoint"
            
        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
            return False, f"Error deleting agent: {str(e)}"
    
    def test_agent(self, agent_name: str, test_message: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Test an agent with a message."""
        if not self._project_endpoint:
            return False, "Project endpoint not set", None
        
        try:
            headers = self.get_auth_headers()
            
            # Create a thread for testing
            thread_payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": test_message
                    }
                ]
            }
            
            # Try different endpoints for creating threads
            thread_endpoints = [
                f"{self._project_endpoint}/threads",
                f"{self._project_endpoint}/api/threads"
            ]
            
            thread_id = None
            for endpoint in thread_endpoints:
                try:
                    response = requests.post(
                        endpoint, 
                        headers=headers, 
                        json=thread_payload,
                        timeout=30
                    )
                    
                    if response.status_code in [200, 201]:
                        thread_data = response.json()
                        thread_id = thread_data.get('id')
                        break
                        
                except requests.RequestException:
                    continue
            
            if not thread_id:
                return False, "Failed to create test thread", None
            
            # Run the agent on the thread
            run_payload = {
                "agent_id": agent_name,
                "instructions": "Please respond to the user's message."
            }
            
            run_endpoints = [
                f"{self._project_endpoint}/threads/{thread_id}/runs",
                f"{self._project_endpoint}/api/threads/{thread_id}/runs"
            ]
            
            run_id = None
            for endpoint in run_endpoints:
                try:
                    response = requests.post(
                        endpoint, 
                        headers=headers, 
                        json=run_payload,
                        timeout=30
                    )
                    
                    if response.status_code in [200, 201]:
                        run_data = response.json()
                        run_id = run_data.get('id')
                        break
                        
                except requests.RequestException:
                    continue
            
            if not run_id:
                return False, "Failed to start agent run", None
            
            # Wait for the run to complete
            max_wait_time = 60  # 60 seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    status_response = requests.get(
                        f"{self._project_endpoint}/threads/{thread_id}/runs/{run_id}",
                        headers=headers,
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        run_status = status_response.json()
                        status = run_status.get('status')
                        
                        if status == 'completed':
                            # Get the response messages
                            messages_response = requests.get(
                                f"{self._project_endpoint}/threads/{thread_id}/messages",
                                headers=headers,
                                timeout=10
                            )
                            
                            if messages_response.status_code == 200:
                                messages_data = messages_response.json()
                                messages = messages_data.get('data', [])
                                
                                # Find the agent's response
                                for message in messages:
                                    if message.get('role') == 'assistant':
                                        content = message.get('content', [])
                                        if content and isinstance(content, list):
                                            text_content = content[0].get('text', {}).get('value', '')
                                            return True, "Agent test successful", {
                                                'agent_response': text_content,
                                                'thread_id': thread_id,
                                                'run_id': run_id,
                                                'test_message': test_message
                                            }
                                
                                return True, "Agent responded but no text content found", {
                                    'thread_id': thread_id,
                                    'run_id': run_id,
                                    'messages': messages
                                }
                            
                        elif status in ['failed', 'cancelled', 'expired']:
                            error_message = run_status.get('last_error', {}).get('message', 'Unknown error')
                            return False, f"Agent run failed: {error_message}", None
                        
                        # Still running, wait a bit more
                        time.sleep(2)
                    
                except requests.RequestException:
                    time.sleep(2)
                    continue
            
            return False, "Agent test timed out", None
            
        except Exception as e:
            logger.error(f"Error testing agent: {e}")
            return False, f"Error testing agent: {str(e)}", None
    
    def create_retrieval_agent(self, agent_name: str, index_name: str, 
                               azure_search_endpoint: str, instructions: str = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Create a specialized retrieval agent for Azure Search integration."""
        
        # Default instructions for retrieval agents
        if not instructions:
            instructions = f"""
You are a helpful AI assistant with access to knowledge from the {index_name} search index.

Your capabilities:
- Answer questions using information from the search index
- Provide accurate, relevant responses based on the available knowledge
- Cite sources when possible
- Admit when you don't have enough information to answer

When responding:
1. Use the search results to provide comprehensive answers
2. Be concise but thorough
3. Always aim to be helpful and accurate
4. If the search doesn't return relevant results, say so clearly

Search Index: {index_name}
Search Endpoint: {azure_search_endpoint}
"""
        
        # Configuration for retrieval agent
        agent_config = {
            'name': agent_name,
            'instructions': instructions.strip(),
            'model': 'gpt-4',
            'tools': [
                {
                    'type': 'search',
                    'search': {
                        'type': 'azure_search',
                        'azure_search': {
                            'endpoint': azure_search_endpoint,
                            'index_name': index_name,
                            'semantic_configuration': 'default',
                            'query_type': 'semantic',
                            'top_k': 5,
                            'reranker_threshold': 1.0
                        }
                    }
                }
            ],
            'metadata': {
                'type': 'retrieval_agent',
                'index_name': index_name,
                'search_endpoint': azure_search_endpoint,
                'created_by': 'agentic_rag_demo',
                'created_at': datetime.now().isoformat()
            },
            'temperature': 0.7,
            'max_tokens': 4096
        }
        
        return self.create_agent(agent_config)
    
    def get_project_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current project."""
        if not self._project_endpoint:
            return None
        
        try:
            headers = self.get_auth_headers()
            
            response = requests.get(self._project_endpoint, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Could not get project info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting project info: {e}")
    
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
            
            # Create a function tool for the Azure Function
            function_tool = FunctionTool(
                function={
                    "name": "call_azure_function",
                    "description": f"Call the Azure Function at {base_url}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The user's query or request to process"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Additional parameters for the function call"
                            }
                        },
                        "required": ["query"]
                    }
                }
            )
            
            # Generate comprehensive instructions for the agent
            instructions = f"""You are an AI assistant agent that can call Azure Functions to help users.

Your primary tool is an Azure Function deployed at: {base_url}

When users ask questions or need assistance, you can:
1. Use the call_azure_function tool to invoke the function with their query
2. Process and explain the results to the user
3. Provide helpful context and guidance

Function Details:
- Base URL: {base_url}
- Authentication: Function key protected
- Purpose: Process user queries and provide intelligent responses

Always be helpful, accurate, and provide clear explanations of any function results.
"""
            
            # Create the agent using the Azure AI SDK
            agent = client.agents.create_agent(
                model=model_deployment_name,
                name=agent_name,
                description=f"AI Agent powered by Azure Function at {base_url}",
                instructions=instructions,
                tools=[function_tool],
                tool_resources=None,  # No file-based tools for now
                metadata={
                    "created_by": "agentic_rag_demo",
                    "function_url": base_url,
                    "creation_time": datetime.now().isoformat(),
                    "agent_type": "azure_function_agent"
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
                                    }
                                },
                                {
                                    "name": "includesrc",
                                    "in": "query",
                                    "required": False,
                                    "schema": {
                                        "type": "boolean",
                                        "default": True
                                    }
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "Plain-text answer",
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
        }
        return tool_schema
    
    def _get_agent_system_message(self, base_url: str, function_key: str) -> str:
        """Generate the system message for the agent."""
        return (
            "You have one action called askAgentFunction.\n"
            "Call it **every time** the user asks a factual question.\n"
            "Send the whole question unchanged as the {question} path parameter **and** include the two query parameters exactly as shown below:\n"
            f"  • code={function_key}\n"
            "  • includesrc=true\n"
            "Example URL you must generate (line breaks added for clarity):\n"
            f"POST {base_url}/AgentFunction/{{question}}?code={function_key}&includesrc=true\n"
            "Return the Function's plain-text response **verbatim and in full**, including any inline citations such as [my_document.pdf].\n"
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
# Global instance - COMMENTED OUT to prevent slow startup
# Use lazy initialization instead:
# ai_foundry_agent_deployment = AIFoundryAgentDeploymentService()

def get_ai_foundry_agent_deployment_service():
    """Get a lazy-initialized instance of AIFoundryAgentDeploymentService."""
    if not hasattr(get_ai_foundry_agent_deployment_service, '_instance'):
        get_ai_foundry_agent_deployment_service._instance = AIFoundryAgentDeploymentService()
    return get_ai_foundry_agent_deployment_service._instance
