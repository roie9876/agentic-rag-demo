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

| Key | Example value (fake) | Where to find it in Azure |
|-----|----------------------|---------------------------|
| `AZURE_OPENAI_ENDPOINT_41` | `https://my-openai-eastus.openai.azure.com/` | **OpenAI resource → Keys & Endpoint** |
| `AZURE_OPENAI_KEY_41` | `YOUR-OPENAI-KEY` | same blade |
| `AZURE_OPENAI_API_VERSION_41` | `2025-01-01-preview` | API version |
| `AZURE_OPENAI_DEPLOYMENT_41` | `gpt-4.1` | **Model deployments → Name** |
| `AGENT_FUNC_KEY` | `YOUR-FUNCTION-HOST-KEY` | **Function App → Function Keys → `default`** |
| `AZURE_SEARCH_ENDPOINT` | `https://my-search-eastus.search.windows.net` | **Cognitive Search → Overview** |
| `PROJECT_ENDPOINT` | `https://my-aoai-resource.services.azure.com/api/projects/my-project` | only if using AI Studio “projects” |
| `MODEL_DEPLOYMENT_NAME` | `gpt-4.1` | same as deployment name |

### Variables pushed to the Function App

| Key | Purpose |
|-----|---------|
| `API_VERSION` | search runtime version (`2025-05-01-preview`) |
| `AZURE_OPENAI_API_VERSION` | OpenAI API version |
| `MAX_OUTPUT_SIZE` | token cap (16 000 default) |
| `OPENAI_ENDPOINT`, `OPENAI_KEY`, `OPENAI_DEPLOYMENT` | AOAI creds the Function calls |
| `SERVICE_NAME` | search service name (e.g. `my-search-eastus`) |
| `SEARCH_API_KEY` | search admin key |
| `RERANKER_THRESHOLD` | reranker cut‑off |
| `includesrc` | `true` → return raw chunks |
| `debug` | extra logging |
| `AGENT_FUNC_KEY` | host key used by the agent |

> Fill these once in `.env`; the **Function Config** tab can push them to the Function automatically.

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
