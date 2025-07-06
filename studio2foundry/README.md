# Studio2Foundry Azure Function

This Azure Function provides HTTP endpoints for integrating with Azure AI Foundry Studio and managing agentic workflows.

## Function Structure

```
studio2foundry/
├── host.json                          # Azure Functions host configuration
├── requirements.txt                   # Python dependencies
├── .funcignore                       # Files to ignore during deployment
├── Studio2FoundryFunction/           # Main HTTP function
│   ├── function.json                 # Function binding configuration
│   └── __init__.py                   # Function implementation
└── README.md                         # This file
```

## Endpoints

### GET Requests

- **GET /?action=status** - Get function health status
- **GET /?action=projects** - List AI Foundry projects

### POST Requests

- **POST /** with `action: create_agent` - Create a new AI Foundry agent
- **POST /** with `action: execute_agent` - Execute an agent request

## Environment Variables

The function expects these environment variables to be configured:

- `PROJECT_ENDPOINT` - Azure AI Foundry project endpoint
- `AZURE_SEARCH_ENDPOINT` - Azure Search service endpoint  
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI service endpoint

## Deployment

This function is deployed via the Studio2Foundry tab in the main application using:

```bash
az functionapp deployment source config-zip \
  -g <resource-group> \
  -n <function-app-name> \
  --src studio2foundry.zip
```

## Authentication

The function uses Azure Managed Identity for authentication with Azure services.

## Logging

All function activity is logged to Azure Application Insights for monitoring and debugging.
