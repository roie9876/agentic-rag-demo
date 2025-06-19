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
import zipfile
import tempfile
import subprocess
import time  # Added to support sleep in polling after ingestion
import base64  # Added to encode document bytes for _chunk_to_docs

from pathlib import Path
from typing import List, Tuple, Dict

# ---------------------------------------------------------------------------
# Streamlit Data‑Editor helper (works on both old & new versions)
# ---------------------------------------------------------------------------
import streamlit as st
from chunking import DocumentChunker

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
        max_tokens=st.session_state.get("max_tokens", 80000),
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


# ───────── Text-based fallback for Office / plain files ─────────
def _plainfile_to_docs(
    file_name: str,
    file_bytes: bytes,
    file_url: str,
    oai_client: AzureOpenAI,
    embed_deployment: str,
) -> list[dict]:
    """
    Fallback extractor for DOCX, PPTX, TXT, MD, JSON.
    Tries rich-parsers first; if unavailable, uses a simple XML/text strip.
    Splits the resulting text into ~4 000-char chunks and embeds them.
    """
    import re, zipfile, io
    ext = os.path.splitext(file_name)[-1].lower()
    txt = ""

    def _strip_xml(xml_bytes: bytes) -> str:
        """Very rough tag-stripper – good enough for plain text."""
        return re.sub(r"<[^>]+>", " ", xml_bytes.decode("utf-8", errors="ignore"))

    try:
        if ext == ".docx":
            try:
                from docx import Document            # python-docx
                txt = "\n".join(p.text for p in Document(io.BytesIO(file_bytes)).paragraphs)
            except ImportError:
                # Fallback: read word/document.xml inside the docx zip
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    xml = zf.read("word/document.xml")
                txt = _strip_xml(xml)
        elif ext == ".pptx":
            try:
                from pptx import Presentation        # python-pptx
                prs = Presentation(io.BytesIO(file_bytes))
                slides = []
                for slide in prs.slides:
                    slides.append(
                        "\n".join(shape.text for shape in slide.shapes if hasattr(shape, "text"))
                    )
                txt = "\n\n".join(slides)
            except ImportError:
                # Fallback: concatenate text from slide XMLs
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    slide_files = [n for n in zf.namelist() if n.startswith("ppt/slides/") and n.endswith(".xml")]
                    txt = "\n\n".join(_strip_xml(zf.read(f)) for f in slide_files)
        elif ext in (".txt", ".md"):
            txt = file_bytes.decode("utf-8", errors="ignore")
        elif ext == ".json":
            import json as _json
            txt = _json.dumps(_json.loads(file_bytes), indent=2, ensure_ascii=False)
    except Exception as parse_err:
        logging.error("Plain extraction failed for %s: %s", file_name, parse_err)
        txt = ""  # will return [] later if empty

    if not txt.strip():
        return []

    chunks = textwrap.wrap(txt, 4000)
    docs = []
    label = f"[{file_name}] "                 # ← new unified prefix
    for i, chunk in enumerate(chunks):
        chunk_txt = label + chunk             # ← prepend filename
        try:
            vector = embed_text(oai_client, embed_deployment, chunk_txt)   # embed prefixed text
        except Exception as emb_err:
            logging.error("Embedding failed for %s (chunk %d): %s", file_name, i, emb_err)
            continue
        docs.append(
            {
                "id": hashlib.md5(f"{file_name}_{i}".encode()).hexdigest(),
                "page_chunk": chunk_txt,      # store prefixed chunk
                "page_embedding_text_3_large": vector,
                "page_number": i + 1,
                "source_file": file_name,
                "source": file_name,
                "url": file_url or "",
                # Enhanced metadata for fallback processing
                "extraction_method": "simple_parser",
                "document_type": {
                    ".docx": "Word Document",
                    ".pptx": "PowerPoint Presentation", 
                    ".txt": "Text Document",
                    ".md": "Markdown Document",
                    ".json": "JSON Document"
                }.get(ext, "Text Document"),
                "has_figures": False,
                "processing_timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
        )
    return docs
# -----------------------------------------------------------------

def _chunk_to_docs(
    file_name: str,
    file_bytes: bytes,
    file_url: str,
    oai_client: AzureOpenAI,
    embed_deployment: str,
) -> list[dict]:
    """
    Run DocumentChunker on *file_bytes* and convert the chunks to the schema
    that agentic-rag indexes (adds url/source_file and ensures embeddings).

    Fix: send **raw bytes** first (needed for XLSX, DOCX, …).  
    Fallback to the old base-64 path if that fails – keeps compatibility
    with formats that still expect a string.
    """
    dc = DocumentChunker()

    ext = os.path.splitext(file_name)[-1].lower()
    # ── EARLY BYPASS for known troublesome formats ────────────────
    if ext in (".csv", ".xls", ".xlsx"):
        return _tabular_to_docs(file_name, file_bytes, file_url, oai_client, embed_deployment)
    # Remove DOCX/PPTX from bypass to allow Document Intelligence processing
    if ext in (".txt", ".md", ".json"):
        return _plainfile_to_docs(file_name, file_bytes, file_url, oai_client, embed_deployment)
    # ------------------------------------------------------------------

    def _call_chunker(doc_bytes):
        data = {
            "fileName": file_name,
            "documentBytes": doc_bytes,
            "documentUrl": file_url or "",
        }
        return dc.chunk_documents(data)

    try:
        chunks, _, _ = _call_chunker(file_bytes)          # 1️⃣ raw bytes
    except Exception as first_err:
        try:
            # 2️⃣ base64 fallback (legacy)
            b64_str = (
                file_bytes
                if isinstance(file_bytes, str)
                else base64.b64encode(file_bytes).decode("utf-8")
            )
            chunks, _, _ = _call_chunker(b64_str)
        except Exception as second_err:
            # 3️⃣ tabular fallback for XLS/CSV
            ext = os.path.splitext(file_name)[-1].lower()
            if ext in (".csv", ".xlsx", ".xls"):
                return _tabular_to_docs(file_name, file_bytes, file_url, oai_client, embed_deployment)
            # Nothing worked – re-raise original error
            raise first_err from second_err

    docs = []
    label = f"[{file_name}] "                 # ← prefix for DocumentChunker path
    
    # Determine extraction method and document type
    extraction_method = "document_intelligence" if ext in ('.pdf', '.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.docx', '.pptx', '.xlsx', '.html') else "langchain_chunker"
    document_type = {
        '.pdf': 'PDF Document',
        '.docx': 'Word Document', 
        '.pptx': 'PowerPoint Presentation',
        '.xlsx': 'Excel Spreadsheet',
        '.png': 'Image',
        '.jpg': 'Image',
        '.jpeg': 'Image',
        '.bmp': 'Image',
        '.tiff': 'Image',
        '.html': 'HTML Document'
    }.get(ext, 'Text Document')
    
    has_figures = False
    
    for i, ch in enumerate(chunks):
        txt = ch.get("page_chunk") or ch.get("chunk") or ch.get("content") or ""
        if not txt:
            continue
        if not txt.startswith(label):         # avoid double-prefix
            txt = label + txt                 # ← prepend filename
            
        # Check if chunk contains figures (for multimodal processing)
        if any(key in ch for key in ['figure_urls', 'figure_descriptions', 'combined_caption']):
            has_figures = True
            
        # embedding – reuse if present, else create with safe fallback
        vector = ch.get("page_embedding_text_3_large")
        if not vector:
            try:
                vector = embed_text(oai_client, embed_deployment, txt)
            except Exception as emb_err:
                logging.error("Embedding failed for %s (chunk %d): %s", file_name, i, emb_err)
                continue  # skip this chunk
        docs.append(
            {
                "id": ch.get("id") or hashlib.md5(f"{file_name}_{i}".encode()).hexdigest(),
                "page_chunk": txt,
                "page_embedding_text_3_large": vector,
                "page_number": ch.get("page_number") or i + 1,
                "source_file": file_name,
                "source": file_name,
                "url": file_url or "",
                # Enhanced metadata
                "extraction_method": extraction_method,
                "document_type": document_type, 
                "has_figures": has_figures,
                "processing_timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
        )
    return docs
# ───────────────────────── end helper ────────────────────────────────


# ─────────────── Fallback: CSV / XLS(X) → docs ───────────────
def _tabular_to_docs(
    file_name: str,
    file_bytes: bytes,
    file_url: str,
    oai_client: AzureOpenAI,
    embed_deployment: str,
) -> list[dict]:
    """
    Last-resort converter for CSV/XLS/XLSX when DocumentChunker fails.
    Turns every ~4 000-char slice of the table (as CSV text) into one doc.
    """
    import io, pandas as pd  # pandas is only needed here
    ext = os.path.splitext(file_name)[-1].lower()  # Add ext definition
    # Extract plain text
    if file_name.lower().endswith(".csv"):
        txt = file_bytes.decode("utf-8", errors="ignore")
    else:  # .xls / .xlsx
        excel = pd.ExcelFile(io.BytesIO(file_bytes))
        txt_parts = []
        for sheet in excel.sheet_names:
            df = excel.parse(sheet)
            txt_parts.append(f"\n\n### Sheet: {sheet}\n" + df.to_csv(index=False))
        txt = "".join(txt_parts)

    chunks = textwrap.wrap(txt, 4000)
    docs = []
    label = f"[{file_name}] "                 # ← prefix for CSV / Excel
    for i, chunk in enumerate(chunks):
        chunk_txt = label + chunk
        try:
            vector = embed_text(oai_client, embed_deployment, chunk_txt)
        except Exception as emb_err:
            logging.error("Embedding failed for %s (chunk %d): %s", file_name, i, emb_err)
            continue  # skip this chunk
        docs.append(
            {
                "id": hashlib.md5(f"{file_name}_{i}".encode()).hexdigest(),
                "page_chunk": chunk_txt,
                "page_embedding_text_3_large": vector,
                "page_number": i + 1,
                "source_file": file_name,
                "source": file_name,
                "url": file_url or "",
                # Enhanced metadata for tabular processing
                "extraction_method": "pandas_parser",
                "document_type": {
                    ".csv": "CSV Spreadsheet",
                    ".xlsx": "Excel Spreadsheet", 
                    ".xls": "Excel Spreadsheet"
                }.get(ext, "Tabular Data"),
                "has_figures": False,
                "processing_timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
        )
    return docs


def init_search_client(index_name: str | None = None) -> Tuple[SearchClient, SearchIndexClient]:
    """
    Return (search_client, index_client).
    Only API Key authentication is supported for agentic retrieval (see Azure docs).
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
    Only API Key authentication is supported for agentic retrieval (see Azure docs).
    """
    cred = _search_credential()   # Always AzureKeyCredential
    return KnowledgeAgentRetrievalClient(
        endpoint=env("AZURE_SEARCH_ENDPOINT"),
        agent_name=agent_name,
        credential=cred,
    )


def create_agentic_rag_index(index_client: "SearchIndexClient", name: str) -> bool:
    """
    Create (or recreate) an index + knowledge-agent עם מפתח-API ל-Azure OpenAI.
    """
    try:
        # ----------- הגדרות בסיסיות -----------------
        azure_openai_endpoint = env("AZURE_OPENAI_ENDPOINT_41")
        embedding_deployment  = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        embedding_model       = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL",      "text-embedding-3-large")
        VECTOR_DIM            = 3072
        # Resolve OpenAI key – prefer suffix _41, fall back to generic
        openai_api_key = os.getenv("AZURE_OPENAI_KEY_41") or os.getenv("AZURE_OPENAI_KEY") or ""

        # ----------- Vectorizer עם api_key -----------
        vec_params = AzureOpenAIVectorizerParameters(
            resource_url    = azure_openai_endpoint,
            deployment_name = embedding_deployment,
            model_name      = embedding_model,
            api_key         = openai_api_key,
        )

        index_schema = SearchIndex(
            name   = name,
            fields = [
                SearchField(name="id", type="Edm.String", key=True, filterable=True, sortable=True, facetable=True),
                SearchableField(name="page_chunk", type="Edm.String", analyzer_name="standard.lucene"),
                SearchField(
                    name="page_embedding_text_3_large",
                    type="Collection(Edm.Single)",
                    stored=False,
                    vector_search_dimensions=VECTOR_DIM,
                    vector_search_profile_name="hnsw_text_3_large",
                ),
                SimpleField(name="page_number",  type="Edm.Int32",  filterable=True, sortable=True, facetable=True),
                SimpleField(name="source_file",  type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="source",       type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="url",          type="Edm.String"),
                SimpleField(name="doc_key",      type="Edm.String", filterable=True), # Added for proper document referencing
                # Enhanced metadata fields for Document Intelligence processing
                SimpleField(name="extraction_method", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="document_type", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="has_figures", type="Edm.Boolean", filterable=True, facetable=True),
                SimpleField(name="processing_timestamp", type="Edm.DateTimeOffset", filterable=True, sortable=True),
            ],
            vector_search = VectorSearch(
                profiles   = [ VectorSearchProfile(name="hnsw_text_3_large", algorithm_configuration_name="alg",
                                                   vectorizer_name="azure_open_ai_text_3_large") ],
                algorithms = [ HnswAlgorithmConfiguration(name="alg") ],
                vectorizers= [ AzureOpenAIVectorizer(vectorizer_name="azure_open_ai_text_3_large",
                                                     parameters=vec_params) ],           # ← משתמשים ב-vec_params
            ),
            semantic_search = SemanticSearch(
                default_configuration_name="semantic_config",
                configurations=[ SemanticConfiguration(
                    name="semantic_config",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[ SemanticField(field_name="page_chunk") ]
                    ),
                )],
            ),
        )

        # מוחקים אינדקס קודם כדי לעדכן במקום
        if name in [idx.name for idx in index_client.list_indexes()]:
            index_client.delete_index(name)
        index_client.create_or_update_index(index_schema)

        # ----------- Knowledge-Agent עם api_key -------
        agent = KnowledgeAgent(
            name = f"{name}-agent",
            models = [
                KnowledgeAgentAzureOpenAIModel(
                    azure_open_ai_parameters = AzureOpenAIVectorizerParameters(
                        resource_url    = azure_openai_endpoint,
                        deployment_name = env("AZURE_OPENAI_DEPLOYMENT_41"),
                        model_name      = "gpt-4.1",
                        api_key         = openai_api_key,
                    )
                )
            ],
            target_indexes = [
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
                "doc_key": getattr(c, "doc_key", None),
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
# ────────────────────────── Helper: zip Azure Function folder ──────────────
def _zip_function_folder(func_dir: Path, zip_path: Path) -> None:
    """Zip *func_dir* (כולל host.json וכו') כ-relative paths אל *zip_path*."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for itm in func_dir.rglob("*"):
            if itm.is_file():
                zf.write(itm, itm.relative_to(func_dir))
# -----------------------------------------------------------------------------
# Processing Information Display Helper
# -----------------------------------------------------------------------------
def display_processing_info(file_name: str, file_ext: str, chunker_type: str = None, show_capabilities: bool = True):
    """
    Display processing information for a file to help users understand 
    what tools and methods are being used for extraction.
    """
    ext = file_ext.lower()
    
    # File type mapping
    file_type_map = {
        '.pdf': '📄 PDF Document',
        '.docx': '📝 Word Document', 
        '.pptx': '📊 PowerPoint Presentation',
        '.xlsx': '📈 Excel Spreadsheet',
        '.xls': '📈 Excel Spreadsheet',
        '.csv': '📈 CSV Data',
        '.png': '🖼️ PNG Image',
        '.jpg': '🖼️ JPEG Image',
        '.jpeg': '🖼️ JPEG Image',
        '.bmp': '🖼️ BMP Image',
        '.tiff': '🖼️ TIFF Image',
        '.txt': '📝 Text File',
        '.md': '📝 Markdown File',
        '.json': '🔧 JSON Data',
        '.html': '🌐 HTML Document',
        '.vtt': '🎬 Video Transcript'
    }
    
    # Processing method mapping
    processing_map = {
        '.pdf': ('🔍 Azure Document Intelligence', 'Advanced OCR, layout analysis, table extraction'),
        '.docx': ('🔍 Azure Document Intelligence', 'Layout analysis, text extraction, formatting preservation'),
        '.pptx': ('🔍 Azure Document Intelligence', 'Slide analysis, text extraction, layout understanding'),
        '.xlsx': ('🐼 Pandas Parser', 'Structured spreadsheet data extraction'),
        '.xls': ('🐼 Pandas Parser', 'Legacy Excel format processing'),
        '.csv': ('🐼 Pandas Parser', 'Comma-separated values processing'),
        '.png': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.jpg': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.jpeg': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.bmp': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.tiff': ('🔍 Azure Document Intelligence', 'OCR text extraction from images'),
        '.txt': ('📝 Simple Text Parser', 'Direct text content extraction'),
        '.md': ('📝 Markdown Parser', 'Markdown formatting with text extraction'),
        '.json': ('🔧 JSON Parser', 'Structured JSON data processing'),
        '.html': ('🔍 Azure Document Intelligence', 'HTML structure and content analysis'),
        '.vtt': ('🎬 Transcript Processor', 'Video subtitle and timing extraction')
    }
    
    file_type = file_type_map.get(ext, f'📄 {ext.upper()} File')
    method, capabilities = processing_map.get(ext, ('🔗 LangChain Chunker', 'General purpose text processing'))
    
    info_container = st.container()
    with info_container:
        col1, col2, col3 = st.columns([2, 3, 3])
        
        with col1:
            st.markdown(f"**File:** {file_type}")
            st.markdown(f"📋 `{file_name}`")
            
        with col2:
            st.markdown(f"**Processing Tool:** {method}")
            if show_capabilities:
                st.markdown(f"⚙️ {capabilities}")
                
        with col3:
            if ext in ['.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.html']:
                st.markdown("🎯 **Advanced Features:**")
                features = ["✅ Layout Analysis", "✅ Smart Text Extraction", "✅ OCR Processing"]
                if chunker_type == "MultimodalChunker":
                    features.extend(["✅ Figure Detection", "✅ AI Image Captions", "✅ Multimodal Processing"])
                for feature in features:
                    st.markdown(f"   {feature}")

# -----------------------------------------------------------------------------
# Streamlit UI wrapper (run with: streamlit run agentic-rag-demo.py)
# -----------------------------------------------------------------------------
def run_streamlit_ui() -> None:
    # Import required modules at function scope to avoid namespace conflicts
    import json as local_json
    from subprocess import check_output, CalledProcessError
    
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
    # Initialize search client for index management
    _, root_index_client = init_search_client()
    
    tab_health, tab_create, tab_manage, tab_test, tab_cfg, tab_ai = st.tabs([
        "🩺 Health Check",
        "1️⃣ Create Index",
        "2️⃣ Manage Index",
        "3️⃣ Test Retrieval",
        "⚙️ Function Config",
        "🤖 AI Foundry Agent"
    ])

    # Health Check Tab
    with tab_health:
        st.header("🩺 Service Health Check")
        if st.button("🔄 Check All Services"):
            with st.spinner("Checking services..."):
                results, all_healthy, troubleshooting = check_all_services()
                st.session_state['health_results'] = results
                st.session_state['all_healthy'] = all_healthy
                st.session_state['troubleshooting'] = troubleshooting

        if 'health_results' in st.session_state:
            results = st.session_state['health_results']
            all_healthy = st.session_state['all_healthy']
            troubleshooting = st.session_state.get('troubleshooting', None)
            
            if all_healthy:
                st.success("🎉 All services are healthy and ready!")
            else:
                st.error("⚠️ Some services have issues. Please check configuration before proceeding to other tabs.")
            
            for service_name, (status, message) in results.items():
                st.write(f"**{service_name}:** {'✅' if status else '❌'} {message}")
                
                # Show troubleshooting info for failed services
                if not status and troubleshooting and service_name in troubleshooting:
                    with st.expander(f"Troubleshooting steps for {service_name}", expanded=True):
                        st.info(troubleshooting[service_name])
                        
                        # For OpenAI specifically, add environment variable inspection
                        if service_name == "OpenAI":
                            st.subheader("Environment Variables")
                            env_vars = {
                                "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT", "Not set"),
                                "AZURE_OPENAI_ENDPOINT_41": os.getenv("AZURE_OPENAI_ENDPOINT_41", "Not set"),
                                "AZURE_OPENAI_ENDPOINT_4o": os.getenv("AZURE_OPENAI_ENDPOINT_4o", "Not set"),
                                "AZURE_OPENAI_KEY": "***" if os.getenv("AZURE_OPENAI_KEY") else "Not set",
                                "AZURE_OPENAI_KEY_41": "***" if os.getenv("AZURE_OPENAI_KEY_41") else "Not set",
                                "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "Not set"),
                                "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT", "Not set"),
                                "AZURE_OPENAI_DEPLOYMENT_41": os.getenv("AZURE_OPENAI_DEPLOYMENT_41", "Not set"),
                            }
                            st.json(env_vars)
                # For Document Intelligence service, add more information even if it's healthy
                if service_name == "Document Intelligence":
                    with st.expander("Document Intelligence Details", expanded=False):
                        st.markdown("""
                        ### Document Intelligence API Versions
                        
                        **Document Intelligence 4.0 API (2023-10-31 and newer):**
                        - Supports DOCX and PPTX parsing
                        - Enhanced layout analysis
                        - More accurate results
                        - Available in 2023-10-31-preview, 2024-02-29-preview, 2024-11-30 (General Availability) API versions
                        
                        **Document Intelligence 3.x API:**
                        - Basic document analysis features
                        - PDF and image analysis
                        - Limited DOCX/PPTX support
                        
                        If your service says "❌ Not Available" for Document Intelligence 4.0 API but you believe you have a 4.0 API resource,
                        check that you're using the correct environment variables that point to your 4.0 API resource.
                        """)
                        
                        # Show environment variables
                        st.subheader("Environment Variables")
                        env_vars = {
                            "DOCUMENT_INTEL_ENDPOINT": os.getenv("DOCUMENT_INTEL_ENDPOINT", "Not set"),
                            "DOCUMENT_INTEL_KEY": "***" if os.getenv("DOCUMENT_INTEL_KEY") else "Not set",
                            "AZURE_FORMREC_SERVICE": os.getenv("AZURE_FORMREC_SERVICE", "Not set (legacy)"),
                            "AZURE_FORMREC_KEY": "***" if os.getenv("AZURE_FORMREC_KEY") else "Not set (legacy)",
                            "AZURE_FORMRECOGNIZER_ENDPOINT": os.getenv("AZURE_FORMRECOGNIZER_ENDPOINT", "Not set (legacy)"),
                            "AZURE_FORMRECOGNIZER_KEY": "***" if os.getenv("AZURE_FORMRECOGNIZER_KEY") else "Not set (legacy)"
                        }
                        st.json(env_vars)
        else:
            st.info("Run a health check before using other tabs.")

    # Block other tabs if health check not passed
    def health_block():
        if 'all_healthy' not in st.session_state or not st.session_state['all_healthy']:
            st.warning("Please run the Health Check tab and ensure all services are healthy before using this feature.")
            st.stop()

    # ─────────────────── Tab 1 – Create Index ────────────────────────────
    with tab_create:
        health_block()
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
        health_block()
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
        st.markdown(
            "פורמטים נתמכים בהעלאה ישירה: **PDF, DOCX, PPTX, XLSX/CSV, TXT, MD, JSON**  \n"
            "_קבצים אחרים יידחו אוטומטית או יועלו כ‑binary ללא חיפוש סמנטי._"
        )
        
        # Processing Information Section
        with st.expander("ℹ️ Document Processing Information", expanded=False):
            st.markdown("### 🔧 Processing Tools & Capabilities")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🔍 Azure Document Intelligence")
                st.markdown("**Supported:** PDF, DOCX, PPTX, Images (PNG, JPG, BMP, TIFF)")
                st.markdown("**Capabilities:**")
                st.markdown("✅ Advanced OCR with high accuracy")
                st.markdown("✅ Layout and structure analysis")
                st.markdown("✅ Table extraction and formatting")
                st.markdown("✅ Figure and image detection")
                st.markdown("✅ Page-aware text chunking")
                st.markdown("✅ Multimodal processing (when enabled)")
                
                st.markdown("#### 🐼 Pandas Parser")
                st.markdown("**Supported:** CSV, XLS, XLSX")
                st.markdown("**Capabilities:**")
                st.markdown("✅ Structured data extraction")
                st.markdown("✅ Multiple sheet processing")
                st.markdown("✅ Data type preservation")
                
            with col2:
                st.markdown("#### 🔗 LangChain Chunker")
                st.markdown("**Supported:** General text files")
                st.markdown("**Capabilities:**")
                st.markdown("✅ Smart text chunking")
                st.markdown("✅ Overlap management")
                st.markdown("✅ Token-aware splitting")
                
                st.markdown("#### 📝 Simple Parser")
                st.markdown("**Supported:** TXT, MD, JSON")
                st.markdown("**Capabilities:**")
                st.markdown("✅ Direct text extraction")
                st.markdown("✅ Format preservation")
                st.markdown("✅ Fast processing")
            
            st.markdown("---")
            st.info("💡 **Tip:** Office documents (DOCX, PPTX) now automatically use Azure Document Intelligence for better structure preservation and metadata extraction!")
        
        if not st.session_state.selected_index:
            st.info("Select an index first.")
        else:
            uploaded = st.file_uploader(
                "בחר קבצים (PDF, DOCX, PPTX, XLSX/CSV, TXT, MD, JSON, RTX, XML)",
                type=["pdf", "docx", "pptx", "xlsx", "csv", "txt", "md", "json", "rtx", "xml"],
                accept_multiple_files=True
            )
            if uploaded and st.button("🚀 Ingest"):
                # Display processing overview
                st.markdown("### 🔄 Processing Overview")
                for pf in uploaded:
                    ext = os.path.splitext(pf.name)[-1].lower()
                    display_processing_info(pf.name, ext, show_capabilities=False)
                    st.markdown("---")
                
                with st.spinner("Embedding and uploading…"):
                    ###############################################
                    # Build buffered sender with error‑tracking
                    ###############################################
                    failed_ids: list[str] = []

                    def _on_error(action) -> None:
                        try:
                            failed_ids.append(action.get("id", "?"))
                        except Exception as exc:
                            logging.error("⚠️  on_error callback failed to record ID: %s", exc)
                            failed_ids.append("?")

                    sender = SearchIndexingBufferedSender(
                        endpoint=env("AZURE_SEARCH_ENDPOINT"),
                        index_name=st.session_state.selected_index,
                        credential=_search_credential(),
                        batch_size=100,
                        auto_flush_interval=5,
                        on_error=_on_error,
                    )

                    embed_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
                    total_pages = 0
                    for pf in uploaded:
                        ext = os.path.splitext(pf.name)[-1].lower()
                        docs = []

                        if ext == ".pdf":
                            # --- PDF path -------------------------------------------------
                            docs = pdf_to_documents(pf, oai_client, embed_deploy)
                        else:
                            # --- ALL other files – use DocumentChunker --------------------
                            try:
                                docs = _chunk_to_docs(
                                    pf.name,
                                    bytes(pf.getbuffer()),
                                    "",          # no public URL for local upload
                                    oai_client,
                                    embed_deploy,
                                )
                            except Exception as docerr:
                                logging.error("DocumentChunker failed for %s: %s", pf.name, docerr)
                                docs = []

                        if not docs:
                            continue
                            
                        # Show processing information to user
                        processing_info = []
                        for doc in docs[:1]:  # Check first document for processing info
                            method = doc.get("extraction_method", "unknown")
                            doc_type = doc.get("document_type", "Unknown")
                            has_figs = doc.get("has_figures", False)
                            
                            if method == "document_intelligence":
                                processing_info.append(f"📄 **{pf.name}** ({doc_type})")
                                processing_info.append("🔍 **Processing Tool:** Azure Document Intelligence")
                                processing_info.append("✨ **Capabilities:** Advanced layout analysis, OCR, table extraction")
                                if has_figs:
                                    processing_info.append("🖼️ **Figures:** Detected and processed with multimodal AI")
                            elif method == "simple_parser":
                                processing_info.append(f"📄 **{pf.name}** ({doc_type})")
                                processing_info.append("🔧 **Processing Tool:** Simple text parser")
                                processing_info.append("📝 **Capabilities:** Basic text extraction")
                            elif method == "pandas_parser":
                                processing_info.append(f"📊 **{pf.name}** ({doc_type})")
                                processing_info.append("🐼 **Processing Tool:** Pandas data parser")
                                processing_info.append("📈 **Capabilities:** Structured data extraction")
                            elif method == "langchain_chunker":
                                processing_info.append(f"📄 **{pf.name}** ({doc_type})")
                                processing_info.append("🔗 **Processing Tool:** LangChain document loader")
                                processing_info.append("⚡ **Capabilities:** Smart text chunking")
                        
                        if processing_info:
                            with st.expander(f"ℹ️ Processing Details for {pf.name}", expanded=False):
                                for info in processing_info:
                                    st.markdown(info)
                                st.markdown(f"📊 **Chunks Created:** {len(docs)}")
                        
                        sender.upload_documents(documents=docs)
                        total_pages += len(docs)

                    sender.close()

                    try:
                        search_client, _ = init_search_client(st.session_state.selected_index)
                        for _ in range(30):
                            if search_client.get_document_count() > 0:
                                break
                            time.sleep(1)
                    except Exception as probe_err:
                        logging.warning("Search probe failed: %s", probe_err)

                    success_pages = total_pages - len(failed_ids)
                    if failed_ids:
                        st.error(f"❌ {len(failed_ids)} pages failed to index – see logs for details.")
                    if success_pages:
                        st.success(f"✅ Indexed {success_pages} pages into **{st.session_state.selected_index}**.")

            # --- SharePoint Ingestion Button and Logic ---
            st.markdown("---")
            st.subheader("📁 Ingest files from SharePoint Folder (any type)")
            st.caption(
                "פורמטים מומלצים: **PDF, DOCX, PPTX, XLSX/CSV, TXT, MD, JSON**.  "
                "תוכל להזין ב‑תיבה למטה את סיומות קבצים מופרדות בפסיקים, או להשאיר ריק ל‑“הכול”."
            )

            # --- SharePoint config UI ---
            def _get_env_or_default(key, default=None):
                v = os.getenv(key)
                return v if v is not None and v != "" else default

            if "sp_site_domain" not in st.session_state:
                st.session_state.sp_site_domain = _get_env_or_default("SHAREPOINT_SITE_DOMAIN", "")
            if "sp_site_name" not in st.session_state:
                st.session_state.sp_site_name = _get_env_or_default("SHAREPOINT_SITE_NAME", "")
            if "sp_drive_name" not in st.session_state:
                st.session_state.sp_drive_name = _get_env_or_default("SHAREPOINT_DRIVE_NAME", "")
            if "sp_folder_path" not in st.session_state:
                st.session_state.sp_folder_path = _get_env_or_default("SHAREPOINT_SITE_FOLDER", "/")

            st.text("Current SharePoint settings:")
            st.session_state.sp_site_domain = st.text_input(
                "SharePoint Site Domain (e.g. mngenvmcap623661.sharepoint.com)",
                value=st.session_state.sp_site_domain or "",
                key="sp_site_domain_input"
            )
            st.session_state.sp_site_name = st.text_input(
                "SharePoint Site Name (blank or 'root' for root site)",
                value=st.session_state.sp_site_name or "",
                key="sp_site_name_input"
            )
            st.session_state.sp_drive_name = st.text_input(
                "SharePoint Drive Name (e.g. Documents)",
                value=st.session_state.sp_drive_name or "",
                key="sp_drive_name_input"
            )
            st.session_state.sp_folder_path = st.text_input(
                "SharePoint Folder Path (e.g. /ASKMANHAR)",
                value=st.session_state.sp_folder_path or "/",
                key="sp_folder_path_input"
            )

            file_type_input = st.text_input(
                "File types to ingest (comma-separated, e.g. pdf,docx,xlsx,txt). Leave blank for all:",
                value="pdf"
            )
            file_types = [ft.strip() for ft in file_type_input.split(",") if ft.strip()] if file_type_input else None
            if st.button("🔗 Ingest from SharePoint"):
                with st.spinner("Fetching and ingesting files from SharePoint…"):
                    # Initialize processing status display
                    status_container = st.empty()
                    
                    try:
                        from connectors.sharepoint.sharepoint_data_reader import SharePointDataReader
                        import io
                        sharepoint_reader = SharePointDataReader()
                        # Use user-specified values, fallback to env if blank
                        site_domain = st.session_state.sp_site_domain or _get_env_or_default("SHAREPOINT_SITE_DOMAIN", "")
                        site_name = st.session_state.sp_site_name or _get_env_or_default("SHAREPOINT_SITE_NAME", "")
                        folder_path = st.session_state.sp_folder_path or _get_env_or_default("SHAREPOINT_SITE_FOLDER", "/")
                        drive_name = st.session_state.sp_drive_name or _get_env_or_default("SHAREPOINT_DRIVE_NAME", "")
                        sp_files = sharepoint_reader.retrieve_sharepoint_files_content(
                            site_domain=site_domain,
                            site_name=site_name,
                            folder_path=folder_path,
                            file_formats=file_types,
                            drive_name=drive_name
                        )
                        if not sp_files:
                            st.warning("No files found in the SharePoint folder.")
                        else:
                            total_files = len(sp_files)
                            st.info(f"Found {total_files} file(s) in the SharePoint folder.")
                            progress_bar = st.progress(0, text="Starting ingestion...")
                            failed_ids = []
                            sender = SearchIndexingBufferedSender(
                                endpoint=env("AZURE_SEARCH_ENDPOINT"),
                                index_name=st.session_state.selected_index,
                                credential=_search_credential(),
                                batch_size=100,
                                auto_flush_interval=5,
                                on_error=lambda action: failed_ids.append(action.get("id", "?")),
                            )
                            embed_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
                            total_pages = 0
                            for idx, file in enumerate(sp_files):
                                file_bytes = file.get("content")
                                fname = file.get("name")
                                file_url = file.get("source") or file.get("webUrl")
                                st.info(f"Processing file {idx+1}/{total_files}: {fname}")
                                if not file_bytes or not fname:
                                    progress_bar.progress((idx + 1) / total_files, text=f"Skipped file {idx+1}/{total_files}")
                                    continue
                                    pdf_file.name = fname
                                    docs = pdf_to_documents(pdf_file, oai_client, embed_deploy)
                                    # Patch each doc's url to SharePoint webUrl
                                    for d in docs:
                                        d["url"] = file_url
                                else:
                                    try:
                                        docs = _chunk_to_docs(
                                            fname,
                                            file_bytes,
                                            file_url,
                                            oai_client,
                                            embed_deploy,
                                        )
                                    except Exception as derr:
                                        logging.error("Chunker failed for %s: %s", fname, derr)
                                        docs = []
                                sender.upload_documents(documents=docs)
                                total_pages += len(docs)
                                progress_bar.progress((idx + 1) / total_files, text=f"Processed {idx+1}/{total_files} files")
                            sender.close()
                            try:
                                search_client, _ = init_search_client(st.session_state.selected_index)
                                for _ in range(30):
                                    if search_client.get_document_count() > 0:
                                        break
                                    time.sleep(1)
                            except Exception as probe_err:
                                logging.warning("Search probe failed: %s", probe_err)
                            success_pages = total_pages - len(failed_ids)
                            if failed_ids:
                                st.error(f"❌ {len(failed_ids)} pages failed to index – see logs for details.")
                            if success_pages:
                                st.success(f"✅ Indexed {success_pages} pages from SharePoint into **{st.session_state.selected_index}**.")
                    except Exception as ex:
                        st.error(f"SharePoint ingestion failed: {ex}")

    # ─────────────────── Tab 3 – Test Retrieval ──────────────────────────
    with tab_test:
        health_block()
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
                    response_fields=["id", "text", "source_file", "url", "doc_key"],
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

                # ── Debug info ─────────────────────────────
                st.markdown("---")
                st.markdown("#### 🐞 Debug Info")
                st.write({
                    "AZURE_SEARCH_ENDPOINT": os.getenv("AZURE_SEARCH_ENDPOINT"),
                    "AZURE_SEARCH_KEY": os.getenv("AZURE_SEARCH_KEY"),
                    "Selected Index": st.session_state.selected_index,
                    "Auth Mode": "API Key" if os.getenv("AZURE_SEARCH_KEY") else "RBAC",
                    "Request Payload": ka_req.dict() if hasattr(ka_req, 'dict') else str(ka_req)
                })
                st.markdown("---")

                with st.spinner("Retrieving…"):
                    try:
                        # ---------- SDK call: retrieve chunks --------------------
                        result = agent_client.knowledge_retrieval.retrieve(
                            retrieval_request=ka_req
                        )
                    except Exception as ex:
                        import traceback
                        st.error(f"Retrieval failed: {ex}")
                        st.code(traceback.format_exc())
                        st.stop()

                # Build chunks directly from the structured Message → Content objects
                chunks = []
                for msg in result.response:
                    for c in getattr(msg, "content", []):
                        # Prefer metadata carried inside the underlying Search document
                        sdoc = getattr(c, "search_document", {}) or {}

                        # Get the doc_key or source_file from the search document
                        doc_key = sdoc.get("doc_key", "")
                        source_file = sdoc.get("source_file", "")
                        
                        # Extract document name from the content if it's formatted like "[filename] content"
                        content_text = getattr(c, "text", "")
                        extracted_filename = ""
                        if content_text and content_text.startswith("[") and "]" in content_text:
                            extracted_filename = content_text.split("]")[0].strip("[")
                            # Clean up the content if we found a filename prefix
                            content_text = content_text[content_text.find("]")+1:].strip()
                        
                        chunk = {
                            # ref_id may be missing – fall back to running index
                            "ref_id": getattr(c, "ref_id", None) or len(chunks),
                            "content": content_text,
                            "source_file": source_file or doc_key or extracted_filename,
                            "doc_key": doc_key or source_file or extracted_filename,
                            "url": sdoc.get("url", "")
                        }
                        chunks.append(chunk)
                
                # Build sources list – keep one entry per source_file but make sure to
                # capture the first non‑empty URL we encounter.
                # ------------------ build deduplicated sources list ------------------
                tmp_sources: Dict[str, dict] = {}
                for itm in chunks:
                    # Handle both dictionary and string/JSON formats
                    if isinstance(itm, str) and itm.startswith('{'):
                        try:
                            itm = local_json.loads(itm)
                        except:
                            pass  # Keep as is if parsing fails
                    
                    # Extract source name from content if needed
                    content = itm.get("content", "")
                    extracted_src = ""
                    if isinstance(content, str) and content.startswith('[') and ']' in content:
                        extracted_src = content[1:content.find(']')]
                    
                    # Prefer source_file or doc_key; fall back to extracted name, URL or generic "doc#" label
                    src_name = (
                        itm.get("source_file")
                        or itm.get("doc_key")
                        or extracted_src
                        or itm.get("url")
                        or f"doc{itm.get('ref_id', itm.get('id', '?'))}"
                    )
                    src_url = itm.get("url", "")
                    # First time we see this source → add entry
                    if src_name not in tmp_sources:
                        tmp_sources[src_name] = {"source_file": src_name, "url": src_url}
                    # If we saw this source before but URL was empty, update when we
                    # finally encounter a non‑empty URL.
                    elif not tmp_sources[src_name]["url"] and src_url:
                        tmp_sources[src_name]["url"] = src_url

                sources_data = list(tmp_sources.values())
                # ---- Best‑effort URL enrichment (if still missing) ----
                for entry in sources_data:
                        if entry.get("url"):
                            continue  # already have one
                        try:
                            # Try to fetch first doc whose source_file matches exactly
                            safe_src = entry["source_file"].replace("'", "''")  # escape single quotes for OData
                            filt = f"source_file eq '{safe_src}'"
                            hits = search_client.search(search_text="*", filter=filt, top=1)
                            for h in hits:
                                if "url" in h and h["url"]:
                                    entry["url"] = h["url"]
                                    break
                        except Exception:
                            pass  # silent failure; leave url empty

                # ---------- Generate answer from chunks -------------------------------
                # Debug chunk data
                st.expander("Debug Chunks Data").json(chunks)
                
                # Format each chunk with its source file for better readability
                formatted_chunks = []
                for c in chunks:
                    source = c.get("source_file") or c.get("doc_key") or f"doc{c.get('ref_id')}"
                    content = c.get("content", "")
                    formatted_chunks.append(f"**Source: {source}**\n\n{content}\n")
                
                answer_text = "\n\n---\n\n".join(formatted_chunks) if chunks else ""
                answer_text = answer_text.strip()
                chunk_count = len(chunks) if chunks else 0

                # Update sidebar diagnostic
                st.session_state.dbg_chunks = chunk_count

                # ---------- Render assistant answer ------------------------------
                with st.chat_message("assistant"):
                    # Ensure we're displaying plain text, not raw JSON
                    formatted_answer = answer_text
                    if isinstance(answer_text, str) and answer_text.startswith('{"'):
                        try:
                            # Try to parse it as JSON and extract content field
                            parsed = local_json.loads(answer_text)
                            if isinstance(parsed, list):
                                formatted_chunks = []
                                for item in parsed:
                                    if isinstance(item, dict) and 'content' in item:
                                        chunk_content = item['content']
                                        src = None
                                        if chunk_content.startswith('[') and ']' in chunk_content:
                                            src_end = chunk_content.find(']')
                                            src = chunk_content[1:src_end]
                                            chunk_content = chunk_content[src_end+1:].strip()
                                        if src:
                                            formatted_chunks.append(f"**Source: {src}**\n\n{chunk_content}")
                                        else:
                                            formatted_chunks.append(chunk_content)
                                formatted_answer = "\n\n---\n\n".join(formatted_chunks)
                            elif isinstance(parsed, dict) and 'content' in parsed:
                                formatted_answer = parsed['content']
                        except:
                            # If JSON parsing fails, keep the original text
                            pass
                    
                    st.markdown(formatted_answer or "*[לא התקבלה תשובה]*", unsafe_allow_html=True)

                    if sources_data:
                        st.markdown("#### 🗂️ Sources")
                        for src in sources_data:
                            if isinstance(src, str) and src.startswith('{'):
                                # Try to parse JSON source
                                try:
                                    parsed_src = local_json.loads(src)
                                    name = parsed_src.get("source_file") or parsed_src.get("content", "").split("]")[0].strip("[") if "]" in parsed_src.get("content", "") else "unknown"
                                    url = parsed_src.get("url", "")
                                except:
                                    name = "unknown"
                                    url = ""
                            else:
                                name = src.get("source_file") or src.get("url") or "unknown"
                                url = src.get("url", "")
                                
                            if url:
                                # clickable name **and** raw URL so the user always sees the link target
                                st.markdown(f"- [{name}]({url}) – <{url}>")
                            else:
                                st.markdown(f"- {name}")

                # ---------- Optional: raw chunks for debugging --------------------
                if isinstance(chunks, list) and chunks:
                    with st.expander("📚 Chunks", expanded=False):
                        for itm in chunks:
                            # Handle both dictionary and string/JSON formats
                            if isinstance(itm, str) and itm.startswith('{'):
                                try:
                                    import json
                                    parsed_itm = local_json.loads(itm)
                                    ref = parsed_itm.get("ref_id", parsed_itm.get("id", '?'))
                                    content = parsed_itm.get("content", "")
                                    if content.startswith('[') and ']' in content:
                                        src = content[1:content.find(']')]
                                        content = content[content.find(']')+1:].strip()
                                        st.markdown(f"**📄 מקור {ref} - {src}:**")
                                    else:
                                        st.markdown(f"**📄 מקור {ref}:**")
                                    st.write(content)
                                except:
                                    st.write(itm)  # Fallback to raw display
                            else:
                                ref = itm.get("ref_id", itm.get("id", '?'))
                                source = itm.get("source_file", "") or itm.get("doc_key", "")
                                if source:
                                    st.markdown(f"**📄 מקור {ref} - {source}:**")
                                else:
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
            az_acc = local_json.loads(check_output(["az", "account", "show", "-o", "json"], text=True))
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
        # Normalise variable names (func_name / func_rg) and keep old aliases
        func_name = app
        func_rg   = rg

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
                if not all((sub_id, func_rg, func_name)):
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
                            func_rg,
                            func_name,
                            {"properties": new_props}
                        )
                        st.success(f"✅ Updated {len(new_props)} settings on **{func_name}**")
                    except Exception as push_err:
                        st.error(f"Failed to update Function settings:\n{push_err}")

            # ── Deploy local ./function code to this Function App ─────────────
            st.divider()
            # ── Deploy local ./function code to this Function App ─────────────
        st.divider()
        if st.button("🚀 Deploy local code to Function"):
            if not all((sub_id, func_rg, func_name)):
                st.error("Fill subscription / RG / Function-App first.")
            else:
                try:
                    st.info("⏳ Zipping and deploying, please wait…")

                    func_dir = Path.cwd() / "function"
                    if not func_dir.exists():
                        st.error(f"Local 'function' folder not found: {func_dir}")
                        st.stop()

                    with tempfile.TemporaryDirectory() as td:
                        zip_path = Path(td) / "function.zip"
                        _zip_function_folder(func_dir, zip_path)

                        cmd = [
                            "az", "functionapp", "deployment", "source", "config-zip",
                            "-g", func_rg,
                            "-n", func_name,
                            "--src", str(zip_path)
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                        st.success("✅ Deployment completed")
                        if result.stdout:
                            st.text(result.stdout.strip())
                except subprocess.CalledProcessError as cerr:
                    st.error(f"az CLI deployment failed:\n{cerr.stderr}")
                except Exception as ex:
                    st.error(f"Failed to deploy: {ex}")

    # ─────────────────── Single Tab – AI Foundry Agent ──────────────────
    with tab_ai:
        health_block()
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
                "3. After that, print a short “Sources:” list. For each object in \"sources\" show its **source_file**, and – if \"url\" is present and not empty – append “ – <url>”. If source_file is empty, show the url instead; if both are missing, use the placeholder doc#.\n"
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

##############################################################################
# Health Check Functions 
##############################################################################

def _init_openai_for_health_check():
    """
    Initialize OpenAI client for health check using the same logic as the rest of the app.
    Tries all available endpoint configurations in order: _41, _4o, and base.
    """
    clients = []
    models_tried = []
    
    # Try the endpoint variations in priority order
    for suffix in ["_41", "_4o", ""]:
        endpoint = os.getenv(f"AZURE_OPENAI_ENDPOINT{suffix}", "").strip()
        key = os.getenv(f"AZURE_OPENAI_KEY{suffix}", "").strip()
        api_version = os.getenv(f"AZURE_OPENAI_API_VERSION{suffix}", "2024-05-01-preview").strip()
        deployment = os.getenv(f"AZURE_OPENAI_DEPLOYMENT{suffix}", "").strip()
        
        if endpoint and (key or os.getenv("AZURE_TENANT_ID")):
            models_tried.append(f"AZURE_OPENAI_ENDPOINT{suffix}")
            try:
                # If key is available, use key auth
                if key:
                    client = AzureOpenAI(
                        azure_endpoint=endpoint,
                        api_key=key,
                        api_version=api_version
                    )
                else:
                    # Use AAD auth as fallback
                    aad = get_bearer_token_provider(
                        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                    )
                    client = AzureOpenAI(
                        azure_endpoint=endpoint,
                        azure_ad_token_provider=aad,
                        api_version=api_version
                    )
                    
                # Verify the client works by listing models
                models = list(client.models.list())
                clients.append({
                    "client": client,
                    "endpoint_var": f"AZURE_OPENAI_ENDPOINT{suffix}",
                    "endpoint": endpoint,
                    "models": models,
                    "deployment": deployment
                })
            except Exception:
                pass
    
    if not clients:
        return None, models_tried
    
    # Return the first working client
    return clients[0], models_tried

def check_openai_health():
    """Check if OpenAI service is available and responsive."""
    try:
        client_info, models_tried = _init_openai_for_health_check()
        
        if not client_info:
            if not models_tried:
                return False, "❌ No OpenAI endpoints configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables."
            else:
                return False, f"❌ Could not connect to any OpenAI endpoints. Tried: {', '.join(models_tried)}"
        
        # Successfully connected
        model_count = len(client_info["models"])
        model_names = ", ".join([m.id for m in client_info["models"][:3]])
        if model_count > 3:
            model_names += f", and {model_count - 3} more"
        
        endpoint_var = client_info["endpoint_var"]
        deployment = client_info["deployment"]
        deployment_info = f" (deployment: {deployment})" if deployment else ""
        
        return True, f"✅ Connected successfully via {endpoint_var}{deployment_info}. Found {model_count} models: {model_names}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def check_ai_search_health():
    """Check if Azure AI Search service is available and responsive."""
    try:
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
        if not search_endpoint:
            return False, "Missing AZURE_SEARCH_ENDPOINT"
        
        credential = _search_credential()
        client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        
        # Try to list indexes as a simple health check
        indexes = list(client.list_indexes())
        index_count = len(indexes)
        
        auth_mode = "Azure AD" if not os.getenv("AZURE_SEARCH_KEY") else "API Key"
        rbac_status = "🟢 Enabled" if _rbac_enabled(search_endpoint) else "🔴 Disabled"
        
        return True, f"✅ Connected successfully. Found {index_count} indexes. Auth: {auth_mode}, RBAC: {rbac_status}"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def check_document_intelligence_health():
    """Check if Document Intelligence service is available and responsive."""
    try:
        from tools.document_intelligence_client import DocumentIntelligenceClientWrapper
        import importlib
        
        # Force reload the module to pick up our changes
        import tools.document_intelligence_client
        importlib.reload(tools.document_intelligence_client)
        from tools.document_intelligence_client import DocumentIntelligenceClientWrapper
        
        docint_wrapper = DocumentIntelligenceClientWrapper()
        
        if not docint_wrapper.client:
            return False, "❌ Document Intelligence not configured (missing endpoint/key)"
        
        # Get endpoint information
        endpoint = (
            os.getenv("DOCUMENT_INTEL_ENDPOINT") or
            os.getenv("AZURE_FORMREC_SERVICE") or
            os.getenv("AZURE_FORMRECOGNIZER_ENDPOINT") or
            "Unknown"
        )
        
        # Try to get API version information
        api_version = "Unknown"
        if hasattr(docint_wrapper.client, '_config') and hasattr(docint_wrapper.client._config, 'api_version'):
            api_version = getattr(docint_wrapper.client._config, 'api_version', 'Unknown')
        
        # Check if Document Intelligence 4.0 API is available
        docint_40_status = "✅ Available" if docint_wrapper.docint_40_api else "❌ Not Available"
        
        # Build informational message
        features = []
        
        # Check document formats support
        if docint_wrapper.docint_40_api:
            features.append("DOCX/PPTX parsing supported")
        else:
            features.append("DOCX/PPTX parsing may be limited")
        
        # Check if we can analyze basic documents
        if hasattr(docint_wrapper.client, 'begin_analyze_document'):
            features.append("Basic document analysis available")
        
        # Check for layout analysis
        if hasattr(docint_wrapper.client, 'begin_analyze_layout'):
            features.append("Layout analysis available")
        
        features_str = ", ".join(features)
        
        # Format a nice message
        api_info = f"API Version: {api_version}"
        return True, f"✅ Connected successfully to {endpoint}. Doc Intelligence 4.0: {docint_40_status}. {api_info}. Features: {features_str}"
        
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def check_all_services():
    """Check health of all services and return summary."""
    results = {
        "OpenAI": check_openai_health(),
        "AI Search": check_ai_search_health(), 
        "Document Intelligence": check_document_intelligence_health()
    }
    
    all_healthy = all(status for status, _ in results.values())
    
    # Add troubleshooting info for failed services
    troubleshooting_info = {}
    if not results["OpenAI"][0]:
        troubleshooting_info["OpenAI"] = (
            "Check that your OpenAI environment variables are set correctly:\n"
            "- Either AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_ENDPOINT_41 should be set\n"
            "- AZURE_OPENAI_KEY should be set\n"
            "- Your app is using AZURE_OPENAI_ENDPOINT_41, ensure the health check can access it\n"
            "- Verify your network connection and firewall settings\n"
            "- Check the API version matches what your endpoint supports\n\n"
            "The app will use the suffix (_41, _4o) endpoints if available, falling back to the base variables."
        )
    if not results["AI Search"][0]:
        troubleshooting_info["AI Search"] = (
            "Check that AZURE_SEARCH_ENDPOINT is set correctly. "
            "If using API key authentication, ensure AZURE_SEARCH_KEY is set."
        )
    if not results["Document Intelligence"][0]:
        troubleshooting_info["Document Intelligence"] = (
            "Check that DOCUMENT_INTEL_ENDPOINT/DOCUMENT_INTEL_KEY or the legacy "
            "AZURE_FORMREC_SERVICE/AZURE_FORMREC_KEY environment variables are set correctly."
        )
    
    return results, all_healthy, troubleshooting_info if troubleshooting_info else None
# Add this guard to call run_streamlit_ui() when the script is run
if __name__ == "__main__":
    run_streamlit_ui()