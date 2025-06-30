# 🏗️ Modular Development Workflow

## Overview
This document describes the enforced workflow to prevent code bloat in `agentic-rag-demo.py` and maintain a clean, modular architecture.

## 🚫 CRITICAL RULE
**NEVER ADD NEW BUSINESS LOGIC TO `agentic-rag-demo.py`**

The main file should ONLY contain:
- Essential imports
- UI orchestration
- Entry points
- Configuration setup

## 🔧 Development Workflow

### 1. Before Starting Development
```bash
# Always run architecture validation before starting
python scripts/validate_modular_architecture.py
```

### 2. When Adding New Features
Follow this decision tree:

```
New Feature Needed?
├── UI Component?
│   ├── Tab? → Create in app/ui/ (or future app/tabs/)
│   └── Reusable Component? → Create in app/ui/components/
├── Business Logic?
│   ├── Azure Service? → Create in core/ (existing: azure_clients.py)
│   ├── Document Processing? → Add to core/document_processor.py ✅
│   ├── Health Checks? → Add to health_check/ ✅
│   └── General Service? → Create new service module
├── Utility Function?
│   ├── Azure-related? → Add to utils/azure_helpers.py ✅
│   ├── File operations? → Add to utils/file_utils.py ✅
│   └── General Utility? → Add to utils/
└── External Integration?
    ├── SharePoint? → Add to connectors/sharepoint/ ✅
    └── Other? → Create in connectors/
```

### 3. Module Creation Template

When creating a new module, use this template:

```python
"""
Module: path/to/module.py
Purpose: [Brief description of what this module does]
Dependencies: [List key dependencies]
Author: [Your name]
Created: [Date]
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ModuleName:
    """
    [Description of the class/module]
    
    Args:
        param1: Description
        param2: Description
    
    Example:
        >>> module = ModuleName(param1="value")
        >>> result = module.method()
    """
    
    def __init__(self, param1: str, param2: Optional[int] = None):
        self.param1 = param1
        self.param2 = param2
        
    def method(self) -> bool:
        """
        [Method description]
        
        Returns:
            bool: Success status
        """
        try:
            # Implementation here
            logger.info(f"Processing {self.param1}")
            return True
        except Exception as e:
            logger.error(f"Error in method: {e}")
            return False

# Module-level functions (if needed)
def utility_function(param: str) -> Dict[str, Any]:
    """Utility function description."""
    return {"result": param}
```

### 4. Integration with Main File

After creating a module, integrate it minimally:

```python
# In agentic-rag-demo.py - ONLY ADD IMPORTS
from app.tabs.new_feature_tab import render_new_feature_tab
from services.new_service import NewService

# In the appropriate section - ONLY ADD ORCHESTRATION
with tab_new_feature:
    render_new_feature_tab(
        session_state=st.session_state,
        clients=azure_clients
    )
```

### 5. Testing New Modules

Always test your modules:

```bash
# Run architecture validation
python scripts/validate_modular_architecture.py

# Run the application to test integration
streamlit run agentic-rag-demo.py

# Check for errors in VS Code Problems panel
```

## 🛠️ Available Tools

### VS Code Tasks
- **Validate Modular Architecture**: `Ctrl+Shift+P` → "Tasks: Run Task" → "Validate Modular Architecture"
- **Check Code Architecture**: Quick validation check

### Command Line Tools
```bash
# Full validation
python scripts/validate_modular_architecture.py

# Check current line count
wc -l agentic-rag-demo.py

# Git pre-commit hook (automatic)
git commit -m "Your changes"  # Will auto-run validation
```

### Configuration
Edit `.modular-architecture.toml` to adjust enforcement rules.

## 📊 Current Status

```
Main File Status: 🔴 CRITICAL (2613 lines)
Target Size: 🟢 <500 lines
Enforcement Mode: ⚠️ WARNING (see .modular-architecture.toml)
```

## 🎯 Migration Priorities

Current functions that should be extracted (in order):

1. **Large Functions (>100 lines)**:
   - `create_agentic_rag_index()` → `services/indexing_service.py`
   - `agentic_retrieval()` → `services/retrieval_service.py`

2. **Display Functions**:
   - `display_processing_info()` → `core/document_processor.py`

3. **Tab Rendering Functions** (if any exist):
   - Move to `app/tabs/`

## 🚨 Enforcement Mechanisms

### 1. Pre-commit Hook
Automatically runs validation before each commit. Will warn about violations.

### 2. VS Code Integration
Tasks available in Command Palette for quick validation.

### 3. Copilot Instructions
GitHub Copilot is configured to enforce these rules automatically.

### 4. Code Review Checklist
Use this checklist for all PRs:

- [ ] No new business logic added to `agentic-rag-demo.py`
- [ ] New code placed in appropriate modules
- [ ] Architecture validation passes
- [ ] Main file imports are clean and minimal
- [ ] New modules follow naming conventions
- [ ] Documentation updated

## 🔄 Refactoring Strategy

When refactoring existing code:

1. **Identify** the function/class to extract
2. **Create** the target module file
3. **Move** the code to the module
4. **Update** imports in main file
5. **Test** the integration
6. **Validate** with architecture checker

### Example Refactoring:

```bash
# Before: Function in main file (2613 lines)
# After: Function in module, import in main file

# 1. Create module (use existing structure)
touch core/indexing_service.py  # or appropriate existing directory

# 2. Move function to module
# ... (manual code movement)

# 3. Update main file import
# from core.indexing_service import create_agentic_rag_index

# 4. Validate
python scripts/validate_modular_architecture.py
```

## 📚 Resources

- **Architecture Guidelines**: `.github/copilot-instructions.md`
- **Validation Script**: `scripts/validate_modular_architecture.py`
- **Configuration**: `.modular-architecture.toml`
- **Pre-commit Hook**: `.git/hooks/pre-commit`

## 🎉 Success Metrics

- Main file under 500 lines
- Each module under 300 lines
- Clear separation of concerns
- Easy to maintain and extend
- Architecture validation passes

---

**Remember**: Every line of code added to the main file should be justified. If it's not core orchestration, it belongs in a module! 🏗️
