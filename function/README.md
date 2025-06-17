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

```jsonc
"Values": {
  "SERVICE_NAME": "my-search-svc",
  "AGENT_NAME":  "my-agent",
  "AZURE_OPENAI_ENDPOINT": "https://my-openai.openai.azure.com",
  "AZURE_OPENAI_KEY": "******",
  "AZURE_OPENAI_DEPLOYMENT": "chat",
  "AZURE_OPENAI_API_VERSION": "2024-02-15-preview"
}
```
Function host reloads on file-save, so just stop/start after editing.

## Environment variables

`local.settings.json` is **local-only**.  
When you publish, add the same keys to the Function App settings:

| Setting name              | Purpose                                |
|---------------------------|----------------------------------------|
| SERVICE_NAME              | Azure AI Search service name           |
| AGENT_NAME                | Knowledge-agent name inside the service|
| SEARCH_API_KEY *or* Managed Identity | Search authentication       |
| AZURE_OPENAI_ENDPOINT     | OpenAI resource URL                    |
| AZURE_OPENAI_KEY          | OpenAI key                             |
| AZURE_OPENAI_DEPLOYMENT   | Chat deployment name                   |
| AZURE_OPENAI_API_VERSION  | API version                            |

CLI example:

```bash
az functionapp config appsettings set -g <rg> -n <func-app> --settings \
  SERVICE_NAME=ai-serach-demo-eastus \
  AGENT_NAME=agentic-rag-agent \
  SEARCH_API_KEY=<admin-key> \
  AZURE_OPENAI_ENDPOINT=https://admin-m845f4ec-eastus2.openai.azure.com \
  AZURE_OPENAI_KEY=<openai-key> \
  AZURE_OPENAI_DEPLOYMENT=gpt-4.1 \
  AZURE_OPENAI_API_VERSION=2025-01-01-preview
```

Restart the Function App after updating the settings.
