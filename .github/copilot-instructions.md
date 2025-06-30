# GitHub Copilot Instructions for Agentic RAG Demo

## 🎯 **Project Architecture Principle**

**CRITICAL**: Keep `agentic-rag-demo.py` MINIMAL and CLEAN. This file is becoming unmanageable at 2600+ lines. All new functionality should be placed in separate modules.

## 📋 **Core Rules for Code Organization**

### 1. **Main File Size Constraint**
- `agentic-rag-demo.py` should ONLY contain:
  - Essential imports and setup
  - Main UI orchestration (`run_streamlit_ui()`)
  - CLI entry point (`main()`)
  - **NO NEW BUSINESS LOGIC**

### 2. **Modular Development Strategy**
When implementing new features, create separate modules in these directories:

```
📁 CURRENT PROJECT STRUCTURE:
├── app/                     # UI components & processing
│   ├── ui/                 # UI components and layouts
│   │   └── components/     # Reusable UI components
│   ├── document_processing/ # Document processing modules
│   ├── openai/             # OpenAI-related functionality
│   └── search/             # Search-related functionality
├── core/                   # Core business logic
│   ├── azure_clients.py   # Azure service clients ✅
│   └── document_processor.py # Document processing ✅
├── utils/                  # Utility functions ✅
│   ├── azure_helpers.py   # Azure utilities ✅
│   ├── file_utils.py       # File operations ✅
│   └── file_format_detector.py # Format detection ✅
├── connectors/             # External integrations ✅
│   └── sharepoint/         # SharePoint integration ✅
├── health_check/           # Health check system ✅
│   ├── health_checker.py   # Health check logic ✅
│   └── health_check_ui.py  # Health check UI ✅
├── chunking/               # Document chunking system
├── scripts/                # Development and deployment scripts ✅
├── tests/                  # Test files
├── tools/                  # Development tools
└── docs/                   # Documentation

📁 RECOMMENDED FUTURE STRUCTURE:
├── app/tabs/               # Individual Streamlit tab modules (CREATE AS NEEDED)
├── services/               # Business services (CREATE AS NEEDED)
└── config/                 # Configuration management (CREATE AS NEEDED)
```

### 3. **Import Strategy**
Always import from modules, not inline code:

✅ **GOOD**:
```python
# In agentic-rag-demo.py
from app.tabs.test_retrieval_tab import render_test_retrieval_tab
from core.search_manager import SearchManager
from services.retrieval_service import AgenticRetrievalService
```

❌ **BAD**:
```python
# Adding 200+ lines of new code directly in agentic-rag-demo.py
def complex_new_feature():
    # ... lots of code ...
```

### 4. **Tab Implementation Pattern**
Each Streamlit tab should be a separate module:

```python
# app/tabs/my_new_tab.py
import streamlit as st
from typing import Dict, Any

def render_my_new_tab(
    session_state: Dict[str, Any],
    azure_clients: Dict[str, Any],
    **kwargs
) -> None:
    """Render the My New Feature tab."""
    st.header("🆕 My New Feature")
    
    # All tab logic here
    # ...
```

### 5. **Function Extraction Rules**

If you need to add a function to `agentic-rag-demo.py`, first check:

1. **Is it UI-related?** → Move to `app/components/`
2. **Is it Azure service-related?** → Move to `core/` or `utils/azure_helpers.py`
3. **Is it document processing?** → Move to `core/document_processor.py`
4. **Is it business logic?** → Move to `services/`

### 6. **Error Handling Strategy**
Create centralized error handling:

```python
# utils/error_handler.py
class AgenticRAGError(Exception):
    """Base exception for Agentic RAG Demo."""
    pass

def handle_azure_error(func):
    """Decorator for Azure service error handling."""
    # ...
```

## 🛠 **Development Patterns**

### Pattern 1: Adding New Azure Service Integration
```python
# core/azure_clients.py - ADD CLIENT HERE
def init_new_azure_service():
    """Initialize new Azure service client."""
    # ...

# services/new_service.py - ADD BUSINESS LOGIC HERE
class NewAzureService:
    def __init__(self, client):
        self.client = client
    
    def perform_operation(self):
        # ...

# agentic-rag-demo.py - MINIMAL IMPORT ONLY
from services.new_service import NewAzureService
```

### Pattern 2: Adding New UI Features
```python
# app/tabs/new_feature_tab.py
def render_new_feature_tab(**kwargs):
    """Complete tab implementation."""
    # All UI logic here

# agentic-rag-demo.py - JUST CALL THE RENDERER
with tab_new_feature:
    render_new_feature_tab(
        session_state=st.session_state,
        clients=azure_clients
    )
```

### Pattern 3: Adding Data Processing Logic
```python
# core/data_processor.py
class DataProcessor:
    def process_new_format(self, data):
        # Processing logic here
        
# services/processing_service.py  
class ProcessingService:
    def __init__(self):
        self.processor = DataProcessor()
    
    def handle_request(self, request):
        # Service orchestration here
```

## 📝 **Code Quality Standards**

### 1. **Type Hints**
Always use type hints:
```python
from typing import Dict, List, Optional, Tuple, Any

def process_documents(
    files: List[str], 
    config: Dict[str, Any]
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Process uploaded documents."""
    # ...
```

### 2. **Documentation**
Every new module needs:
```python
"""
Module: services/retrieval_service.py
Purpose: Handles agentic retrieval operations with Azure Search
Dependencies: core.azure_clients, utils.azure_helpers
"""
```

### 3. **Configuration Management**
Centralize configuration:
```python
# config/settings.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class AzureConfig:
    search_endpoint: str
    openai_endpoint: str
    # ...

def load_config() -> AzureConfig:
    """Load configuration from environment."""
    # ...
```

### 4. **Testing Structure**
```python
# tests/test_retrieval_service.py
import pytest
from services.retrieval_service import AgenticRetrievalService

class TestAgenticRetrievalService:
    def test_retrieve_documents(self):
        # Test implementation
```

## 🚫 **What NOT to Add to agentic-rag-demo.py**

1. **New Streamlit Components** - Use `app/components/`
2. **Azure Service Logic** - Use `core/` or `services/`
3. **Document Processing Functions** - Use `core/document_processor.py`
4. **Utility Functions** - Use `utils/`
5. **SharePoint Integration** - Use `connectors/sharepoint/`
6. **Complex Business Logic** - Use `services/`
7. **Data Validation** - Use `utils/validators.py`
8. **Error Handling** - Use `utils/error_handler.py`

## ✅ **What CAN be Added to agentic-rag-demo.py**

1. **Import statements only**
2. **Tab orchestration calls**
3. **Session state initialization**
4. **Basic configuration setup**
5. **Main entry points**

## 🔄 **Refactoring Guidelines**

When you see large functions in `agentic-rag-demo.py`:

1. **Extract** the function to appropriate module
2. **Create** a clean interface
3. **Import** and call from main file
4. **Test** the extraction works

Example refactoring:
```python
# OLD (in agentic-rag-demo.py)
def complex_sharepoint_processing():
    # 150 lines of code...

# NEW (in connectors/sharepoint/processor.py)
class SharePointProcessor:
    def process_documents(self):
        # 150 lines of code...

# NEW (in agentic-rag-demo.py)
from connectors.sharepoint.processor import SharePointProcessor
processor = SharePointProcessor()
```

## 📊 **Current Architecture State**

```
MAIN FILE STATUS: 🔴 CRITICAL (2600+ lines)
TARGET SIZE: 🟢 <500 lines (imports + orchestration only)

PRIORITY EXTRACTION TARGETS:
1. Test retrieval tab → app/tabs/test_retrieval_tab.py ✅ (DONE)
2. SharePoint processing → connectors/sharepoint/ ✅ (PARTIALLY DONE)
3. Document processing → core/document_processor.py ✅ (DONE)
4. Azure clients → core/azure_clients.py ✅ (DONE)
5. Health checks → health_check/ ✅ (DONE)
6. Index management → services/index_service.py ❌ (TODO)
7. Agent management → services/agent_service.py ❌ (TODO)
```

## 🎯 **Success Metrics**

- `agentic-rag-demo.py` under 500 lines
- Each module under 300 lines
- Clear separation of concerns
- Easy to maintain and extend
- Proper testing coverage

## 🚀 **Implementation Priority**

When implementing new features, follow this order:

1. **Design the module structure first**
2. **Create the module file**
3. **Implement the logic**
4. **Add proper imports to main file**
5. **Test the integration**
6. **Update documentation**

Remember: **Every line of new code should justify its placement in the main file. If it's not core orchestration, it belongs in a module.**
