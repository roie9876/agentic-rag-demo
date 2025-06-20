# Health Check Module

This module provides health checking functionality for the Agentic RAG Demo application. It has been extracted from the main application file to improve code organization and maintainability.

## Structure

```
health_check/
├── __init__.py              # Module initialization
├── health_checker.py        # Core health checking logic
├── health_check_ui.py       # Streamlit UI components
└── README.md               # This file
```

## Classes

### HealthChecker

The `HealthChecker` class provides core health checking functionality for all services:

- **OpenAI**: Checks Azure OpenAI connectivity and model availability
- **AI Search**: Verifies Azure AI Search service connectivity and configuration
- **Document Intelligence**: Tests Azure Document Intelligence service availability

#### Methods

- `check_openai_health()` → `(bool, str)`: Check OpenAI service health
- `check_ai_search_health()` → `(bool, str)`: Check AI Search service health  
- `check_document_intelligence_health()` → `(bool, str)`: Check Document Intelligence service health
- `check_all_services()` → `(Dict, bool, Optional[Dict])`: Comprehensive health check

### HealthCheckUI

The `HealthCheckUI` class provides Streamlit UI components for health checking:

- Renders the complete health check tab interface
- Displays service status with troubleshooting information
- Provides environment variable inspection for failed services
- Includes blocking functionality for other tabs when health check fails

#### Methods

- `render_health_check_tab()`: Render the complete health check tab
- `health_block()`: Show warnings if health check hasn't passed (non-blocking)

## Usage

### Basic Health Checking

```python
from health_check import HealthChecker

# Initialize health checker
health_checker = HealthChecker()

# Check individual services
openai_ok, openai_msg = health_checker.check_openai_health()
search_ok, search_msg = health_checker.check_ai_search_health()
doc_ok, doc_msg = health_checker.check_document_intelligence_health()

# Comprehensive check
results, all_healthy, troubleshooting = health_checker.check_all_services()
```

### Streamlit UI Integration

```python
import streamlit as st
from health_check import HealthCheckUI

# In your Streamlit tab
with st.tab("Health Check"):
    health_ui = HealthCheckUI()
    health_ui.render_health_check_tab()

# In other tabs, show warnings if health check failed
def other_tab():
    health_ui = HealthCheckUI()
    health_ui.health_block()  # This will show warnings if health check failed
    
    # Your tab content here...
```

## Environment Variables

The health checker looks for these environment variables:

### OpenAI
- `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_ENDPOINT_41` / `AZURE_OPENAI_ENDPOINT_4o`
- `AZURE_OPENAI_KEY` / `AZURE_OPENAI_KEY_41` / `AZURE_OPENAI_KEY_4o`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT` / `AZURE_OPENAI_DEPLOYMENT_41`

### AI Search
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_KEY` (optional if using Azure AD authentication)

### Document Intelligence
- `DOCUMENT_INTEL_ENDPOINT` / `AZURE_FORMREC_SERVICE` / `AZURE_FORMRECOGNIZER_ENDPOINT`
- `DOCUMENT_INTEL_KEY` / `AZURE_FORMREC_KEY` / `AZURE_FORMRECOGNIZER_KEY`

## Features

- **Multi-endpoint support**: Tries different OpenAI endpoint configurations (_41, _4o, base)
- **Authentication flexibility**: Supports both API key and Azure AD authentication
- **Detailed diagnostics**: Provides specific error messages and troubleshooting steps
- **UI integration**: Ready-to-use Streamlit components
- **Warning system**: Shows helpful warnings when health check hasn't passed (non-blocking)

## Dependencies

- `azure-identity`
- `azure-search-documents`
- `openai`
- `streamlit` (for UI components)
- Custom `tools.document_intelligence_client` module

## Testing

Run the included test script to verify functionality:

```bash
python test_health_check.py
```

This will test both the core health checking logic and UI component initialization.
