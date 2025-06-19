# Agentic RAG Demo

A full‑stack demonstration of **retrieval‑augmented generation** (RAG) built on:

* **Azure Cognitive Search** – hybrid + vector index  
* **Azure OpenAI** – GPT‑4 / GPT‑4o for answer generation  
* **Azure Functions** – lightweight API wrapper the agent calls  
* **Streamlit** – local UI to manage the whole workflow

The UI lets you:

1. Upload documents → build a vector + keyword index  
2. Run ad‑hoc queries (“Test Retrieval”)  
3. Configure a Function App – push environment variables & zip‑deploy code  
4. Create an **AI Foundry Agent** whose OpenAPI schema points at the selected Function

---

## Quick‑start

```bash
git clone https://github.com/your‑org/agentic-rag-demo.git
cd agentic-rag-demo
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.template .env             # fill with your own values
streamlit run agentic-rag-demo.py
```

---

## Environment variables (`.env`)

Below are the main environment variables used by this project. **Do not use real secrets in documentation or commits.**

| Key | Example value (fake) | Description |
|-----|----------------------|-------------|
| `AZURE_OPENAI_ENDPOINT_41` | `https://my-openai-eastus.openai.azure.com/` | Azure OpenAI endpoint for GPT-4.1 |
| `AZURE_OPENAI_KEY_41` | `YOUR-OPENAI-KEY` | Azure OpenAI API key for GPT-4.1 |
| `AZURE_OPENAI_API_VERSION_41` | `2025-01-01-preview` | API version for GPT-4.1 deployment |
| `AZURE_OPENAI_DEPLOYMENT_41` | `gpt-4.1` | Model deployment name for GPT-4.1 |
| `AZURE_OPENAI_ENDPOINT` | `https://my-openai.openai.azure.com/` | Default Azure OpenAI endpoint |
| `AZURE_OPENAI_KEY` | `YOUR-OPENAI-KEY` | Default Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | `2025-01-01-preview` | Default OpenAI API version |
| `AZURE_OPENAI_SERVICE_NAME` | `my-openai` | Azure OpenAI resource name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-3-large` | Embedding model deployment name |
| `AZURE_OPENAI_CHATGPT_DEPLOYMENT` | `chat` | ChatGPT deployment name |
| `AGENT_FUNC_KEY` | `YOUR-FUNCTION-HOST-KEY` | Azure Function host key |
| `AZURE_SEARCH_ENDPOINT` | `https://my-search-eastus.search.windows.net` | Azure Cognitive Search endpoint |
| `AZURE_SEARCH_SERVICE` | `my-search-eastus` | Azure Cognitive Search service name |
| `SEARCH_API_KEY` | `YOUR-SEARCH-ADMIN-KEY` | Azure Cognitive Search admin key |
| `SERVICE_NAME` | `my-search-eastus` | Search service name (used by Function) |
| `PROJECT_ENDPOINT` | `https://my-aoai-resource.services.azure.com/api/projects/my-project` | AI Studio project endpoint (optional) |
| `MODEL_DEPLOYMENT_NAME` | `gpt-4.1` | Model deployment name (optional) |
| `API_VERSION` | `2025-05-01-preview` | API version for search runtime |
| `MAX_OUTPUT_SIZE` | `16000` | Max output token size |
| `OPENAI_ENDPOINT` | `https://my-openai.openai.azure.com` | OpenAI endpoint for Function calls |
| `OPENAI_KEY` | `YOUR-OPENAI-KEY` | OpenAI key for Function calls |
| `OPENAI_DEPLOYMENT` | `gpt-4.1` | Model deployment for Function calls |
| `RERANKER_THRESHOLD` | `1` | Reranker cut-off threshold |
| `includesrc` | `true` | Return raw chunks in results |
| `debug` | `false` | Enable extra logging |
| `TOP_K` | `5` | Default number of top results |
| `PDF_BASE_URL` | `https://my-storage.blob.core.windows.net/docs/` | (Optional) Base URL for PDF links |
| `AZURE_KEY_VAULT_NAME` | `my-keyvault` | Azure Key Vault name |
| `AZURE_KEY_VAULT_ENDPOINT` | `https://my-keyvault.vault.azure.net/` | Azure Key Vault endpoint |
| `AZURE_FORMREC_SERVICE` | `my-formrec-service` | Azure Document Intelligence service name |
| `AZURE_FORMREC_KEY` | `YOUR-FORMREC-KEY` | Azure Document Intelligence API key |
| `AZURE_FORMREC_ENDPOINT` | `https://my-formrec.cognitiveservices.azure.com` | (Optional) Document Intelligence endpoint |
| `SHAREPOINT_TENANT_ID` | `00000000-0000-0000-0000-000000000000` | SharePoint tenant ID |
| `SHAREPOINT_SITE_DOMAIN` | `mytenant.sharepoint.com` | SharePoint site domain |
| `SHAREPOINT_SITE_NAME` | `mysite` | SharePoint site name |
| `SHAREPOINT_DRIVE_NAME` | `Documents` | SharePoint drive name |
| `SHAREPOINT_SITE_FOLDER` | `/MyFolder` | SharePoint folder path |
| `SHAREPOINT_CONNECTOR_ENABLED` | `true` | Enable SharePoint connector |
| `SHAREPOINT_INDEX_DIRECT` | `true` | Directly index SharePoint files |
| `AZURE_SEARCH_SHAREPOINT_INDEX_NAME` | `my-index` | Search index for SharePoint files |
| `AGENTIC_APP_SPN_CLIENTID` | `00000000-0000-0000-0000-000000000000` | App registration client ID for SharePoint |
| `AGENTIC_APP_SPN_CERT_PATH` | `/path/to/cert.pfx` | Path to app registration certificate |
| `AGENTIC_APP_SPN_CERT_PASSWORD` | `your-cert-password` | Password for app registration certificate |
| `AZURE_TENANT_ID` | `00000000-0000-0000-0000-000000000000` | Azure tenant ID |

### Chunking/Tokenization
| Key | Example value | Description |
|-----|---------------|-------------|
| `NUM_TOKENS` | `2048` | Max tokens per chunk |
| `TOKEN_OVERLAP` | `100` | Overlap between chunks |
| `MIN_CHUNK_SIZE` | `100` | Minimum chunk size |

> Fill these once in `.env`. The **Function Config** tab can push them to the Function automatically.

---

## Required local tooling

| Tool | Purpose | Install |
|------|---------|---------|
| **Python 3.9+** | runs Streamlit UI | `pyenv`, Homebrew, Windows installer |
| **Azure CLI (`az`)** | deploy code / update app settings | <https://aka.ms/azure-cli> |
| **Git** | version control | <https://git-scm.com> |
| *(optional)* VS Code + Python ext. | editing & debugging | <https://code.visualstudio.com> |

Sign in: `az login` targeting the subscription that owns your Search, OpenAI and Function resources.

---

## Architecture

1. **Create Index** – chunk, embed and upload docs to a hybrid index  
2. **Test Retrieval** – BM25 + vector → GPT with inline citations  
3. **Function Config** – read/update app‑settings and zip‑deploy `/function/*`  
4. **AI Foundry Agent** – generates OpenAPI schema pointing at `https://<FUNCTION>.azurewebsites.net/api`

---

## License

MIT – free for personal or commercial use. Never commit real secrets!
