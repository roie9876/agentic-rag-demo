#!/usr/bin/env python3
"""
AI Foundry Agent Deployment Service
Handles deployment and management of AI agents to AI Foundry projects.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from azure.identity import DefaultAzureCredential
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class AIFoundryAgentDeploymentService:
    """Service for deploying and managing AI agents in AI Foundry projects."""
    
    def __init__(self):
        """Initialize the AI Foundry Agent Deployment Service."""
        self.credential = DefaultAzureCredential()
        self._project_endpoint = None
        self._api_version = "2025-05-01-preview"
    
    def set_project_endpoint(self, project_endpoint: str, api_version: str = None) -> None:
        """Set the project endpoint for agent operations."""
        self._project_endpoint = project_endpoint
        if api_version:
            self._api_version = api_version
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for AI Foundry API calls."""
        try:
            # Try different scopes for AI Foundry
            scopes_to_try = [
                "https://cognitiveservices.azure.com/.default",
                "https://ml.azure.com/.default",
                "https://management.azure.com/.default"
            ]
            
            for scope in scopes_to_try:
                try:
                    token = self.credential.get_token(scope)
                    return {
                        'Authorization': f'Bearer {token.token}',
                        'Content-Type': 'application/json'
                    }
                except Exception:
                    continue
            
            raise Exception("Failed to get authentication token for any scope")
            
        except Exception as e:
            logger.error(f"Failed to get auth headers: {e}")
            raise
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents in the current project."""
        if not self._project_endpoint:
            raise ValueError("Project endpoint not set")
        
        try:
            headers = self.get_auth_headers()
            
            # Try different endpoints for listing agents
            agent_endpoints = [
                f"{self._project_endpoint}/agents",
                f"{self._project_endpoint}/api/agents",
                f"{self._project_endpoint}/agents?api-version={self._api_version}"
            ]
            
            for endpoint in agent_endpoints:
                try:
                    response = requests.get(endpoint, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        agents_data = response.json()
                        
                        # Handle different response formats
                        if isinstance(agents_data, list):
                            return agents_data
                        elif isinstance(agents_data, dict) and 'value' in agents_data:
                            return agents_data['value']
                        elif isinstance(agents_data, dict) and 'agents' in agents_data:
                            return agents_data['agents']
                        else:
                            return []
                            
                except requests.RequestException:
                    continue
            
            # If no endpoint worked, return empty list
            logger.warning("Could not list agents from any endpoint")
            return []
            
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            return []
    
    def get_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific agent."""
        if not self._project_endpoint:
            raise ValueError("Project endpoint not set")
        
        try:
            headers = self.get_auth_headers()
            
            # Try different endpoints for getting agent details
            agent_endpoints = [
                f"{self._project_endpoint}/agents/{agent_name}",
                f"{self._project_endpoint}/api/agents/{agent_name}",
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
            return False, "Project endpoint not set", None
        
        try:
            headers = self.get_auth_headers()
            agent_name = agent_config.get('name', 'unnamed-agent')
            
            # Validate required fields
            required_fields = ['name', 'instructions', 'model']
            for field in required_fields:
                if field not in agent_config:
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
            
            # Add agent-specific configuration
            if 'tool_resources' in agent_config:
                agent_payload['tool_resources'] = agent_config['tool_resources']
            
            # Try different endpoints for creating agents
            create_endpoints = [
                f"{self._project_endpoint}/agents",
                f"{self._project_endpoint}/api/agents",
                f"{self._project_endpoint}/agents?api-version={self._api_version}"
            ]
            
            for endpoint in create_endpoints:
                try:
                    response = requests.post(
                        endpoint, 
                        headers=headers, 
                        json=agent_payload,
                        timeout=60
                    )
                    
                    if response.status_code in [200, 201]:
                        created_agent = response.json()
                        return True, f"Agent '{agent_name}' created successfully", created_agent
                    elif response.status_code == 409:
                        return False, f"Agent '{agent_name}' already exists", None
                    elif response.status_code == 400:
                        error_detail = response.json().get('message', response.text)
                        return False, f"Invalid agent configuration: {error_detail}", None
                    else:
                        logger.warning(f"Endpoint {endpoint} returned {response.status_code}")
                        continue
                        
                except requests.RequestException as e:
                    logger.warning(f"Request failed for endpoint {endpoint}: {e}")
                    continue
            
            return False, "Failed to create agent on any endpoint", None
            
        except Exception as e:
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
            return None


# Global instance
ai_foundry_agent_deployment = AIFoundryAgentDeploymentService()
