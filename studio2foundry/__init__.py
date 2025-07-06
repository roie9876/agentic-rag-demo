import logging
import json
import os
from typing import Dict, Any, Optional
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function for Studio2Foundry integration.
    
    This function provides an HTTP endpoint for integrating with Azure AI Foundry Studio
    and handles agent operations, project management, and other Studio2Foundry features.
    """
    logging.info('Studio2Foundry Function processed a request.')

    try:
        # Get request method and body
        method = req.method
        
        if method == "GET":
            return handle_get_request(req)
        elif method == "POST":
            return handle_post_request(req)
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Method {method} not supported"}),
                status_code=405,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"Error in Studio2Foundry Function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_get_request(req: func.HttpRequest) -> func.HttpResponse:
    """Handle GET requests - typically for status checks or retrieving information."""
    
    # Get query parameters
    action = req.params.get('action', 'status')
    
    if action == 'status':
        return get_function_status()
    elif action == 'projects':
        return get_ai_foundry_projects()
    else:
        return func.HttpResponse(
            json.dumps({"error": f"Unknown action: {action}"}),
            status_code=400,
            mimetype="application/json"
        )


def handle_post_request(req: func.HttpRequest) -> func.HttpResponse:
    """Handle POST requests - typically for creating or updating resources."""
    
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        action = req_body.get('action')
        
        if action == 'create_agent':
            return create_ai_foundry_agent(req_body)
        elif action == 'execute_agent':
            return execute_agent_request(req_body)
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown action: {action}"}),
                status_code=400,
                mimetype="application/json"
            )
            
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json"
        )


def get_function_status() -> func.HttpResponse:
    """Return the current status of the Studio2Foundry Function."""
    
    status = {
        "status": "healthy",
        "function_name": "Studio2FoundryFunction",
        "version": "1.0.0",
        "environment_variables": {
            "PROJECT_ENDPOINT": bool(os.getenv("PROJECT_ENDPOINT")),
            "AZURE_SEARCH_ENDPOINT": bool(os.getenv("AZURE_SEARCH_ENDPOINT")),
            "AZURE_OPENAI_ENDPOINT": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
        },
        "timestamp": func.datetime.utcnow().isoformat()
    }
    
    return func.HttpResponse(
        json.dumps(status, indent=2),
        status_code=200,
        mimetype="application/json"
    )


def get_ai_foundry_projects() -> func.HttpResponse:
    """Get list of available AI Foundry projects."""
    
    try:
        # This would integrate with Azure AI Foundry to list projects
        # For now, return a placeholder response
        projects = {
            "projects": [],
            "message": "AI Foundry integration not yet implemented",
            "timestamp": func.datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(projects, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error getting AI Foundry projects: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def create_ai_foundry_agent(req_body: Dict[str, Any]) -> func.HttpResponse:
    """Create a new AI Foundry agent."""
    
    try:
        # Extract required parameters
        agent_name = req_body.get('agent_name')
        if not agent_name:
            return func.HttpResponse(
                json.dumps({"error": "agent_name is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # This would integrate with Azure AI Foundry to create agents
        # For now, return a placeholder response
        result = {
            "agent_name": agent_name,
            "status": "created",
            "message": "AI Foundry agent creation not yet implemented",
            "timestamp": func.datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(result, indent=2),
            status_code=201,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error creating AI Foundry agent: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def execute_agent_request(req_body: Dict[str, Any]) -> func.HttpResponse:
    """Execute a request through an AI Foundry agent."""
    
    try:
        # Extract required parameters
        agent_name = req_body.get('agent_name')
        query = req_body.get('query')
        
        if not agent_name or not query:
            return func.HttpResponse(
                json.dumps({"error": "agent_name and query are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # This would integrate with Azure AI Foundry to execute agent requests
        # For now, return a placeholder response
        result = {
            "agent_name": agent_name,
            "query": query,
            "response": "Agent execution not yet implemented",
            "timestamp": func.datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(result, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error executing agent request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
