"""
Agent Deployment Service
-----------------------
Handles deployment of agents to AI Foundry projects.
"""

import json
import requests
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Configuration for creating an AI agent."""
    name: str
    display_name: str
    description: str
    model_deployment: str
    instructions: str
    tools: List[Dict[str, Any]]
    additional_properties: Dict[str, Any]

@dataclass
class DeployedAgent:
    """Represents a deployed AI agent."""
    agent_id: str
    name: str
    display_name: str
    description: str
    model: str
    status: str
    endpoint: str
    created_at: str
    properties: Dict[str, Any]

class AgentDeploymentService:
    """Service for deploying agents to AI Foundry projects."""
    
    def __init__(self):
        """Initialize the agent deployment service."""
        self.credential = DefaultAzureCredential()
    
    def list_agents_in_project(self, project_endpoint: str) -> Tuple[List[DeployedAgent], List[str]]:
        """List all agents in a project."""
        agents = []
        errors = []
        
        try:
            # Try SDK approach first
            agents_sdk, errors_sdk = self._list_agents_sdk(project_endpoint)
            if agents_sdk:
                return agents_sdk, errors_sdk
            
            # Fallback to REST API
            agents_rest, errors_rest = self._list_agents_rest(project_endpoint)
            errors.extend(errors_sdk)
            errors.extend(errors_rest)
            return agents_rest, errors
            
        except Exception as e:
            error_msg = f"Failed to list agents: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return agents, errors
    
    def _list_agents_sdk(self, project_endpoint: str) -> Tuple[List[DeployedAgent], List[str]]:
        """List agents using Azure AI Projects SDK."""
        agents = []
        errors = []
        
        try:
            client = AIProjectClient.from_connection_string(
                conn_str=project_endpoint,
                credential=self.credential
            )
            
            # List agents using the SDK
            agents_list = client.agents.list_agents()
            
            for agent in agents_list:
                agents.append(DeployedAgent(
                    agent_id=agent.id,
                    name=agent.name or agent.id,
                    display_name=agent.name or agent.id,
                    description=agent.description or "",
                    model=getattr(agent.model, 'deployment_name', 'Unknown'),
                    status="active",
                    endpoint=f"{project_endpoint}/agents/{agent.id}",
                    created_at=str(agent.created_at) if hasattr(agent, 'created_at') else "",
                    properties=agent.__dict__ if hasattr(agent, '__dict__') else {}
                ))
                
        except Exception as e:
            errors.append(f"SDK method failed: {str(e)}")
        
        return agents, errors
    
    def _list_agents_rest(self, project_endpoint: str) -> Tuple[List[DeployedAgent], List[str]]:
        """List agents using REST API."""
        agents = []
        errors = []
        
        try:
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Try different API endpoints
            api_endpoints = [
                f"{project_endpoint}/agents",
                f"{project_endpoint}/api/agents"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = requests.get(
                        endpoint,
                        headers=headers,
                        params={"api-version": "2024-05-01-preview"},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        agents_data = response.json()
                        agent_list = agents_data.get('value', [])
                        
                        for agent in agent_list:
                            agents.append(DeployedAgent(
                                agent_id=agent.get('id', 'unknown'),
                                name=agent.get('name', 'Unknown'),
                                display_name=agent.get('displayName', agent.get('name', 'Unknown')),
                                description=agent.get('description', ''),
                                model=agent.get('model', {}).get('deploymentName', 'Unknown'),
                                status=agent.get('status', 'unknown'),
                                endpoint=f"{project_endpoint}/agents/{agent.get('id', '')}",
                                created_at=agent.get('createdAt', ''),
                                properties=agent
                            ))
                        break
                    elif response.status_code == 404:
                        continue
                    else:
                        errors.append(f"API call failed: {response.status_code} - {response.text}")
                        
                except requests.RequestException as e:
                    errors.append(f"Request failed for {endpoint}: {str(e)}")
                    continue
        
        except Exception as e:
            errors.append(f"REST method failed: {str(e)}")
        
        return agents, errors
    
    def create_agent(self, project_endpoint: str, agent_config: AgentConfig) -> Tuple[bool, str, Optional[DeployedAgent]]:
        """Create a new agent in the project."""
        try:
            # Try SDK approach first
            success, message, agent = self._create_agent_sdk(project_endpoint, agent_config)
            if success:
                return success, message, agent
            
            # Fallback to REST API
            return self._create_agent_rest(project_endpoint, agent_config)
            
        except Exception as e:
            error_msg = f"Failed to create agent: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _create_agent_sdk(self, project_endpoint: str, agent_config: AgentConfig) -> Tuple[bool, str, Optional[DeployedAgent]]:
        """Create agent using Azure AI Projects SDK."""
        try:
            client = AIProjectClient.from_connection_string(
                conn_str=project_endpoint,
                credential=self.credential
            )
            
            # Prepare agent creation parameters
            from azure.ai.agents.models import FunctionTool, FunctionDefinition
            
            # Convert tool configurations to SDK format
            tools = []
            for tool_config in agent_config.tools:
                if tool_config.get('type') == 'function':
                    func_def = FunctionDefinition(
                        name=tool_config['function']['name'],
                        description=tool_config['function']['description'],
                        parameters=tool_config['function']['parameters']
                    )
                    tools.append(FunctionTool(function=func_def))
            
            # Create the agent
            agent = client.agents.create_agent(
                model=agent_config.model_deployment,
                name=agent_config.name,
                description=agent_config.description,
                instructions=agent_config.instructions,
                tools=tools
            )
            
            deployed_agent = DeployedAgent(
                agent_id=agent.id,
                name=agent.name or agent_config.name,
                display_name=agent.name or agent_config.display_name,
                description=agent.description or agent_config.description,
                model=agent_config.model_deployment,
                status="active",
                endpoint=f"{project_endpoint}/agents/{agent.id}",
                created_at=str(agent.created_at) if hasattr(agent, 'created_at') else "",
                properties=agent.__dict__ if hasattr(agent, '__dict__') else {}
            )
            
            return True, "Agent created successfully using SDK", deployed_agent
            
        except Exception as e:
            return False, f"SDK creation failed: {str(e)}", None
    
    def _create_agent_rest(self, project_endpoint: str, agent_config: AgentConfig) -> Tuple[bool, str, Optional[DeployedAgent]]:
        """Create agent using REST API."""
        try:
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare agent data
            agent_data = {
                "name": agent_config.name,
                "description": agent_config.description,
                "instructions": agent_config.instructions,
                "model": agent_config.model_deployment,
                "tools": agent_config.tools
            }
            
            # Add additional properties
            agent_data.update(agent_config.additional_properties)
            
            # Try different API endpoints
            api_endpoints = [
                f"{project_endpoint}/agents",
                f"{project_endpoint}/api/agents"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        json=agent_data,
                        params={"api-version": "2024-05-01-preview"},
                        timeout=60
                    )
                    
                    if response.status_code in [200, 201]:
                        agent_result = response.json()
                        
                        deployed_agent = DeployedAgent(
                            agent_id=agent_result.get('id', 'unknown'),
                            name=agent_result.get('name', agent_config.name),
                            display_name=agent_result.get('displayName', agent_config.display_name),
                            description=agent_result.get('description', agent_config.description),
                            model=agent_config.model_deployment,
                            status=agent_result.get('status', 'active'),
                            endpoint=f"{project_endpoint}/agents/{agent_result.get('id', '')}",
                            created_at=agent_result.get('createdAt', ''),
                            properties=agent_result
                        )
                        
                        return True, "Agent created successfully using REST API", deployed_agent
                    elif response.status_code == 404:
                        continue
                    else:
                        return False, f"API call failed: {response.status_code} - {response.text}", None
                        
                except requests.RequestException as e:
                    continue
            
            return False, "All API endpoints failed", None
            
        except Exception as e:
            return False, f"REST creation failed: {str(e)}", None
    
    def delete_agent(self, project_endpoint: str, agent_id: str) -> Tuple[bool, str]:
        """Delete an agent from the project."""
        try:
            # Try SDK approach first
            success, message = self._delete_agent_sdk(project_endpoint, agent_id)
            if success:
                return success, message
            
            # Fallback to REST API
            return self._delete_agent_rest(project_endpoint, agent_id)
            
        except Exception as e:
            error_msg = f"Failed to delete agent: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _delete_agent_sdk(self, project_endpoint: str, agent_id: str) -> Tuple[bool, str]:
        """Delete agent using Azure AI Projects SDK."""
        try:
            client = AIProjectClient.from_connection_string(
                conn_str=project_endpoint,
                credential=self.credential
            )
            
            client.agents.delete_agent(agent_id)
            return True, "Agent deleted successfully using SDK"
            
        except Exception as e:
            return False, f"SDK deletion failed: {str(e)}"
    
    def _delete_agent_rest(self, project_endpoint: str, agent_id: str) -> Tuple[bool, str]:
        """Delete agent using REST API."""
        try:
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Try different API endpoints
            api_endpoints = [
                f"{project_endpoint}/agents/{agent_id}",
                f"{project_endpoint}/api/agents/{agent_id}"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = requests.delete(
                        endpoint,
                        headers=headers,
                        params={"api-version": "2024-05-01-preview"},
                        timeout=30
                    )
                    
                    if response.status_code in [200, 204]:
                        return True, "Agent deleted successfully using REST API"
                    elif response.status_code == 404:
                        return True, "Agent not found (already deleted)"
                    else:
                        continue
                        
                except requests.RequestException as e:
                    continue
            
            return False, "All deletion endpoints failed"
            
        except Exception as e:
            return False, f"REST deletion failed: {str(e)}"
    
    def get_agent_details(self, project_endpoint: str, agent_id: str) -> Tuple[Optional[DeployedAgent], List[str]]:
        """Get detailed information about a specific agent."""
        errors = []
        
        try:
            # Try SDK approach first
            agent, errors_sdk = self._get_agent_details_sdk(project_endpoint, agent_id)
            if agent:
                return agent, errors_sdk
            
            # Fallback to REST API
            agent_rest, errors_rest = self._get_agent_details_rest(project_endpoint, agent_id)
            errors.extend(errors_sdk)
            errors.extend(errors_rest)
            return agent_rest, errors
            
        except Exception as e:
            error_msg = f"Failed to get agent details: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return None, errors
    
    def _get_agent_details_sdk(self, project_endpoint: str, agent_id: str) -> Tuple[Optional[DeployedAgent], List[str]]:
        """Get agent details using Azure AI Projects SDK."""
        errors = []
        
        try:
            client = AIProjectClient.from_connection_string(
                conn_str=project_endpoint,
                credential=self.credential
            )
            
            agent = client.agents.get_agent(agent_id)
            
            deployed_agent = DeployedAgent(
                agent_id=agent.id,
                name=agent.name or agent.id,
                display_name=agent.name or agent.id,
                description=agent.description or "",
                model=getattr(agent.model, 'deployment_name', 'Unknown'),
                status="active",
                endpoint=f"{project_endpoint}/agents/{agent.id}",
                created_at=str(agent.created_at) if hasattr(agent, 'created_at') else "",
                properties=agent.__dict__ if hasattr(agent, '__dict__') else {}
            )
            
            return deployed_agent, errors
            
        except Exception as e:
            errors.append(f"SDK method failed: {str(e)}")
            return None, errors
    
    def _get_agent_details_rest(self, project_endpoint: str, agent_id: str) -> Tuple[Optional[DeployedAgent], List[str]]:
        """Get agent details using REST API."""
        errors = []
        
        try:
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Try different API endpoints
            api_endpoints = [
                f"{project_endpoint}/agents/{agent_id}",
                f"{project_endpoint}/api/agents/{agent_id}"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = requests.get(
                        endpoint,
                        headers=headers,
                        params={"api-version": "2024-05-01-preview"},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        agent = response.json()
                        
                        deployed_agent = DeployedAgent(
                            agent_id=agent.get('id', agent_id),
                            name=agent.get('name', 'Unknown'),
                            display_name=agent.get('displayName', agent.get('name', 'Unknown')),
                            description=agent.get('description', ''),
                            model=agent.get('model', {}).get('deploymentName', 'Unknown'),
                            status=agent.get('status', 'unknown'),
                            endpoint=f"{project_endpoint}/agents/{agent_id}",
                            created_at=agent.get('createdAt', ''),
                            properties=agent
                        )
                        
                        return deployed_agent, errors
                    elif response.status_code == 404:
                        continue
                    else:
                        errors.append(f"API call failed: {response.status_code} - {response.text}")
                        
                except requests.RequestException as e:
                    errors.append(f"Request failed for {endpoint}: {str(e)}")
                    continue
        
        except Exception as e:
            errors.append(f"REST method failed: {str(e)}")
        
        return None, errors
    
    def create_function_tool_config(self, function_name: str, base_url: str, function_key: str) -> Dict[str, Any]:
        """Create a function tool configuration for Azure Function integration."""
        return {
            "type": "function",
            "function": {
                "name": function_name,
                "description": f"Call the {function_name} Azure Function for document retrieval and search",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query or question to process"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                },
                "url": f"{base_url}/{function_name}?code={function_key}",
                "method": "POST"
            }
        }
    
    def validate_project_endpoint(self, project_endpoint: str) -> Tuple[bool, str]:
        """Validate that a project endpoint is accessible."""
        try:
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            headers = {
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            }
            
            # Try to get project info
            response = requests.get(
                project_endpoint,
                headers=headers,
                params={"api-version": "2024-05-01-preview"},
                timeout=30
            )
            
            if response.status_code == 200:
                return True, "Project endpoint is accessible"
            elif response.status_code == 404:
                return False, "Project not found - please check the endpoint URL"
            elif response.status_code == 403:
                return False, "Access denied - please check your permissions"
            else:
                return False, f"Unexpected response: {response.status_code}"
                
        except Exception as e:
            return False, f"Failed to validate endpoint: {str(e)}"
