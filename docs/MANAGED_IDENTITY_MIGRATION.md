# Managed Identity Migration Guide

## 🔐 Migrating from API Keys to Managed Identity

This guide helps you migrate your Azure Function from API key authentication to managed identity for enhanced security.

## ✅ Benefits of Managed Identity

- **Enhanced Security**: No API keys to manage, rotate, or accidentally expose
- **Simplified Management**: Azure handles credential lifecycle automatically  
- **RBAC Integration**: Fine-grained access control with Azure role-based access
- **Audit Trail**: Better tracking of service access through Azure Activity Log
- **Zero Downtime**: Fallback support allows gradual migration

## 📋 Prerequisites

1. **Azure Function App** with system-assigned managed identity enabled
2. **Azure AI Search** service with RBAC enabled
3. **Azure OpenAI** service with RBAC enabled
4. **Appropriate permissions** to assign RBAC roles

## 🚀 Migration Steps

### Step 1: Enable Managed Identity

```bash
# Enable system-assigned managed identity on Function App
az functionapp identity assign \
  --resource-group <your-rg> \
  --name <your-function-app>
```

Or via Azure Portal:
1. Go to your Function App
2. Navigate to **Identity** → **System assigned**
3. Toggle **Status** to **On**
4. Click **Save**

### Step 2: Assign RBAC Roles

#### For Azure AI Search:

```bash
# Get the Function App's principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --resource-group <your-rg> \
  --name <your-function-app> \
  --query principalId -o tsv)

# Get your Search service resource ID
SEARCH_ID=$(az search service show \
  --resource-group <your-rg> \
  --name <your-search-service> \
  --query id -o tsv)

# Assign Search Index Data Contributor role
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Search Index Data Contributor" \
  --scope $SEARCH_ID

# Assign Search Service Contributor role  
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Search Service Contributor" \
  --scope $SEARCH_ID
```

#### For Azure OpenAI:

```bash
# Get your OpenAI service resource ID
OPENAI_ID=$(az cognitiveservices account show \
  --resource-group <your-rg> \
  --name <your-openai-service> \
  --query id -o tsv)

# Assign Cognitive Services OpenAI User role
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Cognitive Services OpenAI User" \
  --scope $OPENAI_ID
```

### Step 3: Update Environment Variables

#### Remove These Variables (API Keys):
- `AZURE_OPENAI_KEY` / `OPENAI_KEY`
- `AZURE_SEARCH_KEY` / `SEARCH_API_KEY`

#### Update These Variables (Endpoint Format):
- `AZURE_OPENAI_ENDPOINT` → `OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT` → `OPENAI_DEPLOYMENT`

#### Example Update:

**Before (API Keys):**
```bash
az functionapp config appsettings set \
  --resource-group <your-rg> \
  --name <your-function-app> \
  --settings \
    AZURE_OPENAI_KEY="sk-..." \
    SEARCH_API_KEY="abcd..." \
    AZURE_OPENAI_ENDPOINT="https://my-openai.openai.azure.com" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4"
```

**After (Managed Identity):**
```bash
az functionapp config appsettings set \
  --resource-group <your-rg> \
  --name <your-function-app> \
  --settings \
    OPENAI_ENDPOINT="https://my-openai.openai.azure.com" \
    OPENAI_DEPLOYMENT="gpt-4"

# Remove the API keys
az functionapp config appsettings delete \
  --resource-group <your-rg> \
  --name <your-function-app> \
  --setting-names AZURE_OPENAI_KEY SEARCH_API_KEY
```

### Step 4: Deploy Updated Code

1. **Deploy the updated function code** that supports managed identity
2. **Restart the Function App** to pick up new settings
3. **Test the function** to ensure it works with managed identity

### Step 5: Validate Setup

Run the validation script:

```bash
python scripts/validate_managed_identity.py
```

## 🧪 Testing the Migration

### Test Locally (Development)

For local testing, you can keep API keys in `local.settings.json`:

```json
{
  "Values": {
    "SERVICE_NAME": "my-search-service",
    "AGENT_NAME": "my-agent",
    "OPENAI_ENDPOINT": "https://my-openai.openai.azure.com",
    "OPENAI_KEY": "sk-...",
    "OPENAI_DEPLOYMENT": "gpt-4",
    "SEARCH_API_KEY": "abcd...",
    "INDEX_NAME": "my-index"
  }
}
```

### Test in Azure (Production)

For Azure deployment, only managed identity will be used:

```bash
# Test the function endpoint
curl "https://<your-function-app>.azurewebsites.net/api/AgentFunction?q=test"
```

## 🔄 Rollback Plan

If you need to rollback to API keys:

1. **Re-add API key environment variables**
2. **Deploy previous version of function code** (if needed)
3. **Restart Function App**

The updated code maintains backward compatibility with API keys as fallback.

## 📊 Environment Variable Comparison

| Category | API Keys (Old) | Managed Identity (New) |
|----------|----------------|------------------------|
| **Authentication** | API Keys | Azure RBAC |
| **Search Auth** | `SEARCH_API_KEY` | Managed Identity |
| **OpenAI Auth** | `OPENAI_KEY` | Managed Identity |
| **Search Endpoint** | `AZURE_SEARCH_ENDPOINT` | `SERVICE_NAME` |
| **OpenAI Endpoint** | `AZURE_OPENAI_ENDPOINT` | `OPENAI_ENDPOINT` |
| **OpenAI Model** | `AZURE_OPENAI_DEPLOYMENT` | `OPENAI_DEPLOYMENT` |
| **Security** | Keys in config | RBAC only |
| **Maintenance** | Manual key rotation | Automatic |

## ❗ Common Issues

### Issue: "No Search authentication available"
**Solution**: Verify managed identity is enabled and RBAC roles are assigned

### Issue: "Failed to initialize OpenAI with managed identity"  
**Solution**: Check that `Cognitive Services OpenAI User` role is assigned

### Issue: "Access denied" errors
**Solution**: Wait 5-10 minutes for RBAC role assignments to propagate

### Issue: Function works locally but fails in Azure
**Solution**: Ensure environment variables are set in Function App settings, not just `local.settings.json`

## 🎯 Final Checklist

- [ ] Managed identity enabled on Function App
- [ ] RBAC roles assigned for Azure AI Search
- [ ] RBAC roles assigned for Azure OpenAI  
- [ ] Environment variables updated
- [ ] API keys removed from production settings
- [ ] Function code deployed and tested
- [ ] Validation script passes
- [ ] Function endpoint responds correctly

## 📚 Additional Resources

- [Azure Function Managed Identity](https://docs.microsoft.com/en-us/azure/app-service/overview-managed-identity)
- [Azure AI Search RBAC](https://docs.microsoft.com/en-us/azure/search/search-security-rbac)
- [Azure OpenAI RBAC](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/how-to/role-based-access-control)
