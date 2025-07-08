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
├── config/                 # Configuration management (CREATE AS NEEDED)
└── tests/                  # Test files, debug scripts, diagnostics
    ├── debug/              # Debug scripts (CREATE AS NEEDED)
    ├── diagnostics/        # Diagnostic scripts (CREATE AS NEEDED)
    ├── unit/               # Unit tests (CREATE AS NEEDED)
    └── integration/        # Integration tests (CREATE AS NEEDED)
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

**Testing Requirements:**
- Always use `python3` command for running tests and scripts
- Example: `python3 -m pytest tests/` instead of `python -m pytest tests/`
- Example: `python3 scripts/validate_architecture.py` instead of `python scripts/validate_architecture.py`

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

## 🧪 **Script Organization Policy**

### **Current State**: 
The main project directory contains many legacy debug, fix, diagnostic, and test scripts that will be cleaned up later. **DO NOT add new scripts to the root directory.**

### **New Script Placement Rules**:

#### 🔍 **Debug Scripts** → `tests/debug/`
- Resource group deletion debug scripts
- Azure service troubleshooting scripts  
- Network connectivity diagnostics
- Authentication debugging tools

#### 🩺 **Diagnostic Scripts** → `tests/diagnostics/`
- Health check scripts
- Performance analysis tools
- System status checkers
- Configuration validators

#### 🧪 **Test Scripts** → `tests/unit/` or `tests/integration/`
- Unit test files
- Integration test suites
- End-to-end test scenarios
- Mock data generators

#### 📋 **Utility Scripts** → `scripts/`
- Deployment scripts
- Setup/installation helpers
- Data migration tools
- Administrative utilities

### **Script Naming Convention**:
```
tests/debug/debug_<feature>_<issue>.py
tests/diagnostics/diagnose_<service>_<component>.py
tests/unit/test_<module>_<functionality>.py
tests/integration/test_<workflow>_<scenario>.py
scripts/<action>_<target>.py
```

### **Examples**:
```
✅ GOOD (New scripts):
tests/debug/debug_resource_group_deletion.py
tests/diagnostics/diagnose_azure_search_connectivity.py
tests/unit/test_document_processor_chunking.py
scripts/deploy_ai_foundry_project.py

❌ BAD (Root directory clutter):
debug_resource_group_deletion.py
fix_azure_search.py
test_new_feature.py
deployment_helper.py
```

### **Legacy Script Cleanup**:
- **Current root-level scripts will remain** for now and be addressed later
- **Do not move existing scripts** unless specifically requested
- **Focus on preventing new clutter** in the root directory

### **When Creating New Scripts**:
1. **Check if functionality belongs in an existing module first**
2. **Create in appropriate `tests/` subdirectory**
3. **Use descriptive, standardized naming**
4. **Include proper documentation header**
5. **Make executable with proper shebang**

## 📄 **Documentation Organization Policy**

### **Current State**: 
The main project directory contains many legacy status and implementation summary MD files. **These should be organized properly.**

### **Documentation Placement Rules**:

#### 📚 **Core Documentation** → **Stay in Root**
- `README.md` - Main project documentation
- `CHANGELOG.md` - Version history (if exists)
- `CONTRIBUTING.md` - Contribution guidelines (if exists)
- `LICENSE.md` - License information (if exists)

#### 📋 **Implementation Status/Summary Files** → `docs/status/`
- Implementation summaries (AI_FOUNDRY_IMPLEMENTATION_*.md)
- Deployment success summaries (AI_FOUNDRY_DEPLOYMENT_*.md)
- Integration completion reports (*_INTEGRATION_*.md)
- Fix/enhancement reports (*_FIX*.md, *_FIXES*.md)

#### 🔧 **Technical Documentation** → `docs/technical/`
- Architecture documentation
- API documentation
- Configuration guides
- Troubleshooting guides

#### 🎯 **Feature Documentation** → `docs/features/`
- Feature-specific documentation
- User guides for specific capabilities
- Feature implementation details

### **MD File Naming Convention**:
```
docs/status/ai_foundry_implementation_final_summary.md
docs/status/delete_deployment_integration_complete.md
docs/technical/dns_zone_configuration_guide.md
docs/features/enhanced_ai_foundry_capabilities.md
```

### **Examples**:
```
✅ GOOD (Organized structure):
README.md (root)
docs/status/ai_foundry_deployment_success_summary.md
docs/technical/dns_zone_resource_group_configuration.md
docs/features/delete_deployment_tab_integration.md

❌ BAD (Root directory clutter):
AI_FOUNDRY_DEPLOYMENT_SUCCESS_SUMMARY.md (root)
DELETE_DEPLOYMENT_INTEGRATION_FIXED.md (root)
DNS_ZONE_RESOURCE_GROUP_FIX_COMPLETE.md (root)
```

### **MD Files to Move**:

#### To `docs/status/`:
- `AI_FOUNDRY_CAPABILITY_HOST_DNS_FIXES.md`
- `AI_FOUNDRY_DEPLOYMENT_SUCCESS_SUMMARY.md`
- `AI_FOUNDRY_IMPLEMENTATION_FINAL_SUMMARY.md`
- `AI_FOUNDRY_UI_STATUS_DNS_ZONE_FIXES.md`
- `DELETE_DEPLOYMENT_INTEGRATION_FIXED.md`
- `DELETE_DEPLOYMENT_SERVICE_LINKS_FIX.md`
- `DELETE_DEPLOYMENT_TAB_INTEGRATION_COMPLETE.md`
- `DNS_ZONE_RESOURCE_GROUP_FIX_COMPLETE.md`
- `ENHANCED_DELETE_DEPLOYMENT_LEGIONSERVICELINK_FIX.md`

### **When Creating New Documentation**:
1. **Determine the documentation type** (core, status, technical, feature)
2. **Place in appropriate `docs/` subdirectory**
3. **Use lowercase, underscore-separated naming**
4. **Include proper front matter if using a documentation system**
5. **Keep README.md and other core docs in root**
