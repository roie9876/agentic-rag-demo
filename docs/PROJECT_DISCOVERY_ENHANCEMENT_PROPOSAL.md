# AI Foundry Project Discovery Enhancement Proposal

## Current State

The app currently supports:
- ✅ **AI Foundry Hubs** discovery via Azure Management API
- ✅ **Projects within Hubs** discovery via Azure ML API
- ❌ **AI Foundry Accounts** (not supported - no public APIs)

## Enhancement Opportunities

### 1. Automatic Endpoint Generation for Hub Projects

For discovered projects in AI Foundry Hubs, we could automatically generate the PROJECT_ENDPOINT:

```python
def generate_project_endpoint(project: AIFoundryProject) -> str:
    """Generate PROJECT_ENDPOINT for a hub-based project."""
    # For hub projects, the endpoint might be constructable
    # but needs verification with Azure documentation
    return f"https://{project.location}.api.azureml.ms/projects/{project.name}"
```

**Challenges:**
- Endpoint format not documented for hub projects
- May not work with the AI Projects SDK
- Needs testing with real hub projects

### 2. Enhanced Hub Project Management

```python
def enhanced_hub_project_workflow(hub: AIFoundryHub) -> Dict[str, Any]:
    """Enhanced workflow for hub-based projects."""
    projects = discover_projects_for_hub(hub)
    
    for project in projects:
        # Try to generate endpoint
        endpoint = generate_project_endpoint(project)
        
        # Test if endpoint works with AI Projects SDK
        try:
            test_client = AIProjectClient(
                credential=credential,
                endpoint=endpoint
            )
            # If successful, project is ready for agent creation
        except Exception:
            # Fallback to Azure Portal guidance
            pass
```

### 3. Clear User Guidance

Add better messaging in the UI:

```python
def render_project_discovery_guidance():
    st.info("""
    **AI Foundry Project Discovery:**
    
    ✅ **AI Foundry Hubs**: Projects can be discovered automatically
    ❌ **AI Foundry Accounts**: Manual PROJECT_ENDPOINT required
    
    If you have an AI Foundry Account, please:
    1. Go to Azure Portal → Your AI Foundry Account → Projects
    2. Copy the PROJECT_ENDPOINT from your project
    3. Paste it in the manual entry field below
    """)
```

## Implementation Priority

### Phase 1: Documentation and Guidance
1. ✅ Update UI with clear messaging about Hub vs Account differences
2. ✅ Add helpful links to Azure Portal for Account users
3. ✅ Improve error messages when discovery fails

### Phase 2: Enhanced Hub Support
1. 🔄 Test endpoint generation for hub projects
2. 🔄 Validate compatibility with AI Projects SDK
3. 🔄 Add automatic endpoint generation if successful

### Phase 3: Future Improvements
1. 🔮 Monitor for Microsoft API updates
2. 🔮 Consider Azure Resource Graph queries for enhanced discovery
3. 🔮 Explore alternative authentication methods

## Technical Notes

### Why AI Foundry Accounts Can't Be Discovered

From Microsoft's documentation and our analysis:
- AI Foundry Accounts use `Microsoft.CognitiveServices/accounts` resource type
- No public REST APIs for project management
- Management must be done through Azure Portal
- This is a deliberate design choice by Microsoft

### Azure Resource Graph Alternative

Could potentially use Azure Resource Graph to find resources:

```python
def discover_via_resource_graph():
    """Alternative discovery using Azure Resource Graph."""
    query = """
    Resources
    | where type == "microsoft.cognitiveservices/accounts"
    | where properties.kind == "AIFoundry"
    """
    # This might help find AI Foundry Accounts, but still no project discovery
```

**Limitations:**
- Still wouldn't provide project-level discovery
- Still wouldn't provide PROJECT_ENDPOINT
- Users would still need manual endpoint entry

## Conclusion

**AI Foundry Hubs**: ✅ Project discovery already works
**AI Foundry Accounts**: ❌ PROJECT_ENDPOINT will always be required

The app should focus on improving the Hub experience and providing clear guidance for Account users.
