# Agent Function – local run

```bash
# 1. Create and activate venv
python -m venv .venv
source .venv/bin/activate                     # Windows: .venv\Scripts\activate

# 2. Install deps
pip install -r requirements.txt

# 3. Make sure local.settings.json exists (see template)
#    Contains SERVICE_NAME, AGENT_NAME, OpenAI keys, etc.

# 4. Start the Functions host
func start
```

You should see:

```
HttpFunctions:
        AgentFunction: [GET,POST] http://localhost:7071/api/AgentFunction
```

Invoke:

```bash
# Path parameter
curl "http://localhost:7071/api/AgentFunction/What%20is%20RAG?"

# Query-string (English)
curl "http://localhost:7071/api/AgentFunction?q=What%20is%20RAG?"

# Hebrew question – easiest with curl auto-encoding
curl --get --data-urlencode "q=מי הם חברי ועדת התמיכות" \
     http://localhost:7071/api/AgentFunction

# Hebrew with JSON POST (no encoding required)
curl -X POST http://localhost:7071/api/AgentFunction \
     -H "Content-Type: application/json" \
     -d '{"question":"מי הם חברי ועדת התמיכות"}'
```

Debugging in VS Code – simply press **F5** after installing the “Azure Functions” extension.

## ⚠️  Set required environment values

Update **local.settings.json** (or export vars in your terminal) **before running `func start`**:

### 🔐 Managed Identity Configuration (Recommended for Production)

```jsonc
"Values": {
  "SERVICE_NAME": "my-search-svc",
  "AGENT_NAME":  "my-agent",
  "OPENAI_ENDPOINT": "https://my-openai.openai.azure.com",
  "OPENAI_DEPLOYMENT": "gpt-4",
  "API_VERSION": "2025-01-01-preview",
  "INDEX_NAME": "my-index",
  "RERANKER_THRESHOLD": "2.0"
}
```

### 🔑 API Key Fallback (Development/Testing)

```jsonc
"Values": {
  "SERVICE_NAME": "my-search-svc", 
  "AGENT_NAME":  "my-agent",
  "OPENAI_ENDPOINT": "https://my-openai.openai.azure.com",
  "OPENAI_KEY": "******",
  "OPENAI_DEPLOYMENT": "gpt-4",
  "SEARCH_API_KEY": "******",
  "API_VERSION": "2025-01-01-preview",
  "INDEX_NAME": "my-index", 
  "RERANKER_THRESHOLD": "2.0"
}
```

Function host reloads on file-save, so just stop/start after editing.

## Environment variables

`local.settings.json` is **local-only**.  
When you publish, add the same keys to the Function App settings:

### Required for Managed Identity Setup

| Setting name              | Purpose                                | Required |
|---------------------------|----------------------------------------|----------|
| SERVICE_NAME              | Azure AI Search service name          | ✅       |
| AGENT_NAME                | Knowledge-agent name inside the service| ✅       |
| OPENAI_ENDPOINT           | OpenAI resource URL                    | ✅       |
| OPENAI_DEPLOYMENT         | Chat deployment name                   | ✅       |
| API_VERSION               | Search API version                     | ✅       |
| INDEX_NAME                | Default search index                   | ✅       |
| RERANKER_THRESHOLD        | Reranker threshold (default: 2.0)     | ❌       |

### Optional Fallback Credentials

| Setting name              | Purpose                                | Required |
|---------------------------|----------------------------------------|----------|
| SEARCH_API_KEY            | Search API key (fallback only)        | ❌       |
| OPENAI_KEY                | OpenAI API key (fallback only)        | ❌       |

### 🔐 Managed Identity RBAC Requirements

Before deployment, ensure your Function App's managed identity has these roles:

**Azure AI Search:**
- `Search Index Data Contributor`
- `Search Service Contributor`

**Azure OpenAI:**
- `Cognitive Services OpenAI User`

### CLI Deployment Example (Managed Identity)

```bash
az functionapp config appsettings set -g <rg> -n <func-app> --settings \
  SERVICE_NAME=ai-search-demo-eastus \
  AGENT_NAME=agentic-rag-agent \
  OPENAI_ENDPOINT=https://my-openai.openai.azure.com \
  OPENAI_DEPLOYMENT=gpt-4 \
  API_VERSION=2025-01-01-preview \
  INDEX_NAME=my-index \
  RERANKER_THRESHOLD=2.0
```

### CLI Deployment Example (API Keys Fallback)

```bash
az functionapp config appsettings set -g <rg> -n <func-app> --settings \
  SERVICE_NAME=ai-search-demo-eastus \
  AGENT_NAME=agentic-rag-agent \
  SEARCH_API_KEY=<admin-key> \
  OPENAI_ENDPOINT=https://my-openai.openai.azure.com \
  OPENAI_KEY=<openai-key> \
  OPENAI_DEPLOYMENT=gpt-4 \
  API_VERSION=2025-01-01-preview \
  INDEX_NAME=my-index
```

🔄 **Restart the Function App after updating the settings.**

### 🧪 Validate Setup

Run the validation script to test managed identity configuration:

```bash
python scripts/validate_managed_identity.py
```
