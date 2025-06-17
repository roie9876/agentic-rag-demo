#!/usr/bin/env python3
"""
agentic-rag-demo.py
===================
CLI demo of Agentic Retrieval‑Augmented Generation on Azure
compatible with **openai‑python ≥ 1.0**.

Based on the official quick‑start:
https://learn.microsoft.com/azure/search/search-get-started-agentic-retrieval?pivots=python
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import subprocess   # for az cli calls
import httpx  # HTTP probe for RBAC status
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Streamlit Data‑Editor helper (works on both old & new versions)
# ---------------------------------------------------------------------------
import streamlit as st

def _st_data_editor(*args, **kwargs):
    """
    Wrapper that tries st.data_editor (Streamlit ≥ 1.29) and falls back to
    st.experimental_data_editor for older releases.
    """
    if hasattr(st, "data_editor"):
        return st.data_editor(*args, **kwargs)
    elif hasattr(st, "experimental_data_editor"):
        return st.experimental_data_editor(*args, **kwargs)
    else:
        st.error(
            "⚠️ Your Streamlit version is too old for data‑editor. "
            "Upgrade with:\n\n"
            "    pip install --upgrade streamlit"
        )
        st.stop()
# Reliable check whether code runs under `streamlit run …`
try:
    from streamlit.runtime import exists as _st_in_runtime
except ImportError:       # fallback for older Streamlit
    _st_in_runtime = lambda: False

import re  # for citation parsing
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient  # NEW
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    KnowledgeAgent,
    KnowledgeAgentAzureOpenAIModel,
    KnowledgeAgentTargetIndex,
    KnowledgeAgentRequestLimits,
)

# --- Logging setup ---
import logging
import inspect
# Show only warnings and errors in the terminal
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# Knowledge‑agent runtime
from azure.search.documents.agent import KnowledgeAgentRetrievalClient
from azure.search.documents.agent.models import (
    KnowledgeAgentRetrievalRequest,
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    KnowledgeAgentIndexParams,
)
from dotenv import load_dotenv

from azure.search.documents import SearchIndexingBufferedSender  # NEW
import fitz                            # PyMuPDF
import hashlib, tempfile               # for PDF processing
import zipfile
from azure.identity import AzureCliCredential, get_bearer_token_provider
from azure.ai.projects import AIProjectClient
# --- Azure AI Foundry SDK ----------------------------------------------------
# Support multiple SDK generations where the tool classes moved packages/names
try:
    # GA / recent preview: everything under azure.ai.agents
    from azure.ai.agents import FunctionTool, FunctionDefinition
except ImportError:
    # Older builds may expose FunctionTool and/or FunctionDefinition
    # under azure.ai.agents.models
    try:
        from azure.ai.agents import FunctionTool  # type: ignore
    except ImportError:
        FunctionTool = None  # type: ignore
    try:
        from azure.ai.agents.models import FunctionTool as _FTModel, FunctionDefinition  # type: ignore
        if FunctionTool is None:  # fallback when only the models version exists
            FunctionTool = _FTModel  # type: ignore
    except ImportError:
        FunctionDefinition = None  # type: ignore

# OpenAPI tool helper (available in azure‑ai‑agents ≥ 1.0.0b2)
from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails


# ToolDefinition is only under .models
def _search_credential() -> AzureKeyCredential | DefaultAzureCredential:
    """
    Return Azure credential based on env:
    • If AZURE_SEARCH_KEY is set → key auth
    • else → DefaultAzureCredential (AAD)
    """
    key = os.getenv("AZURE_SEARCH_KEY", "").strip()
    if key:
        return AzureKeyCredential(key)
    return DefaultAzureCredential()


# ---------------------------------------------------------------------------
# RBAC status probe
# ---------------------------------------------------------------------------
def _rbac_enabled(service_url: str) -> bool:
    """
    Quick probe: return True if Role‑based access control is enabled on the
    Search service (Authentication mode = RBAC).
    """
    try:
        url = f"{service_url.rstrip('/')}/?api-version=2023-11-01"
        r = httpx.get(url, timeout=3)
        # When RBAC is ON the payload includes "RoleBasedAccessControl"
        return "RoleBasedAccessControl" in r.text
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Azure CLI helpers
# ---------------------------------------------------------------------------
def _az_logged_user() -> tuple[str | None, str | None]:
    """Return (UPN/email, subscription-id) of the signed‑in az cli user, or (None,None)."""
    try:
        out = subprocess.check_output(
            ["az", "account", "show", "--output", "json"], text=True, timeout=3
        )
        data = json.loads(out)
        return data["user"]["name"], data["id"]
    except Exception:
        return None, None


def check_azure_cli_login() -> tuple[bool, dict | None]:
    """
    Return (logged_in, account_json_or_None) by running `az account show`.
    """
    try:
        out = subprocess.check_output(
            ["az", "account", "show", "--output", "json"],
            text=True,
            timeout=5,
        )
        return True, json.loads(out)
    except subprocess.CalledProcessError:
        return False, None
    except Exception:
        return False, None


def get_ai_foundry_projects(cred: AzureCliCredential) -> list[dict]:
    """
    Return a list of Foundry projects visible to the signed‑in CLI user via
    `az ai project list`. Each item includes:
        {name, location, endpoint, resource_group, hub_name}
    """
    try:
        out = subprocess.check_output(
            ["az", "ai", "project", "list", "--output", "json"],
            text=True,
            timeout=10,
        )
        data = json.loads(out)
        projs = []
        for p in data:
            projs.append(
                {
                    "name": p["name"],
                    "location": p["location"],
                    "endpoint": p["properties"]["endpoint"],
                    "resource_group": p["resourceGroup"],
                    "hub_name": p["properties"].get("hubName", ""),
                }
            )
        return projs
    except Exception as err:
        logging.warning("Failed to list AI Foundry projects: %s", err)
        return []


def _grant_search_role(service_name: str, subscription_id: str, resource_group: str, principal: str, role: str) -> tuple[bool, str]:
    """
    Grant the specified *role* to *principal* on the given service.
    Returns (success, message).
    """
    try:
        scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Search/searchServices/{service_name}"
        subprocess.check_call(
            [
                "az", "role", "assignment", "create",
                "--role", role,
                "--assignee", principal,
                "--scope", scope
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        return True, "Role granted successfully"
    except subprocess.CalledProcessError as e:
        return False, f"az cli error: {e}"
    except Exception as ex:
        return False, str(ex)

# ---------------------------------------------------------------------------
# Zip local ./function folder for deployment
# ---------------------------------------------------------------------------
def _zip_function_folder() -> str:
    """
    Create a temp .zip archive of the ./function folder and return its path.
    """
    func_dir = Path(__file__).resolve().parent / "function"
    if not func_dir.exists():
        raise FileNotFoundError("Local 'function' folder not found.")
    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in func_dir.rglob("*"):
            if p.is_file():
                # keep path relative to "function" folder so host.json at zip root
                zf.write(p, p.relative_to(func_dir))
    return tmp_zip.name
# ---------------------------------------------------------------------------
# Helper to grant OpenAI role
# ---------------------------------------------------------------------------
def _grant_openai_role(account_name: str, subscription_id: str, resource_group: str,
                       principal: str, role: str = "Cognitive Services OpenAI User") -> tuple[bool, str]:
    """
    Grant *role* (default: Cognitive Services OpenAI User) on the Azure OpenAI
    account to *principal*.
    """
    try:
        scope = (
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
        )
        subprocess.check_call(
            [
                "az", "role", "assignment", "create",
                "--role", role,
                "--assignee", principal,
                "--scope", scope,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        return True, "Role granted successfully"
    except subprocess.CalledProcessError as e:
        return False, f"az cli error: {e}"
    except Exception as ex:
        return False, str(ex)

# ---------------------------------------------------------------------------
# Force‑reload .env at runtime
# ---------------------------------------------------------------------------
def _reload_env_and_restart():
    """
    Reload the .env file (override existing variables), clear cached clients,
    and rerun the Streamlit script so the new values take effect.
    """
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path, override=True)

    # Clear Streamlit caches for resource‑building functions
    for fn in (init_openai, init_search_client, init_agent_client):
        if hasattr(fn, "clear"):
            fn.clear()

    st.toast("✅ .env reloaded – restarting app…", icon="🔄")
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # fallback for older versions
        st.experimental_rerun()

##############################################################################
# Environment helpers
##############################################################################

load_dotenv(Path(__file__).resolve().parent / ".env")
FUNCTION_KEY = os.getenv("AGENT_FUNC_KEY", "")
TOP_K_DEFAULT = int(os.getenv("TOP_K", 5))   # fallback for CLI path


def env(var: str) -> str:
    """Fetch env var or exit with error."""
    v = os.getenv(var)
    if not v:
        sys.exit(f"❌ Missing env var: {var}")
    return v


def init_openai(model: str = "o3") -> Tuple[AzureOpenAI, dict]:
    """
    Return AzureOpenAI client + chat params for the chosen *model*
    (o3, 4o, 41).  Picks env‑vars with appropriate suffix.
    """
    suffix = {"o3": "", "4o": "_4o", "41": "_41"}.get(model, "")
    client = AzureOpenAI(
        api_key=env(f"AZURE_OPENAI_KEY{suffix}"),
        azure_endpoint=env(f"AZURE_OPENAI_ENDPOINT{suffix}").rstrip("/"),
        api_version=env(f"AZURE_OPENAI_API_VERSION{suffix}"),
    )
    # If no API key, use AAD token provider
    if not os.getenv(f"AZURE_OPENAI_KEY{suffix}", "").strip():
        # Switch to AAD token provider
        aad = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        client = AzureOpenAI(
            azure_endpoint=env(f"AZURE_OPENAI_ENDPOINT{suffix}").rstrip("/"),
            azure_ad_token_provider=aad,
            api_version=env(f"AZURE_OPENAI_API_VERSION{suffix}"),
        )
    chat_params = dict(
        model=env(f"AZURE_OPENAI_DEPLOYMENT{suffix}"),
        temperature=0,
        max_tokens=st.session_state.get("max_tokens", 20000),
    )
    return client, chat_params


def embed_text(oai_client: AzureOpenAI, deployment: str, text: str) -> list[float]:
    """Return embedding vector for *text* using the specified deployment."""
    resp = oai_client.embeddings.create(input=[text], model=deployment)
    return resp.data[0].embedding


def pdf_to_documents(pdf_file, oai_client: AzureOpenAI, embed_deployment: str) -> list[dict]:
    """
    Extract pages from an uploaded PDF and return list of documents matching
    the quick‑start index schema.
    """
    docs = []
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.getbuffer())
        tmp_path = tmp.name

    pdf = fitz.open(tmp_path)
    for page_num in range(len(pdf)):
        page_text = pdf[page_num].get_text().strip()
        page_text = f"[{pdf_file.name}] " + page_text
        if not page_text:
            continue
        vector = embed_text(oai_client, embed_deployment, page_text)
        # Build a public-facing link to the PDF (example: blob storage)
        pdf_url = os.getenv("PDF_BASE_URL", "") + pdf_file.name
        doc = {
            "id": hashlib.md5(f"{pdf_file.name}_{page_num}".encode()).hexdigest(),
            "page_chunk": page_text,
            "page_embedding_text_3_large": vector,
            "page_number": page_num + 1,
            "source_file": pdf_file.name,
            "source": pdf_file.name,             # extra alias recognised by agent
            "url": pdf_url,
        }
        docs.append(doc)
    pdf.close()
    return docs


def init_search_client(index_name: str | None = None) -> Tuple[SearchClient, SearchIndexClient]:
    """
    Return (search_client, index_client).

    `index_name` – if provided, SearchClient will target that index,
    otherwise a dummy client pointing at the service root is returned.
    """
    endpoint = env("AZURE_SEARCH_ENDPOINT")
    credential = _search_credential()

    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

    if index_name:
        search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    else:
        # Return a SearchClient bound to some default index just to keep type happy.
        # Caller should create a proper one later.
        search_client = SearchClient(endpoint=endpoint, index_name="dummy", credential=credential)

    # Improved index listing debug
    try:
        available_indexes = list(index_client.list_indexes())
        st.session_state.available_indexes = [idx.name for idx in available_indexes]
    except Exception as conn_error:
        logging.error("list_indexes() failed: %s", conn_error)
        st.session_state.available_indexes = []

    return search_client, index_client

# ---------------------------------------------------------------------------
# Knowledge‑Agent client (cached per agent name)
# ---------------------------------------------------------------------------
@st.cache_resource
def init_agent_client(agent_name: str) -> KnowledgeAgentRetrievalClient:
    """
    Create KnowledgeAgentRetrievalClient.
    • If we have an Admin Key → use it.
    • Otherwise rely on DefaultAzureCredential (AAD token).
      (The SDK itself will request the token with the proper scope.)
    """
    cred = _search_credential()   # Either AzureKeyCredential or DefaultAzureCredential
    return KnowledgeAgentRetrievalClient(
        endpoint=env("AZURE_SEARCH_ENDPOINT"),
        agent_name=agent_name,
        credential=cred,
    )


def create_agentic_rag_index(index_client: "SearchIndexClient", name: str) -> bool:
    """
    Create (or recreate) an index identical to the quick‑start example:
    https://learn.microsoft.com/azure/search/search-get-started-agentic-retrieval?pivots=python
    """
    try:
        # --- configurable bits pulled from environment ----------------------
        azure_openai_endpoint   = env("AZURE_OPENAI_ENDPOINT_41")  # or without suffix
        embedding_deployment    = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        embedding_model         = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL",      "text-embedding-3-large")
        VECTOR_DIM              = 3072
        # --------------------------------------------------------------------

        index_schema = SearchIndex(
            name=name,
            fields=[
                SearchField(name="id",
                            type="Edm.String",
                            key=True,
                            filterable=True,
                            sortable=True,
                            facetable=True),
                SearchableField(
                    name="page_chunk",
                    type="Edm.String",
                    analyzer_name="standard.lucene",
                    filterable=False,
                    sortable=False,
                    facetable=False),
                SearchField(name="page_embedding_text_3_large",
                            type="Collection(Edm.Single)",
                            stored=False,
                            vector_search_dimensions=VECTOR_DIM,
                            vector_search_profile_name="hnsw_text_3_large"),
                SearchField(name="page_number",
                            type="Edm.Int32",
                            filterable=True,
                            sortable=True,
                            facetable=True),
                SimpleField(name="source_file", type="Edm.String",
                            filterable=True, facetable=True),
                SimpleField(name="source", type="Edm.String",
                            filterable=True, facetable=True),
                SimpleField(name="url", type="Edm.String",
                            filterable=False),
            ],
            vector_search=VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="hnsw_text_3_large",
                        algorithm_configuration_name="alg",
                        vectorizer_name="azure_openai_text_3_large",   # ← fixed
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(name="alg")
                ],
                vectorizers=[
                    AzureOpenAIVectorizer(
                        # Must match the profile name above
                        vectorizer_name="azure_openai_text_3_large",
                        parameters=AzureOpenAIVectorizerParameters(
                            resource_url=azure_openai_endpoint,
                            deployment_name=embedding_deployment,
                            model_name=embedding_model,
                        ),
                    )
                ],
            ),
            semantic_search=SemanticSearch(
                default_configuration_name="semantic_config",
                configurations=[
                    SemanticConfiguration(
                        name="semantic_config",
                        prioritized_fields=SemanticPrioritizedFields(
                            content_fields=[SemanticField(field_name="page_chunk")]
                        ),
                    )
                ],
            ),
        )

        # Delete existing index with same name (quick iteration)
        if name in [idx.name for idx in index_client.list_indexes()]:
            index_client.delete_index(name)

        index_client.create_or_update_index(index_schema)
        # Create / update knowledge agent bound to this index + GPT-4.1
        agent = KnowledgeAgent(
            name=f"{name}-agent",
            models=[
                KnowledgeAgentAzureOpenAIModel(
                    azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                        resource_url=azure_openai_endpoint,
                        deployment_name=env("AZURE_OPENAI_DEPLOYMENT_41"),
                        model_name="gpt-4.1",
                    )
                )
            ],
            target_indexes=[
                KnowledgeAgentTargetIndex(index_name=name, default_reranker_threshold=2.5)
            ],
        )
        index_client.create_or_update_agent(agent)
        return True

    except Exception as exc:
        st.error(f"Failed to create index '{name}': {exc}")
        return False


##############################################################################
# LLM prompts
##############################################################################

PLANNER_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a query‑planning assistant. Rewrite or split the **user question**
    Return **only** a JSON
    array of strings – no extra text.
    """
).strip()

ANSWER_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an AI assistant grounded in internal knowledge from Azure AI Search.
    • Use **only** the context passages below.  
    • When you quote, keep the exact citation label already inside the brackets – do **not** invent new labels.  
      Example: if the passage includes “[מב 50.02.pdf]” then cite exactly “[מב 50.02.pdf]”.  
    • If you lack information – say so honestly.  
    • Output in Markdown.
    """
).strip()

##############################################################################
# Agentic RAG core
##############################################################################


def plan_queries(question: str, client: AzureOpenAI, params: dict) -> List[str]:
    msgs = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    resp = client.chat.completions.create(messages=msgs, **params)
    txt = resp.choices[0].message.content.strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return [txt]


def retrieve(queries: List[str], client: SearchClient) -> List[dict]:
    docs: List[dict] = []
    for q in queries:
        hits = list(client.search(q, top=st.session_state.get("top_k", TOP_K_DEFAULT)))
        logging.warning("🔍 query='%s'  hits=%s", q, len(hits))
        for res in hits:
            docs.append(
                {
                    "id": len(docs) + 1,
                    "query": q,
                    "score": res["@search.score"],
                    "content": res.get("content", str(res))[:1000],
                }
            )
    return docs


def build_context(docs: List[dict]) -> str:
    """
    Build a concise context string by taking the first TOP‑K documents overall
    (no per‑query grouping) and truncating each passage to 600 characters.
    """
    chunk_size = 600
    top_k = (
        st.session_state.get("top_k", TOP_K_DEFAULT)
        if "top_k" in st.session_state
        else TOP_K_DEFAULT
    )

    return "\n\n".join(
        f"[doc{d['id']}] {d['content'][:chunk_size]}…" for d in docs[:top_k]
    )


def answer(question: str, ctx: str, client: AzureOpenAI, params: dict) -> tuple[str, int]:
    msgs = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "system", "content": f"Context:\n\n{ctx}"},
        {"role": "user", "content": question},
    ]
    resp = client.chat.completions.create(messages=msgs, **params)
    answer_txt = resp.choices[0].message.content.strip()
    # `resp.usage` is a `CompletionUsage` object, not a dict
    tokens_used = getattr(resp, "usage", None)
    if tokens_used is not None and hasattr(tokens_used, "total_tokens"):
        tokens_used = tokens_used.total_tokens
    else:
        tokens_used = 0
    return answer_txt, tokens_used


##############################################################################
# CLI entry‑point
##############################################################################

##############################################################################
# Pipeline‑as‑a‑Tool helper: wraps KnowledgeAgentRetrievalClient.retrieve
# ---------------------------------------------------------------------------
def agentic_retrieval(agent_name: str, index_name: str, messages: list[dict]) -> str:
    """
    מבצע שליפה סוכנתית (Agentic Retrieval) באמצעות KnowledgeAgentRetrievalClient עבור agent נתון ו-index נתון.
    """
    # הגנה על פורמט ההודעות: המרה לסchema תקינה
    fixed_msgs = []
    for m in messages:
        if isinstance(m, dict) and "role" in m and "content" in m:
            fixed_msgs.append(m)
        elif isinstance(m, str):
            fixed_msgs.append({"role": "user", "content": m})
        else:
            raise ValueError(f"Unknown message format: {m}")

    ka_client = KnowledgeAgentRetrievalClient(
        endpoint=env("AZURE_SEARCH_ENDPOINT"),
        agent_name=agent_name,
        credential=_search_credential(),
    )
    ka_msgs = [
        KnowledgeAgentMessage(
            role=m["role"],
            content=[KnowledgeAgentMessageTextContent(text=m["content"])]
        )
        for m in fixed_msgs
    ]
    # ------------------ build retrieval request ---------------------------
    # If caller supplies an index_name, try to force the query there; otherwise
    # fall back to the agent’s default target index.
    target_params: list[KnowledgeAgentIndexParams] | None = None
    if index_name:
        target_params = [
            KnowledgeAgentIndexParams(
                index_name=index_name,
                reranker_threshold=2.5,
            )
        ]

    req = KnowledgeAgentRetrievalRequest(
        messages=ka_msgs,
        citation_field_name="source_file",
        # Only include target_index_params if we actually specified one
        target_index_params=target_params,
        request_limits=KnowledgeAgentRequestLimits(max_output_size=6000),
    )

    # ------------------ execute – retry without explicit index on mismatch -
    try:
        result = ka_client.knowledge_retrieval.retrieve(retrieval_request=req)
    except HttpResponseError as err:
        # If the agent is not configured for *index_name*, retry letting the
        # agent use its default target index.
        if (
            "target index name must match" in str(err).lower()
            and target_params is not None
        ):
            req.target_index_params = None  # remove the conflicting override
            result = ka_client.knowledge_retrieval.retrieve(retrieval_request=req)
        else:
            raise  # re‑raise unrelated errors

    # ----------------------------------------------------------------------
    # Build a rich JSON array with metadata so downstream agents can show
    # proper citations (url / source_file / page_number).
    # Each chunk inside `result.response` is a KnowledgeAgentMessage object
    # that holds one or more `content` items.
    # We flatten everything into a list like:
    #   [{"ref_id": 0, "content": "...", "url": "...", "source_file": "...", "page_number": 3}, …]
    # ----------------------------------------------------------------------
    chunks: list[dict] = []
    for msg in result.response:
        for c in getattr(msg, "content", []):
            chunk = {
                # ref_id might be absent – fall back to running index
                "ref_id": getattr(c, "ref_id", None) or len(chunks),
                "content": getattr(c, "text", ""),
                "url": getattr(c, "url", None),
                "source_file": getattr(c, "source_file", None),
                "page_number": getattr(c, "page_number", None),
                "score": getattr(c, "score", None),
            }
            # prune empty keys
            chunks.append({k: v for k, v in chunk.items() if v is not None})

    # Return the raw JSON string (no extra formatting)
    return json.dumps(chunks, ensure_ascii=False)

##############################################################################
# ZIP Function Folder Helper
##############################################################################
def _zip_function_folder(func_dir: Path, zip_path: Path) -> None:
    """
    Zip up the contents of *func_dir* (including all subfolders) into *zip_path*.
    Ensures all files are stored relative to func_dir (so host.json is at root).
    """
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in func_dir.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(func_dir))

# -----------------------------------------------------------------------------
# Streamlit UI wrapper (run with: streamlit run agentic-rag-demo.py)
# -----------------------------------------------------------------------------
def run_streamlit_ui() -> None:
    st.set_page_config(page_title="Agentic RAG Demo", page_icon="📚", layout="wide")

    # ── persistent session keys ───────────────────────────────────────────
    for k, default in {
        "selected_index": None,
        "available_indexes": [],
        "uploaded_files": [],
        "indexed_documents": {},
        "history": [],
        "agent_messages": [],
        "dbg_chunks": 0,
        "raw_index_json": "",  # last raw JSON from retrieval
        "orchestrator_targets": {},  # mapping: orchestrator agent → retrieval agent
    }.items():
        st.session_state.setdefault(k, default)

    st.title("📚 Agentic Retrieval‑Augmented Chat")
    st.markdown(
        """
        <style>
        html, body, .stApp { direction: ltr; text-align: left; }
        .ltr { direction: ltr; text-align: left; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Sidebar – model & RAG knobs ───────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Model: GPT‑4.1")
        model_choice = "41"
        oai_client, chat_params = init_openai(model_choice)

        st.caption("Change `.env` to add more deployments")
        auth_mode = "Azure AD" if not os.getenv("AZURE_SEARCH_KEY") else "API Key"
        st.caption(f"🔑 Search auth: {auth_mode}")
        rbac_flag = _rbac_enabled(env("AZURE_SEARCH_ENDPOINT"))
        st.caption(f"🔒 RBAC: {'🟢 Enabled' if rbac_flag else '🔴 Disabled'}")
        if not rbac_flag:
            st.warning(
                "Turn on **Role‑based access control (Azure RBAC)** under "
                "*Search service → Networking → Authentication*."
            )

        st.subheader("🛠️ RAG Parameters")
        st.session_state.ctx_size = st.slider("Context chars per chunk", 300, 2000, 600, 50)
        st.session_state.top_k = st.slider("TOP‑K per query", 1, 200, 5, 1)
        st.session_state.rerank_thr = st.slider("Reranker threshold", 0.0, 4.0, 2.0, 0.1)
        st.session_state.max_output_size = st.slider("Knowledge‑agent maxOutputSize", 1000, 16000, 5000, 500)
        st.session_state.max_tokens = st.slider("Max completion tokens", 256, 32768, 32768, 256)

        chunks_placeholder = st.empty()
        chunks_placeholder.caption(f"Chunks sent to LLM: {st.session_state.get('dbg_chunks', 0)}")

        if st.button("🔄 Reload .env & restart"):
            _reload_env_and_restart()

    # ── Tabbed layout ─────────────────────────────────────────────────────
    tab_create, tab_manage, tab_test, tab_cfg, tab_ai = st.tabs(
        [
            "1️⃣ Create Index",
            "2️⃣ Manage Index",
            "3️⃣ Test Retrieval",
            "⚙️ Function Config",
            "🤖 AI Foundry Agent"
        ]
    )
    

    # Service‑root client used across tabs
    _, root_index_client = init_search_client()

    # ─────────────────── Tab 1 – Create Index ────────────────────────────
    with tab_create:
        st.header("🆕 Create a New Vector Index")
        new_index_name = st.text_input("New index name", placeholder="e.g. agentic‑vectors")
        if st.button("➕ Create new index") and new_index_name:
            if create_agentic_rag_index(root_index_client, new_index_name):
                st.success(f"Created index '{new_index_name}'")
                st.session_state.selected_index = new_index_name
                if new_index_name not in st.session_state.available_indexes:
                    st.session_state.available_indexes.append(new_index_name)

    # ─────────────────── Tab 2 – Manage Index ────────────────────────────
    with tab_manage:
        st.header("📂 Manage Existing Index")

        # refresh list each render
        st.session_state.available_indexes = [idx.name for idx in root_index_client.list_indexes()]

        existing = st.selectbox(
            "Existing indexes",
            options=[""] + st.session_state.available_indexes,
            index=0 if not st.session_state.selected_index else
                   st.session_state.available_indexes.index(st.session_state.selected_index)+1
                   if st.session_state.selected_index in st.session_state.available_indexes else 0,
            placeholder="Select index"
        )
        if existing:
            st.session_state.selected_index = existing
            st.success(f"Selected index: {existing}")

        # delete selected
        if st.session_state.selected_index:
            st.warning(f"Selected index: **{st.session_state.selected_index}**")
            if st.button("🗑️ Delete selected index"):
                try:
                    idx_name = st.session_state.selected_index
                    agent_name = f"{idx_name}-agent"
                    try:
                        root_index_client.delete_agent(agent_name)
                    except Exception:
                        pass
                    root_index_client.delete_index(idx_name)
                    st.session_state.available_indexes.remove(idx_name)
                    st.session_state.selected_index = None
                    st.success(f"Deleted index **{idx_name}** and its agent.")
                except Exception as ex:
                    st.error(f"Failed to delete index: {ex}")

        st.divider()
        st.subheader("📄 Upload PDFs into Selected Index")
        if not st.session_state.selected_index:
            st.info("Select an index first.")
        else:
            uploaded = st.file_uploader("Choose PDF files", type=["pdf"], accept_multiple_files=True)
            if uploaded and st.button("🚀 Ingest"):
                with st.spinner("Embedding and uploading…"):
                    ###############################################
                    # Build buffered sender with error‑tracking
                    ###############################################
                    failed_ids: list[str] = []

                    def _on_error(action) -> None:
                        """
                        Callback for SearchIndexingBufferedSender — called once per failed
                        indexing action. *action* is the document that failed.

                        We record its ID (if present) so the UI can report how many pages
                        were skipped.
                        """
                        try:
                            # `action` is usually the original document (dict) we provided
                            failed_ids.append(action.get("id", "?"))
                        except Exception as exc:
                            logging.error("⚠️  on_error callback failed to record ID: %s", exc)
                            failed_ids.append("?")

                    sender = SearchIndexingBufferedSender(
                        endpoint=env("AZURE_SEARCH_ENDPOINT"),
                        index_name=st.session_state.selected_index,
                        credential=_search_credential(),
                        # Flush every 100 docs or every 5 s – whichever comes first
                        batch_size=100,
                        auto_flush_interval=5,
                        on_error=_on_error,
                    )

                    embed_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
                    total_pages = 0
                    for pf in uploaded:
                        docs = pdf_to_documents(pf, oai_client, embed_deploy)
                        sender.upload_documents(documents=docs)
                        total_pages += len(docs)

                    # Ensure everything is sent
                    sender.close()

                    ###############################################
                    # Optional: wait until the documents are searchable
                    ###############################################
                    try:
                        search_client, _ = init_search_client(st.session_state.selected_index)
                        # Basic probe – wait until at least one document shows up
                        import time
                        for _ in range(30):                  # up to ~30 s
                            if search_client.get_document_count() > 0:
                                break
                            time.sleep(1)
                    except Exception as probe_err:
                        logging.warning("Search probe failed: %s", probe_err)

                    ###############################################
                    # Report outcome
                    ###############################################
                    success_pages = total_pages - len(failed_ids)
                    if failed_ids:
                        st.error(f"❌ {len(failed_ids)} pages failed to index – see logs for details.")
                    if success_pages:
                        st.success(f"✅ Indexed {success_pages} pages into **{st.session_state.selected_index}**.")

    # ─────────────────── Tab 3 – Test Retrieval ──────────────────────────
    with tab_test:
        st.header("🧪 Test Retrieval Without Foundry")
        if not st.session_state.selected_index:
            st.info("Select or create an index in the previous tabs.")
        else:
            search_client, _ = init_search_client(st.session_state.selected_index)

            # History
            for turn in st.session_state.history:
                with st.chat_message(turn["role"]):
                    st.markdown(f'<div class="ltr">{turn["content"]}</div>', unsafe_allow_html=True)

            user_query = st.chat_input("Ask your question…")
            if user_query:
                st.session_state.history.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.markdown(f'<div class="ltr">{user_query}</div>', unsafe_allow_html=True)

                agent_name = f"{st.session_state.selected_index}-agent"
                agent_client = init_agent_client(agent_name)
                if not st.session_state.agent_messages:
                    st.session_state.agent_messages = [{"role": "assistant", "content": "Answer with sources."}]
                st.session_state.agent_messages.append({"role": "user", "content": user_query})

                ka_msgs = [
                    KnowledgeAgentMessage(
                        role=m["role"],
                        content=[KnowledgeAgentMessageTextContent(text=m["content"])]
                    )
                    for m in st.session_state.agent_messages
                ]

                ka_req = KnowledgeAgentRetrievalRequest(
                    messages=ka_msgs,
                    citation_field_name="source_file",
                    include_doc_key=True,
                    response_fields=["text", "source_file", "url", "doc_key"],
                    target_index_params=[
                        KnowledgeAgentIndexParams(
                            index_name=st.session_state.selected_index,
                            reranker_threshold=float(st.session_state.rerank_thr),
                            citation_field_name="source_file",   # ensure citations use filenames
                        )
                    ],
                    request_limits=KnowledgeAgentRequestLimits(
                        max_output_size=int(st.session_state.max_output_size)
                    ),
                )
                with st.spinner("Retrieving…"):
                    # ---------- SDK call: retrieve chunks --------------------
                    result = agent_client.knowledge_retrieval.retrieve(
                        retrieval_request=ka_req
                    )

                # The agent returns a single assistant message whose first
                # content item is a JSON string (list of chunks).

                raw_text = result.response[0].content[0].text
                st.session_state.raw_index_json = raw_text
                st.session_state.agent_messages.append(
                    {"role": "assistant", "content": raw_text}
                )

                # ────────────────────────────────────────────────────────────
                # Post‑processing: parse raw_text → build answer + citations
                # ────────────────────────────────────────────────────────────
                try:
                    parsed_json = json.loads(raw_text)
                except Exception:
                    parsed_json = None      # plain text fallback

                answer_text: str | None = None
                sources_data: list[dict] = []
                chunk_count = 0
                usage_tok = 0
                ctx_for_llm: str | None = None

                # ---------- Case 1: {"answer": "...", "sources": [...]} ----------
                if isinstance(parsed_json, dict) and "answer" in parsed_json:
                    answer_text = parsed_json.get("answer", "").strip()
                    sources_data = parsed_json.get("sources", [])
                    chunk_count = 1

                # ---------- Case 2: list‑of‑chunks (classic) ----------------------
                elif isinstance(parsed_json, list):
                    # Ensure each chunk has source_file (lookup by doc_key when missing)
                    for itm in parsed_json:
                        if "source_file" not in itm and "doc_key" in itm:
                            try:
                                doc = search_client.get_document(key=itm["doc_key"])
                                if doc and "source_file" in doc:
                                    itm["source_file"] = doc["source_file"]
                            except Exception:
                                pass  # ignore lookup errors

                    def _label(itm: dict) -> str:
                        """
                        Return the best human‑readable citation label,
                        priority order:
                          1) source_file   – injected during ingestion
                          2) source        – alias field
                          3) url           – last segment of URL
                          4) filename embedded inside the content itself,
                             e.g. text begins with “[my.pdf] …”
                          5) fallback      – generic doc{ref_id}
                        """
                        # 1) explicit filename from metadata
                        if itm.get("source_file"):
                            return itm["source_file"]

                        # 2) alias field (also set during ingestion)
                        if itm.get("source"):
                            return itm["source"]

                        # 3) last path segment of URL
                        if itm.get("url"):
                            from pathlib import Path
                            return Path(itm["url"]).name or itm["url"]

                        # 4) extract leading “[filename] ...” from the content
                        txt = itm.get("content", "")
                        if txt.startswith("[") and "]" in txt[:150]:
                            return txt[1 : txt.find("]")]

                        # 5) generic fallback
                        return f"doc{itm.get('ref_id', '?')}"

                    ctx_for_llm = "\n\n".join(
                        f"[{_label(itm)}] {itm.get('content','')}" for itm in parsed_json
                    )
                    chunk_count = len(parsed_json)

                    # Summarise via OpenAI (answer function defined earlier)
                    answer_text, usage_tok = answer(user_query, ctx_for_llm, oai_client, chat_params)

                    # Build sources list (unique labels)
                    seen = set()
                    for itm in parsed_json:
                        src = itm.get("source_file") or _label(itm)
                        if src not in seen:
                            sources_data.append(
                                {"source_file": src, "url": itm.get("url", "")}
                            )
                            seen.add(src)

                # ---------- Case 3: raw plain text -------------------------------
                else:
                    answer_text = raw_text.strip()
                    chunk_count = 1

                # Update sidebar diagnostic
                st.session_state.dbg_chunks = chunk_count

                # ---------- Render assistant answer ------------------------------
                with st.chat_message("assistant"):
                    st.markdown(answer_text or "*[לא התקבלה תשובה]*", unsafe_allow_html=True)

                    if sources_data:
                        st.markdown("#### 🗂️ Sources")
                        for src in sources_data:
                            name = src.get("source_file") or src.get("url") or "unknown"
                            url  = src.get("url")
                            if url:
                                st.markdown(f"- [{name}]({url})")
                            else:
                                st.markdown(f"- {name}")

                # ---------- Optional: raw chunks for debugging --------------------
                if isinstance(parsed_json, list) and parsed_json:
                    with st.expander("📚 Chunks", expanded=False):
                        for itm in parsed_json:
                            ref = itm.get("ref_id", itm.get("id", '?'))
                            st.markdown(f"**📄 מקור {ref}:**")
                            st.write(itm.get("content", ""))
                            st.markdown("---")

                # ── Raw payload for debugging ───────────────────────────
                if st.session_state.raw_index_json:
                    with st.expander("📃 מידע גולמי מהאינדקס", expanded=False):
                        try:
                            st.json(json.loads(st.session_state.raw_index_json))
                        except Exception:
                            st.code(st.session_state.raw_index_json)


    # ─────────────────── Tab 5 – Function Config ──────────────────────────
    with tab_cfg:
        st.header("⚙️ Configure Azure Function")

        # ── Load .env once for this tab ────────────────────────────────
        from dotenv import dotenv_values
        env_file_path = Path(__file__).resolve().parent / ".env"
        env_vars = dotenv_values(env_file_path) if env_file_path.exists() else {}

        # ------------------------------------------------------------------
        # Runtime parameters – choose index from dropdown
        # ------------------------------------------------------------------
        st.markdown("##### Runtime parameters")

        # Populate from earlier tabs (Manage/Create) – falls back to manual
        index_options = st.session_state.get("available_indexes", [])
        if index_options:
            # Pre‑select value from .env if present
            try:
                preselect = index_options.index(env_vars.get("INDEX_NAME", index_options[0]))
            except ValueError:
                preselect = 0
            idx_selected = st.selectbox("INDEX_NAME", index_options, index=preselect)
        else:
            st.warning("No index list detected – enter manually.")
            idx_selected = st.text_input("INDEX_NAME", env_vars.get("INDEX_NAME", ""))

        # Update env_vars with the chosen/typed value
        env_vars["INDEX_NAME"] = idx_selected.strip()
        env_vars["AGENT_NAME"] = f"{idx_selected.strip()}-agent" if idx_selected else ""

        # Display the derived AGENT_NAME (read‑only)
        st.text_input("AGENT_NAME", env_vars["AGENT_NAME"], disabled=True)

        # Try to pre‑fill subscription from az cli
        from subprocess import check_output, CalledProcessError
        try:
            az_acc = json.loads(check_output(["az", "account", "show", "-o", "json"], text=True))
            cli_sub = az_acc.get("id", "")
        except (CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            cli_sub = ""
        sub_id = st.text_input("Subscription ID", cli_sub)

        # List Function Apps in this subscription (needs DefaultAzureCredential)
        func_choices = []
        func_map = {}          # "app (rg)" → (name, rg)
        if sub_id:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.web import WebSiteManagementClient
            try:
                _wcli_tmp = WebSiteManagementClient(DefaultAzureCredential(), sub_id)
                for site in _wcli_tmp.web_apps.list():
                    # Filter only Function Apps (kind contains "functionapp")
                    if site.kind and "functionapp" in site.kind:
                        label = f"{site.name}  ({site.resource_group})"
                        func_choices.append(label)
                        func_map[label] = (site.name, site.resource_group)
            except Exception as _exc:
                st.warning("⚠️ Could not list Function Apps automatically; fill manually.")

        func_sel_lbl = st.selectbox(
            "Choose Function App",
            ["-- manual input --"] + func_choices,
            index=0
        )
        st.session_state["func_map"]     = func_map
        st.session_state["func_choices"] = func_choices
        if func_sel_lbl != "-- manual input --":
            app, rg = func_map[func_sel_lbl]
        else:
            rg = st.text_input("Resource Group", os.getenv("AZURE_RG", ""))
            app = st.text_input("Function App name", os.getenv("AZURE_FUNCTION_APP", ""))

        if not all((sub_id, rg, app)):
            st.info("Fill subscription / RG / Function-App and click 🔄 Load settings.")
        else:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.web import WebSiteManagementClient
            import pandas as pd, re

            wcli = WebSiteManagementClient(DefaultAzureCredential(), sub_id)

            def _mask(v: str) -> str:
                if v.startswith("@Microsoft.KeyVault(") or re.search(r"(key|secret|token|pass)", v, re.I):
                    return "••••••"
                return v

            if "func_raw" not in st.session_state:
                st.session_state.func_raw = {}
            if "func_df" not in st.session_state:
                st.session_state.func_df  = pd.DataFrame(columns=["key", "value"])

            if st.button("🔄 Load settings"):
                try:
                    cfg = wcli.web_apps.list_application_settings(rg, app)
                    raw = cfg.properties or {}
                    st.session_state.func_raw = raw

                    # ── Merge precedence: Function settings ← .env values (1‑to‑1) ──
                    param_vals = raw.copy()
                    param_vals.update(env_vars)   # .env already matches Function key names
                    REQUIRED_KEYS = [
                        "AGENT_FUNC_KEY", "AGENT_NAME", "API_VERSION",
                        "APPLICATIONINSIGHTS_CONNECTION_STRING",
                        "AZURE_OPENAI_API_VERSION", "AzureWebJobsStorage", "debug",
                        "DEPLOYMENT_STORAGE_CONNECTION_STRING", "includesrc",
                        "INDEX_NAME", "MAX_OUTPUT_SIZE",
                        "OPENAI_DEPLOYMENT", "OPENAI_ENDPOINT", "OPENAI_KEY",
                        "RERANKER_THRESHOLD", "SEARCH_API_KEY",
                        "SERVICE_NAME"
                    ]
                    for k in REQUIRED_KEYS:
                        param_vals.setdefault(k, "")

                    rows = [{"key": k, "value": _mask(str(param_vals[k]))} for k in REQUIRED_KEYS]
                    st.session_state.func_df = pd.DataFrame(rows)

                    st.success(f"Loaded & merged {len(st.session_state.func_df)} setting(s).")
                except Exception as err:
                    st.error(f"Failed to load: {err}")

        
        # ── Show editable table on every render once loaded ───────────────
        if st.session_state.get("func_df") is not None and not st.session_state.func_df.empty:
            st.markdown("#### Function App Settings")
            st.session_state.func_df = _st_data_editor(
                st.session_state.func_df,
                num_rows="dynamic",
                use_container_width=True,
                key="func_editor",
            )

            # ── Push edited settings back to the Function App ────────────────
            st.divider()
            if st.button("💾 Push settings to Function"):
                if not all((sub_id, rg, app)):
                    st.error("Fill subscription / resource‑group / app name first.")
                elif st.session_state.func_df.empty:
                    st.error("Nothing to push – load settings first.")
                else:
                    try:
                        # Build new property map –
                        # start with the *original* raw to preserve hidden keys
                        new_props = dict(st.session_state.func_raw)

                        # Overwrite with rows from the edited table
                        for _, row in st.session_state.func_df.iterrows():
                            k = str(row["key"]).strip()
                            v = str(row["value"]).strip()
                            # If the cell still shows masked dots, keep original
                            if v == "••••••" and k in new_props:
                                continue
                            new_props[k] = v

                        # Update in Azure
                        wcli.web_apps.update_application_settings(
                            rg,
                            app,
                            {"properties": new_props}
                        )
                        st.success(f"✅ Updated {len(new_props)} settings on **{app}**")
                    except Exception as push_err:
                        st.error(f"Failed to update Function settings:\n{push_err}")

            # ── Deploy local ./function code to this Function App ─────────────
            st.divider()
            if st.button("🚀 Deploy local code to Function"):
                if not all((sub_id, rg, app)):
                    st.error("Fill subscription / RG / Function‑App first.")
                else:
                    try:
                        zip_path = _zip_function_folder()
                        with st.spinner("Creating zip and deploying…"):
                            
                            cmd = [
                                "az", "functionapp", "deployment", "source", "config-zip",
                                "-g", rg, "-n", app,
                                "--src", zip_path
                            ]
                            subprocess.check_call(cmd)
                        st.success("✅ Deployment succeeded.")
                    except subprocess.CalledProcessError as cerr:
                        st.error(f"az CLI deployment failed: {cerr}")
                    except Exception as zerr:
                        st.error(f"Failed to deploy: {zerr}")

    # ─────────────────── Single Tab – AI Foundry Agent ──────────────────
    with tab_ai:
        st.header("🤖 Create AI Foundry Agent")

        func_map     = st.session_state.get("func_map", {})
        func_choices = st.session_state.get("func_choices", [])

        if not func_choices:
            st.info("Go to **Function Config** tab first and load settings.")
            st.stop()

        func_sel = st.selectbox("Function App to invoke", func_choices, index=0)
        func_name, func_rg = func_map[func_sel]
        base_url = f"https://{func_name}.azurewebsites.net/api"

        # Detect Foundry projects the CLI user can access
        cli_cred = AzureCliCredential()
        logged_in, _ = check_azure_cli_login()
        if not logged_in:
            st.error("🔑 Run `az login` before using this feature.")
            st.stop()

        projects = get_ai_foundry_projects(cli_cred)
        if not projects and os.getenv("PROJECT_ENDPOINT"):
            ep = os.getenv("PROJECT_ENDPOINT").strip()
            projects = [{
                "name": ep.split('/')[-1][:30] or "env-project",
                "location": "env",
                "endpoint": ep,
                "resource_group": "env",
                "hub_name": "env",
            }]

        if not projects:
            st.warning("No AI Foundry projects detected.")
            st.stop()

        proj_labels = [f"{p['name']} – {p['location']}" for p in projects]
        sel = st.selectbox("Choose Foundry project", proj_labels, index=0)
        project_endpoint = projects[proj_labels.index(sel)]['endpoint']
        st.caption(f"🔗 Endpoint: {project_endpoint}")

        agent_name = st.text_input("Agent name", placeholder="function‑assistant")
        if st.button("🚀 Create Agent") and agent_name:
            # --- Build anonymous OpenAPI tool -----------------------------------
            TOOL_NAME = "Test_askAgentFunction"
            tool_schema = {
                "openapi": "3.0.1",
                "info": {
                    "title": "AgentFunction",
                    "version": "1.0.0"
                },
                # Base URL for the Function App (no query‑string here!)
                "servers": [
                    {
                        "url": base_url
                    }
                ],
                "paths": {
                    "/AgentFunction/{question}": {
                        "post": {
                            "operationId": "askAgentFunction",
                            "summary": "Ask the Azure Function",
                            "parameters": [
                                {
                                    "name": "question",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "string"}
                                },
                                {
                                    "name": "code",
                                    "in": "query",
                                    "required": True,
                                    "schema": {
                                        "type": "string",
                                        "default": FUNCTION_KEY
                                    },
                                    "description": "Function host key (taken from env‑var AGENT_FUNC_KEY)"
                                },
                                {
                                    "name": "includesrc",
                                    "in": "query",
                                    "required": False,
                                    "schema": {
                                        "type": "boolean",
                                        "default": True
                                    },
                                    "description": "Include sources in the Function response"
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "Plain‑text answer",
                                    "content": {
                                        "text/plain": {
                                            "schema": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            SYSTEM_MSG = (
                "You have one action called Test_askAgentFunction.\n"
                "Call it **every time** the user asks a factual question.\n"
                "Send the whole question unchanged as the {question} path parameter **and** include the two query parameters exactly as shown below:\n"
                f"  • code={FUNCTION_KEY}\n"
                "  • includesrc=true\n"
                "Example URL you must generate (line breaks added for clarity):\n"
                f"POST {base_url}/AgentFunction/{{question}}?code={FUNCTION_KEY}&includesrc=true"
                "Return the Function's plain‑text response **verbatim and in full**, including any inline citations such as [my_document.pdf].\n"
                "Do **NOT** add, remove, reorder, or paraphrase content, and do **NOT** drop those citation markers.\n"
                "If the action fails, reply exactly with: I don't know\n"
                "Do **NOT** answer from your own internal knowledge and do **NOT** answer questions unrelated to the Function.\n"
                "\n"
                "### How to respond\n"
                "1. Parse the JSON the Function returns.\n"
                "2. Reply with the **exact value of \"answer\"** – do NOT change it.\n"
                "3. After that, print a short “Sources:” list. For each object in \"sources\" show its **source_file** (fallback to url if empty; if both missing, show the placeholder doc#).\n"
                "   Example:\n"
                "   Sources:\n"
                "   • המב 50.02.pdf\n"
                "   • מס 40.021.pdf\n"
            )

            # --- Create OpenAPI tool (anonymous auth) ---------------------------
            auth = OpenApiAnonymousAuthDetails()  # public endpoint – no key required
            openapi_tool = OpenApiTool(
                name=TOOL_NAME,
                spec=tool_schema,
                description="Invoke the Azure Function via HTTP POST",
                auth=auth,
            )

            # Create the agent via the Azure AI Projects SDK
            try:
                proj_client = AIProjectClient(project_endpoint, DefaultAzureCredential())
                with proj_client:
                    agent = proj_client.agents.create_agent(
                        name=agent_name,
                        model="gpt-4.1",                   # make sure this deployment exists
                        instructions=SYSTEM_MSG,
                        description="Assistant created from Streamlit UI",
                        tools=openapi_tool.definitions,   # <-- note: *definitions*
                    )
                st.success(f"✅ Agent **{agent.name}** created (ID: {agent.id})")
            except Exception as err:
                st.error("Failed to create agent via SDK:")
                st.exception(err)
def main() -> None:
    # This script must be run with Streamlit.
    if not _st_in_runtime():
        print(
            "🔴  CLI execution is no longer supported.\n"
            "    Start the app with:\n\n"
            "      streamlit run agentic-rag-demo.py\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Streamlit runtime detected → launch UI
    run_streamlit_ui()


if __name__ == "__main__":
    main()