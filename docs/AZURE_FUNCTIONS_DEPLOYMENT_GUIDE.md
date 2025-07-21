# 🚀 Azure Functions Deployment Guide

**Date:** July 2025  
**Status:** ✅ COMPLETE  
**Impact:** Comprehensive guide for deploying and configuring Azure Functions with Agentic RAG

## 🎯 Overview

This guide covers the complete deployment and configuration process for Azure Functions that power the Agentic RAG system, including authentication, RBAC setup, environment configuration, and troubleshooting.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Function App Structure](#function-app-structure)
3. [Deployment Methods](#deployment-methods)
4. [Environment Configuration](#environment-configuration)
5. [RBAC and Authentication](#rbac-and-authentication)
6. [Testing and Validation](#testing-and-validation)
7. [Troubleshooting](#troubleshooting)
8. [Monitoring and Logging](#monitoring-and-logging)

## 🔧 Prerequisites

### Azure Resources
- **Azure Subscription** with Function App creation permissions
- **Resource Group** for deployment
- **Storage Account** for Function App backend
- **Application Insights** (optional but recommended)

### Required Azure Services
- **Azure OpenAI** service with deployed models
- **Azure AI Search** service with configured indexes
- **Azure Document Intelligence** service
- **Azure Blob Storage** for document storage

### Development Environment
- **Azure CLI** installed and configured
- **Python 3.8+** for local development
- **Visual Studio Code** with Azure Functions extension (recommended)
- **Git** for version control

## 📁 Function App Structure

### Project Layout
```
function/
├── function_app.py              # Main function entry point
├── requirements.txt             # Python dependencies
├── host.json                   # Function host configuration
├── local.settings.json         # Local development settings
└── AgentFunction/
    └── __init__.py             # Function implementation
```

### Core Dependencies
```python
# function/requirements.txt
azure-functions
azure-identity>=1.15.0
azure-ai-projects
azure-search-documents==11.6.0b12
azure-ai-agents==1.0.1
openai>=1.35.0
requests>=2.32.0
tenacity==8.5.0
```

## 🚀 Deployment Methods

### Method 1: Streamlit UI Deployment (Recommended)

The project includes a comprehensive deployment interface:

```python
# Access via the main Streamlit application
python3 agentic-rag-demo.py
# Navigate to "Azure Function Config" tab
```

**Features:**
- ✅ **Visual configuration** of environment variables
- ✅ **Automatic RBAC setup** for managed identity
- ✅ **Real-time deployment status** tracking
- ✅ **Integrated testing** with function validation
- ✅ **SSL troubleshooting** for private network deployments

### Method 2: Azure CLI Deployment

```bash
# 1. Create Function App (if not exists)
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name $FUNCTION_APP_NAME \
  --storage-account $STORAGE_ACCOUNT

# 2. Deploy function code
cd function
func azure functionapp publish $FUNCTION_APP_NAME

# 3. Configure application settings (see Environment Configuration section)
```

### Method 3: Visual Studio Code

1. **Install Extensions**: Azure Functions extension
2. **Open Project**: Load the `/function` folder
3. **Deploy**: Use F1 > "Azure Functions: Deploy to Function App"
4. **Configure**: Set environment variables in Azure Portal

### Method 4: ZIP Deployment

```python
# Using the built-in deployment helper
from azure_function_helper import deploy_function_code

success, message, output = deploy_function_code(
    resource_group="my-rg",
    function_name="my-function-app",
    subscription_id="my-subscription-id"
)
```

## ⚙️ Environment Configuration

### Required Environment Variables

#### Core Function Settings
```bash
# Azure AI Search Configuration
SERVICE_NAME=your-search-service-name
INDEX_NAME=your-search-index-name

# Azure OpenAI Configuration  
OPENAI_ENDPOINT=https://your-openai-account.openai.azure.com
OPENAI_DEPLOYMENT=gpt-4o
API_VERSION=2025-01-01-preview

# Agent Configuration
AGENT_NAME=your-agent-name
RERANKER_THRESHOLD=2.0
MAX_OUTPUT_SIZE=16000
```

#### Optional Settings
```bash
# Debug and Development
debug=false
includesrc=true
TOP_K=5

# Function Infrastructure (Auto-configured)
APPLICATIONINSIGHTS_CONNECTION_STRING=<auto>
AzureWebJobsStorage=<auto>
```

### Configuration Methods

#### 1. Azure Portal Configuration
1. Navigate to **Function App** → **Configuration** → **Application settings**
2. Add each environment variable using **+ New application setting**
3. **Save** configuration and **restart** Function App

#### 2. Azure CLI Configuration
```bash
az functionapp config appsettings set \
  --name $FUNCTION_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    SERVICE_NAME=your-search-service \
    INDEX_NAME=your-index \
    OPENAI_ENDPOINT=https://your-openai.openai.azure.com \
    OPENAI_DEPLOYMENT=gpt-4o \
    API_VERSION=2025-01-01-preview \
    AGENT_NAME=your-agent \
    RERANKER_THRESHOLD=2.0
```

#### 3. Programmatic Configuration
```python
from azure_function_helper import push_function_settings

# Load settings from DataFrame or dict
success, message = push_function_settings(
    resource_group="my-rg",
    function_name="my-function",
    subscription_id="my-subscription",
    edited_df=settings_dataframe,
    original_raw=original_settings
)
```

## 🔐 RBAC and Authentication

### Managed Identity Setup

The Function App uses **Managed Identity** for secure authentication to Azure services.

#### Enable Managed Identity
```bash
# Enable system-assigned managed identity
az functionapp identity assign \
  --name $FUNCTION_APP_NAME \
  --resource-group $RESOURCE_GROUP
```

#### Required RBAC Roles

**Azure AI Search:**
```bash
# Search Index Data Contributor - for querying and managing indexes
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Search Index Data Contributor" \
  --scope $SEARCH_SERVICE_RESOURCE_ID

# Search Service Contributor - for service-level operations
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Search Service Contributor" \
  --scope $SEARCH_SERVICE_RESOURCE_ID
```

**Azure OpenAI:**
```bash
# Cognitive Services OpenAI User - for model inference
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Cognitive Services OpenAI User" \
  --scope $OPENAI_SERVICE_RESOURCE_ID
```

#### Automated RBAC Setup
```python
from azure_function_helper import assign_all_rbac_roles

success, message = assign_all_rbac_roles(
    subscription_id="your-subscription",
    function_app_name="your-function-app",
    resource_group="your-rg",
    search_service_name="your-search-service",
    openai_service_name="your-openai-account"
)
```

### Authentication Flow
```python
# The function automatically uses managed identity
from azure.identity import DefaultAzureCredential

# This works seamlessly in Azure Functions
credential = DefaultAzureCredential()

# No API keys needed in production
search_client = SearchClient(
    endpoint=search_endpoint,
    index_name=index_name,
    credential=credential
)
```

## 🧪 Testing and Validation

### Function URL and Key Retrieval
```python
from azure_function_helper import get_function_url_and_key

success, function_url, function_key, error = get_function_url_and_key(
    subscription_id="your-subscription",
    resource_group="your-rg", 
    function_app_name="your-function-app",
    function_name="AgentFunction"
)
```

### Test Function Call
```python
from azure_function_helper import generate_test_function_url

success, test_url, error = generate_test_function_url(
    subscription_id="your-subscription",
    resource_group="your-rg",
    function_app_name="your-function-app", 
    test_message="Hello world test",
    function_name="AgentFunction"
)

# Use the generated URL to test your function
import requests
response = requests.get(test_url)
```

### Validation Checklist
- [ ] **Function deployment** completed successfully
- [ ] **Environment variables** configured correctly
- [ ] **Managed identity** enabled and roles assigned
- [ ] **Function responds** to test requests
- [ ] **Azure services** accessible from function
- [ ] **Logs show** successful authentication
- [ ] **Performance** meets requirements

## 🐛 Troubleshooting

### Common Issues

#### 1. SSL Certificate Errors
```bash
# Error: SSL certificate verification failed
# Solution: Configure SSL bypass for private networks

# In deployment code:
env = os.environ.copy()
env['AZURE_CLI_DISABLE_CONNECTION_VERIFICATION'] = '1'
env['PYTHONHTTPSVERIFY'] = '0'
```

#### 2. Managed Identity Authentication Failures
```python
# Check if managed identity is enabled
az functionapp identity show \
  --name $FUNCTION_APP_NAME \
  --resource-group $RESOURCE_GROUP

# Verify RBAC assignments
az role assignment list \
  --assignee $PRINCIPAL_ID \
  --output table
```

#### 3. Missing Environment Variables
```python
# Use the configuration helper to identify missing variables
from tests.debug.configure_function_openai import print_function_app_settings
print_function_app_settings()
```

#### 4. Function Import Errors
```bash
# Check Python dependencies
cat function/requirements.txt

# Verify function structure
python3 -c "from function.AgentFunction import main"
```

#### 5. Deployment Timeouts
```python
# Alternative deployment methods for network issues
success, message, output = _try_alternative_deployment(
    resource_group="your-rg",
    function_name="your-function",
    zip_path=Path("function.zip")
)
```

### Debug Tools

#### Function Logs
```bash
# Stream function logs
az functionapp log tail \
  --name $FUNCTION_APP_NAME \
  --resource-group $RESOURCE_GROUP
```

#### Configuration Validation
```python
# Validate function configuration
from azure_function_helper import load_function_settings

success, df, raw_settings, error = load_function_settings(
    resource_group="your-rg",
    function_name="your-function", 
    subscription_id="your-subscription",
    env_vars={}
)

# Check for missing required settings
required_keys = ["SERVICE_NAME", "OPENAI_ENDPOINT", "OPENAI_DEPLOYMENT"]
missing = [key for key in required_keys if key not in raw_settings]
if missing:
    print(f"Missing required settings: {missing}")
```

## 📊 Monitoring and Logging

### Application Insights Integration
```json
{
  "APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=...",
  "APPINSIGHTS_INSTRUMENTATIONKEY": "...",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true
      }
    }
  }
}
```

### Performance Metrics
- **Function execution time**
- **Memory usage**
- **Request/response sizes**
- **Error rates**
- **Azure service call latency**

### Log Analysis Queries
```kusto
// Function execution time trends
requests
| where name == "AgentFunction"
| summarize avg(duration), count() by bin(timestamp, 1h)

// Error rate analysis  
exceptions
| where cloud_RoleName == "your-function-app"
| summarize count() by problemId, type
```

## 🔄 CI/CD Integration

### GitHub Actions Workflow
```yaml
name: Deploy Azure Function
on:
  push:
    branches: [main]
    paths: ['function/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          cd function
          pip install -r requirements.txt
          
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
          
      - name: Deploy Function
        run: |
          cd function
          func azure functionapp publish ${{ secrets.FUNCTION_APP_NAME }}
```

### Environment-Specific Deployments
```python
# Different configurations per environment
environments = {
    "dev": {
        "function_app_name": "my-function-dev",
        "search_service": "my-search-dev",
        "openai_account": "my-openai-dev"
    },
    "prod": {
        "function_app_name": "my-function-prod", 
        "search_service": "my-search-prod",
        "openai_account": "my-openai-prod"
    }
}
```

## 📚 Related Documentation

- **[🔐 Private Network Deployment](PRIVATE_NETWORK_DEPLOYMENT_GUIDE.md)** - Network security configuration
- **[🌐 AI Foundry Implementation](AI_FOUNDRY_FINAL_IMPLEMENTATION_SUMMARY.md)** - AI Foundry integration
- **[🏗️ Project Structure](PROJECT_STRUCTURE.md)** - Overall system architecture
- **[📊 SharePoint Integration](technical/sharepoint_indexing_flow_complete.md)** - SharePoint workflow integration

## 🎯 Best Practices

### Security
1. **Use Managed Identity** - Never store API keys in Function App settings
2. **Principle of Least Privilege** - Assign minimal required RBAC roles
3. **Network Isolation** - Deploy in private networks when possible
4. **Key Rotation** - Regularly rotate any API keys used for development
5. **Audit Logging** - Enable comprehensive logging for compliance

### Performance
1. **Connection Pooling** - Reuse Azure service clients across function calls
2. **Async Operations** - Use async/await for I/O operations
3. **Memory Management** - Monitor memory usage and optimize chunking
4. **Caching** - Cache frequently accessed data where appropriate
5. **Batch Processing** - Process multiple documents efficiently

### Reliability
1. **Error Handling** - Implement comprehensive error handling
2. **Retry Logic** - Use exponential backoff for transient failures
3. **Health Checks** - Implement function health monitoring
4. **Timeouts** - Configure appropriate timeout values
5. **Graceful Degradation** - Handle service unavailability gracefully

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] **Azure resources** provisioned (Function App, Storage, etc.)
- [ ] **Development environment** set up with required tools
- [ ] **Code tested** locally with Azure Functions Core Tools
- [ ] **Dependencies verified** in requirements.txt
- [ ] **Configuration validated** with required environment variables

### Deployment
- [ ] **Function code deployed** successfully
- [ ] **Environment variables configured** in Function App
- [ ] **Managed identity enabled** for Function App
- [ ] **RBAC roles assigned** for Azure services
- [ ] **Function accessible** via HTTP endpoint
- [ ] **Test calls successful** with expected responses

### Post-Deployment
- [ ] **Monitoring configured** with Application Insights
- [ ] **Log aggregation** working correctly
- [ ] **Performance baselines** established
- [ ] **Error alerting** configured
- [ ] **Documentation updated** with deployment specifics
- [ ] **CI/CD pipeline** tested (if applicable)

## 🎉 Success Indicators

### Functional Success
- [x] **Function deployment** completes without errors
- [x] **Authentication** works with managed identity
- [x] **Azure services** accessible from function
- [x] **Test queries** return expected results
- [x] **Error handling** works correctly for edge cases

### Performance Success
- [x] **Response times** under 30 seconds for complex queries
- [x] **Memory usage** stays within Function App limits
- [x] **Concurrent requests** handled efficiently
- [x] **Azure service calls** complete within timeout limits
- [x] **Resource utilization** optimized for cost

### Security Success
- [x] **No API keys** stored in configuration
- [x] **Managed identity** used for all Azure service calls
- [x] **Network access** properly restricted (if using private networking)
- [x] **RBAC permissions** follow least privilege principle
- [x] **Audit logs** capture all function executions

**Bottom Line**: A successful Azure Functions deployment provides **secure, scalable, and reliable** serverless compute for the Agentic RAG system, enabling **seamless integration** with Azure AI services through **managed identity authentication**.
