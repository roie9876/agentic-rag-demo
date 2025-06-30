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
from datetime import datetime, timedelta  # Added for scheduler functionality

from pathlib import Path
from typing import List, Tuple, Dict

import pandas as pd           # ← ADD THIS LINE

# Import SharePoint components
from ui_sharepoint import SharePointIndexUI
from sharepoint_scheduler import SharePointScheduler
from sharepoint_index_manager import SharePointIndexManager
from sharepoint_reports import SharePointReports

# ---------------------------------------------------------------------------
# Streamlit Data‑Editor helper (works on both old & new versions)
# ---------------------------------------------------------------------------
import streamlit as st
from chunking import DocumentChunker
from tools.aoai import AzureOpenAIClient

# Import the test_retrieval module
from test_retrieval import render_test_retrieval_tab

# Import the Studio2Foundry module
from studio2foundry_tab import render_studio2foundry_tab

# Import extracted modules
from utils.azure_helpers import (
    get_search_credential,
    rbac_enabled, 
    get_az_logged_user,
    grant_search_role,
    grant_openai_role,
    reload_env_and_restart,
    env
)
from core.azure_clients import init_openai, init_search_client, init_agent_client
# Import document processing functions
from core.document_processor import (
    embed_text,
    pdf_to_documents,
    plainfile_to_docs as _plainfile_to_docs,
    chunk_to_docs as _chunk_to_docs,
    tabular_to_docs as _tabular_to_docs
)

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

# Health Check Module
from health_check import HealthChecker, HealthCheckUI

# Import the new module for AI Foundry functionality
from agent_foundry import (
    check_azure_cli_login, 
    get_ai_foundry_projects,
    create_ai_foundry_agent
)

# Import Azure Function helper module
from azure_function_helper import (
    load_env_vars,
    get_azure_subscription,
    list_function_apps,
    load_function_settings,
    push_function_settings,
    deploy_function_code
)

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

# ---------------------------------------------------------------------------
# RBAC status probe
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Azure CLI helpers
# ---------------------------------------------------------------------------

# Remove the duplicate function since it's now in agent_foundry.py
# def check_azure_cli_login() -> tuple[bool, dict | None]:
#     """
#     Return (logged_in, account_json_or_None) by running `az account show`.
#     """
#     try:
#         out = subprocess.check_output(
#             ["az", "account", "show", "--output", "json"],
#             text=True,
#             timeout=5,
#         )
#         return True, json.loads(out)
#     except subprocess.CalledProcessError:
#         return False, None
#     except Exception:
#         return False, None

# Remove the duplicate function since it's now in agent_foundry.py
# def get_ai_foundry_projects(cred: AzureCliCredential) -> list[dict]:
#     """
#     Return a list of Foundry projects visible to the signed‑in CLI user via
#     `az ai project list`. Each item includes:
#         {name, location, endpoint, resource_group, hub_name}
#     """
#     try:
#         out = subprocess.check_output(
#             ["az", "ai", "project", "list", "--output", "json"],
#             text=True,
#             timeout=10,
#         )
#         data = json.loads(out)
#         projs = []
#         for p in data:
#             projs.append(
#                 {
#                     "name": p["name"],
#                     "location": p["location"],
#                     "endpoint": p["properties"]["endpoint"],
#                     "resource_group": p["resourceGroup"],
#                     "hub_name": p["properties"].get("hubName", ""),
#                 }
#             )
#         return projs
#     except Exception as err:
#         logging.warning("Failed to list AI Foundry projects: %s", err)
#         return []

# ---------------------------------------------------------------------------
# Helper to grant OpenAI role
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Force‑reload .env at runtime
# ---------------------------------------------------------------------------

##############################################################################
# Environment helpers
##############################################################################

load_dotenv(Path(__file__).resolve().parent / ".env")
FUNCTION_KEY = os.getenv("AGENT_FUNC_KEY", "")
TOP_K_DEFAULT = int(os.getenv("TOP_K", 5))   # fallback for CLI path

# ───────── Text-based fallback for Office / plain files ─────────

# ─────────────── Fallback: CSV / XLS(X) → docs ───────────────

# ---------------------------------------------------------------------------
# Knowledge‑Agent client (cached per agent name)
# ---------------------------------------------------------------------------

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
                SimpleField(name="url",          type="Edm.String", filterable=True, searchable=True),
                SimpleField(name="doc_key",      type="Edm.String", filterable=True), # Added for proper document referencing
                # Enhanced metadata fields for Document Intelligence processing
                SimpleField(name="extraction_method", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="document_type", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="has_figures", type="Edm.Boolean", filterable=True, facetable=True),
                SimpleField(name="processing_timestamp", type="Edm.DateTimeOffset", filterable=True, sortable=True),
                # Multimodal fields for image processing
                SearchableField(name="content", type="Edm.String", analyzer_name="standard.lucene"),
                SearchField(name="contentVector",
                           type="Collection(Edm.Single)",
                           stored=False,
                           vector_search_dimensions=VECTOR_DIM,
                           vector_search_profile_name="hnsw_text_3_large"),
                SimpleField(name="imageCaptions", type="Edm.String", searchable=True, retrievable=True),
                SearchField(name="captionVector",
                           type="Collection(Edm.Single)",
                           stored=False,
                           vector_search_dimensions=VECTOR_DIM,
                           vector_search_profile_name="hnsw_text_3_large"),
                SimpleField(name="relatedImages", type="Collection(Edm.String)", filterable=True, retrievable=True),
                SimpleField(name="isMultimodal", type="Edm.Boolean", filterable=True, facetable=True),
                SimpleField(name="filename", type="Edm.String", filterable=True, facetable=True),
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

        # ----------- Knowledge-Agent עם api_key and max_output_size -------
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
            request_limits = KnowledgeAgentRequestLimits(
                max_output_size = 16000  # Match Azure Function's MAX_OUTPUT_SIZE default
            ),
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
        credential=get_search_credential(),
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

    # Create a base request with only the most essential parameters
    req_params = {
        "messages": ka_msgs,
        # Only include target_index_params if we actually specified one
        "target_index_params": target_params
        # NOTE: Removed request_limits with max_output_size - this parameter is set on the knowledge agent definition, not in retrieve requests
    }
    
    # Try to add optional parameters that might not be supported in all SDK versions
    try:
        # Create a test instance to check supported parameters
        test_req = KnowledgeAgentRetrievalRequest(messages=ka_msgs)
        
        # Check if citation_field_name is supported
        if hasattr(test_req, "citation_field_name"):
            req_params["citation_field_name"] = "source_file"
        
        # Add any other potentially unsupported parameters here
    except Exception:
        pass  # Silently continue with base parameters
    
    # Create the actual request
    req = KnowledgeAgentRetrievalRequest(**req_params)

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
# def _zip_function_folder(func_dir: Path, zip_path: Path) -> None:
#     """Zip *func_dir* (כולל host.json וכו') כ-relative paths אל *zip_path*."""
#     with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
#         for itm in func_dir.rglob("*"):
#             if itm.is_file():
#                 zf.write(itm, itm.relative_to(func_dir))
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
        auth_mode = "Managed Identity (RBAC)" if not os.getenv("AZURE_SEARCH_KEY") else "API Key"
        st.caption(f"🔑 Search auth: {auth_mode}")
        rbac_flag = rbac_enabled(env("AZURE_SEARCH_ENDPOINT"))
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
        # NOTE: max_output_size is set on the knowledge agent definition, not in retrieve requests - commenting out
        # st.session_state.max_output_size = st.slider("Knowledge‑agent maxOutputSize", 1000, 16000, 5000, 500)
        st.session_state.max_tokens = st.slider("Max completion tokens", 256, 32768, 32768, 256)

        chunks_placeholder = st.empty()
        chunks_placeholder.caption(f"Chunks sent to LLM: {st.session_state.get('dbg_chunks', 0)}")

        if st.button("🔄 Reload .env & restart"):
            reload_env_and_restart()

    # ── Tabbed layout ─────────────────────────────────────────────────────
    # Initialize search client for index management
    _, root_index_client = init_search_client()
    
    tab_health, tab_create, tab_manage, tab_sharepoint, tab_test, tab_cfg, tab_ai, tab_studio2foundry = st.tabs([
        "🩺 Health Check",
        "1️⃣ Create Index",
        "2️⃣ Manage Index",
        "📁 SharePoint Index",
        "3️⃣ Test Retrieval",
        "⚙️ Function Config",
        "🤖 AI Foundry Agent",
        "🏭 Studio2Foundry"
    ])

    # Health Check Tab
    with tab_health:
        # Initialize and render health check UI
        health_ui = HealthCheckUI()
        health_ui.render_health_check_tab()

    # Show warnings if health check not passed (optional, non-blocking)
    def health_block():
        health_ui = HealthCheckUI()
        health_ui.health_block()

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
        
        # =================== AGENT CONFIGURATION SECTION ===================
        if st.session_state.selected_index:
            st.subheader("🤖 Knowledge Agent Configuration")
            agent_name = f"{st.session_state.selected_index}-agent"
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Agent Name:** `{agent_name}`")
                
                # Check if agent exists and get current configuration
                agent_exists = False
                current_config = {}
                
                try:
                    # Try to get current agent configuration
                    current_agent = root_index_client.get_agent(agent_name)
                    agent_exists = True
                    
                    # Extract current configuration values
                    current_config = {
                        "max_output_size": None,
                        "reranker_threshold": 2.5,  # default
                        "model_name": "gpt-4.1",    # default
                    }
                    
                    # Try to get max_output_size from request_limits
                    if hasattr(current_agent, 'request_limits') and current_agent.request_limits:
                        if hasattr(current_agent.request_limits, 'max_output_size'):
                            current_config["max_output_size"] = current_agent.request_limits.max_output_size
                    
                    # Get reranker threshold from target indexes
                    if hasattr(current_agent, 'target_indexes') and current_agent.target_indexes:
                        for target_idx in current_agent.target_indexes:
                            if hasattr(target_idx, 'default_reranker_threshold'):
                                current_config["reranker_threshold"] = target_idx.default_reranker_threshold
                                break
                    
                    # Get model name from models
                    if hasattr(current_agent, 'models') and current_agent.models:
                        for model in current_agent.models:
                            if hasattr(model, 'azure_open_ai_parameters') and hasattr(model.azure_open_ai_parameters, 'model_name'):
                                current_config["model_name"] = model.azure_open_ai_parameters.model_name
                                break
                                
                except Exception as e:
                    st.info(f"Agent `{agent_name}` doesn't exist yet. You can create it below.")
                    agent_exists = False
            
            with col2:
                status_icon = "✅" if agent_exists else "❌"
                st.markdown(f"**Status:** {status_icon} {'Exists' if agent_exists else 'Not Found'}")
            
            # Configuration form
            with st.form("agent_config_form"):
                st.markdown("#### Agent Parameters")
                
                # Max Output Size
                current_max_output = current_config.get("max_output_size", 16000)
                if current_max_output is None:
                    current_max_output = 16000  # Default if not set
                    
                new_max_output_size = st.number_input(
                    "Max Output Size (characters)",
                    min_value=1000,
                    max_value=100000,
                    value=current_max_output,
                    step=1000,
                    help="Maximum number of characters the agent can return in a single response"
                )
                
                # Reranker Threshold
                new_reranker_threshold = st.number_input(
                    "Reranker Threshold",
                    min_value=0.0,
                    max_value=5.0,
                    value=float(current_config.get("reranker_threshold", 2.5)),
                    step=0.1,
                    help="Threshold for semantic reranking (lower = more results, higher = more selective)"
                )
                
                # Model Selection
                model_options = ["gpt-4.1", "gpt-4o", "gpt-3.5-turbo"]
                current_model = current_config.get("model_name", "gpt-4.1")
                try:
                    model_index = model_options.index(current_model)
                except ValueError:
                    model_index = 0
                    
                new_model = st.selectbox(
                    "Model",
                    options=model_options,
                    index=model_index,
                    help="OpenAI model to use for agent responses"
                )
                
                # Form buttons
                col1, col2 = st.columns(2)
                with col1:
                    create_button = st.form_submit_button("🆕 Create Agent" if not agent_exists else "🔄 Update Agent")
                with col2:
                    if agent_exists:
                        delete_agent_button = st.form_submit_button("🗑️ Delete Agent")
                    else:
                        delete_agent_button = False
                
                # Handle form submission
                if create_button:
                    try:
                        # Get Azure OpenAI configuration
                        azure_openai_endpoint = env("AZURE_OPENAI_ENDPOINT_41")
                        openai_api_key = os.getenv("AZURE_OPENAI_KEY_41") or os.getenv("AZURE_OPENAI_KEY") or ""
                        
                        # Select deployment based on model
                        deployment_map = {
                            "gpt-4.1": "AZURE_OPENAI_DEPLOYMENT_41",
                            "gpt-4o": "AZURE_OPENAI_DEPLOYMENT_4o", 
                            "gpt-3.5-turbo": "AZURE_OPENAI_DEPLOYMENT"
                        }
                        deployment_env = deployment_map.get(new_model, "AZURE_OPENAI_DEPLOYMENT_41")
                        deployment_name = os.getenv(deployment_env, "gpt-4.1")
                        
                        # Create/update the agent
                        agent = KnowledgeAgent(
                            name = agent_name,
                            models = [
                                KnowledgeAgentAzureOpenAIModel(
                                    azure_open_ai_parameters = AzureOpenAIVectorizerParameters(
                                        resource_url    = azure_openai_endpoint,
                                        deployment_name = deployment_name,
                                        model_name      = new_model,
                                        api_key         = openai_api_key,
                                    )
                                )
                            ],
                            target_indexes = [
                                KnowledgeAgentTargetIndex(
                                    index_name=st.session_state.selected_index, 
                                    default_reranker_threshold=new_reranker_threshold
                                )
                            ],
                            request_limits = KnowledgeAgentRequestLimits(
                                max_output_size = int(new_max_output_size)
                            ),
                        )
                        
                        root_index_client.create_or_update_agent(agent)
                        
                        action = "Updated" if agent_exists else "Created"
                        st.success(f"✅ {action} agent `{agent_name}` successfully!")
                        st.info(f"📋 Configuration: Max Output: {new_max_output_size}, Reranker: {new_reranker_threshold}, Model: {new_model}")
                        
                        # Force a rerun to refresh the current config display
                        if hasattr(st, "rerun"):
                            st.rerun()
                        else:
                            st.experimental_rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Failed to create/update agent: {str(e)}")
                        st.code(f"Error details: {e}")
                
                if delete_agent_button and agent_exists:
                    try:
                        root_index_client.delete_agent(agent_name)
                        st.success(f"✅ Deleted agent `{agent_name}` successfully!")
                        
                        # Force a rerun to refresh the display
                        if hasattr(st, "rerun"):
                            st.rerun()
                        else:
                            st.experimental_rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Failed to delete agent: {str(e)}")
            
            # Show current configuration summary
            if agent_exists:
                with st.expander("📋 Current Agent Configuration", expanded=False):
                    config_data = {
                        "Parameter": ["Max Output Size", "Reranker Threshold", "Model", "Target Index"],
                        "Value": [
                            f"{current_config.get('max_output_size', 'Not Set')} characters",
                            f"{current_config.get('reranker_threshold', 'Default')}",
                            current_config.get('model_name', 'Unknown'),
                            st.session_state.selected_index
                        ]
                    }
                    config_df = pd.DataFrame(config_data)
                    st.dataframe(config_df, use_container_width=True, hide_index=True)
        
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
                            # IndexAction object doesn't have .get() method, need to access attributes
                            if hasattr(action, 'id'):
                                failed_ids.append(action.id)
                            elif hasattr(action, 'document') and hasattr(action.document, 'get'):
                                failed_ids.append(action.document.get("id", "?"))
                            else:
                                failed_ids.append("?")
                        except Exception as exc:
                            logging.error("⚠️  on_error callback failed to record ID: %s", exc)
                            failed_ids.append("?")

                    sender = SearchIndexingBufferedSender(
                        endpoint=env("AZURE_SEARCH_ENDPOINT"),
                        index_name=st.session_state.selected_index,
                        credential=get_search_credential(),
                        batch_size=100,
                        auto_flush_interval=5,
                        on_error=_on_error,
                    )

                    embed_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
                    total_pages = 0
                    processed_files = []
                    skipped_files = []
                    
                    for pf in uploaded:
                        ext = os.path.splitext(pf.name)[-1].lower()
                        docs = []

                        # --- Use DocumentChunker for ALL files including PDFs for multimodal support ---
                        error_message = None
                        
                        # DEBUG: Check file size at the very beginning
                        original_file_size = len(bytes(pf.getbuffer()))
                        logging.info(f"[Streamlit Upload][{pf.name}] ORIGINAL FILE SIZE: {original_file_size:,} bytes")
                        
                        # Also check the Streamlit file object properties
                        logging.info(f"[Streamlit Upload][{pf.name}] File object type: {type(pf)}")
                        logging.info(f"[Streamlit Upload][{pf.name}] File object size property: {getattr(pf, 'size', 'N/A')}")
                        
                        try:
                            docs = _chunk_to_docs(
                                pf.name,
                                bytes(pf.getbuffer()),
                                "",          # no public URL for local upload
                                oai_client,
                                embed_deploy,
                            )
                            
                            # Check if file was processed successfully
                            if not docs:
                                # Check if the original chunker returned any useful error information
                                multimodal_enabled = os.getenv("MULTIMODAL", "false").lower() in ["true", "1", "yes"] and ext in ('.pdf', '.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.docx', '.pptx')
                                dc = DocumentChunker(multimodal=multimodal_enabled, openai_client=oai_client if multimodal_enabled else None)
                                data = {
                                    "fileName": pf.name,
                                    "documentBytes": base64.b64encode(bytes(pf.getbuffer())).decode("utf-8"),
                                    "documentUrl": "",
                                }
                                chunks, errors, warnings = dc.chunk_documents(data)
                                
                                if errors:
                                    error_message = f"Processing failed: {errors[0] if errors else 'Unknown error'}"
                                else:
                                    error_message = "No content could be extracted from this file"
                                    
                        except Exception as docerr:
                            error_message = str(docerr)
                            logging.error("DocumentChunker failed for %s: %s", pf.name, docerr)
                            
                            # Try fallback for PDFs only
                            if ext == ".pdf":
                                try:
                                    docs = pdf_to_documents(pf, oai_client, embed_deploy)
                                    error_message = None  # Clear error if fallback succeeded
                                    logging.info("Fallback to simple PDF processing for %s", pf.name)
                                except Exception as pdf_err:
                                    logging.error("PDF fallback also failed for %s: %s", pf.name, pdf_err)
                                    error_message = f"PDF processing failed: {str(docerr)[:200]}... (Fallback also failed: {str(pdf_err)[:100]}...)"
                            else:
                                # For non-PDF files, keep the original error
                                error_message = f"Failed to process {ext} file: {str(docerr)[:300]}..."
                        
                        # Handle errors - show in UI and track for summary
                        if error_message or not docs:
                            # Enhanced error message based on common issues
                            file_size = len(bytes(pf.getbuffer()))
                            enhanced_error = error_message or "Unknown processing error"
                            
                            # Provide specific guidance for common issues
                            guidance = ""
                            if file_size < 1000:
                                guidance = """
                                **This file is very small ({} bytes) which suggests it may be:**
                                - Corrupted or incomplete
                                - An empty file
                                - A file that failed to upload properly
                                
                                **Try:**
                                - Re-downloading the original file
                                - Checking if it opens properly in its native application
                                - Using a different version of the file
                                """.format(file_size)
                            elif "Document Intelligence" in enhanced_error and "UnsupportedContent" in enhanced_error:
                                guidance = """
                                **Document Intelligence couldn't process this file because:**
                                - The file may be corrupted or have invalid internal structure
                                - It might be password-protected
                                - The format may not be fully compatible

                                **Try:**
                                - Opening and re-saving the file in its native application
                                - Converting to a different format (e.g., PDF → DOCX)
                                - Ensuring the file isn't password-protected
                                """
                            elif ext == ".pdf":
                                guidance = """
                                **PDF processing failed. Common causes:**
                                - Corrupted PDF file
                                - Password-protected PDF
                                - Non-standard PDF encoding
                                - Scanned PDF without OCR text layer
                                
                                **Try:**
                                - Re-saving the PDF from its source application
                                - Using a PDF repair tool
                                - Converting to Word format first
                                """
                            
                            st.error(f"""
                            **❌ Processing Failed: {pf.name}**
                            
                            {enhanced_error}
                            
                            **File details:**
                            - Size: {file_size} bytes  
                            - Type: {ext}
                            
                            {guidance}
                            
                            **What you can try:**
                            - Check if the file opens correctly in its native application
                            - Try re-saving or converting the file to a different format
                            - For PDFs: ensure they're not password-protected
                            - For images: ensure they're in a standard format
                            """)
                            
                            skipped_files.append({
                                "name": pf.name,
                                "size": len(bytes(pf.getbuffer())),
                                "reason": error_message or "Processing failed"
                            })
                            continue

                        if not docs:
                            skipped_files.append({
                                "name": pf.name,
                                "size": len(bytes(pf.getbuffer())),
                                "reason": "Corrupted or unsupported file"
                            })
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
                                # Check if this was a fallback from multimodal/Document Intelligence
                                if ext in ('.pdf', '.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.docx', '.pptx'):
                                    processing_info.append("⚠️ **Note:** Fell back to basic text extraction (Document Intelligence unavailable or file unsupported)")
                            else:
                                # Unknown method - show basic info
                                processing_info.append(f"📄 **{pf.name}** ({doc_type})")
                                processing_info.append(f"🔧 **Processing Tool:** {method}")
                        
                        # Add multimodal status info
                        multimodal_docs = [doc for doc in docs if doc.get("isMultimodal", False)]
                        if multimodal_docs:
                            processing_info.append(f"🎨 **Multimodal Content:** {len(multimodal_docs)} chunks contain images/figures")
                        elif ext in ('.pdf', '.png', '.jpeg', '.jpg', '.bmp', '.tiff') and os.getenv("MULTIMODAL", "false").lower() in ["true", "1", "yes"]:
                            processing_info.append("ℹ️ **Multimodal Status:** No images detected or multimodal processing failed")
                        
                        if processing_info:
                            with st.expander(f"ℹ️ Processing Details for {pf.name}", expanded=False):
                                for info in processing_info:
                                    st.markdown(info)
                                st.markdown(f"📊 **Chunks Created:** {len(docs)}")
                        
                        sender.upload_documents(documents=docs)
                        total_pages += len(docs)
                        processed_files.append({
                            "name": pf.name,
                            "chunks": len(docs),
                            "method": docs[0].get("extraction_method", "unknown") if docs else "unknown"
                        })

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
                    
                    # Show processing summary
                    if processed_files or skipped_files:
                        st.markdown("### 📊 Processing Summary")
                        
                        if processed_files:
                            st.markdown(f"**✅ Successfully Processed ({len(processed_files)} files):**")
                            for file_info in processed_files:
                                st.markdown(f"   • {file_info['name']} - {file_info['chunks']} chunks ({file_info['method']})")
                        
                        if skipped_files:
                            st.markdown(f"**⚠️ Skipped Files ({len(skipped_files)} files):**")
                            for file_info in skipped_files:
                                st.markdown(f"   • {file_info['name']} ({file_info['size']} bytes) - {file_info['reason']}")
                            st.info("💡 **Tip:** Skipped files are usually corrupted, too small, or in an unsupported format.")

    # ─────────────────── Tab 4 – SharePoint Index ────────────────────────
    with tab_sharepoint:
        health_block()
        st.header("📁 SharePoint Index Management")
        
        try:
            from sharepoint_index_manager import SharePointIndexManager
            sp_manager = SharePointIndexManager()
            
            # Check SharePoint authentication
            auth_status = sp_manager.get_sharepoint_auth_status()
            
            if not auth_status['authenticated']:
                st.error(f"❌ SharePoint Authentication Failed: {auth_status['error']}")
                st.markdown("""
                **To fix this, please ensure:**
                1. Your `.env` file contains the required SharePoint credentials:
                   - `SHAREPOINT_TENANT_ID`
                   - `SHAREPOINT_CLIENT_ID`
                   - `SHAREPOINT_CLIENT_SECRET`
                2. The SharePoint app has proper permissions
                3. The credentials are valid and not expired
                """)
                st.stop()
            
            st.success("✅ SharePoint Authentication Successful")
            st.caption(f"Tenant ID: {auth_status['tenant_id']}")
            
            # SharePoint Configuration
            st.subheader("🔧 SharePoint Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                site_domain = st.text_input(
                    "Site Domain", 
                    value=os.getenv("SHAREPOINT_SITE_DOMAIN", ""),
                    placeholder="e.g., contoso.sharepoint.com"
                )
                site_name = st.text_input(
                    "Site Name", 
                    value=os.getenv("SHAREPOINT_SITE_NAME", ""),
                    placeholder="e.g., MyTeamSite"
                )
            
            with col2:
                drive_name = st.text_input(
                    "Drive/Library Name", 
                    value=os.getenv("SHAREPOINT_DRIVE_NAME", ""),
                    placeholder="e.g., Documents (leave blank for default)"
                )
                file_types = st.text_input(
                    "File Types (comma-separated)",
                    value="pdf,docx,pptx,xlsx",
                    placeholder="pdf,docx,pptx,xlsx"
                )
            
            # Target Index Selection (SharePoint-specific)
            st.subheader("🎯 Target Index Selection")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Get available indexes for SharePoint
                if "sp_available_indexes" not in st.session_state:
                    st.session_state.sp_available_indexes = []
                
                try:
                    # Get available indexes from session state (populated in main initialization)
                    indexes_list = st.session_state.get('available_indexes', [])
                    st.session_state.sp_available_indexes = indexes_list
                    
                    # Index selection dropdown
                    index_options = ["Select an index..."] + indexes_list
                    
                    # Get current selection (prioritize SharePoint-specific selection over global)
                    current_sp_index = getattr(st.session_state, 'sp_target_index', None)
                    if not current_sp_index:
                        current_sp_index = st.session_state.get('selected_index', None)
                    
                    # Find current index in options
                    current_index = 0
                    if current_sp_index and current_sp_index in indexes_list:
                        current_index = indexes_list.index(current_sp_index) + 1
                    
                    selected_index_display = st.selectbox(
                        "Select Target Index for SharePoint",
                        options=index_options,
                        index=current_index,
                        help="Choose the search index where SharePoint documents will be stored"
                    )
                    
                    # Update SharePoint-specific index selection
                    if selected_index_display != "Select an index...":
                        st.session_state.sp_target_index = selected_index_display
                        # Also update global selection if not set
                        if not st.session_state.selected_index:
                            st.session_state.selected_index = selected_index_display
                    else:
                        st.session_state.sp_target_index = None
                    
                except Exception as e:
                    st.error(f"Error loading indexes: {str(e)}")
                    st.session_state.sp_target_index = None
            
            with col2:
                # Index status and actions
                if hasattr(st.session_state, 'sp_target_index') and st.session_state.sp_target_index:
                    st.success(f"✅ Target Index")
                    st.caption(f"**{st.session_state.sp_target_index}**")
                    
                    # Quick action to sync with global selection
                    if st.button("🔄 Set as Global Index", help="Make this the global selected index for all tabs"):
                        st.session_state.selected_index = st.session_state.sp_target_index
                        st.success(f"Global index updated to: {st.session_state.sp_target_index}")
                        st.rerun()
                else:
                    st.warning("⚠️ No Index Selected")
                    if st.session_state.selected_index:
                        st.caption(f"Global: {st.session_state.selected_index}")
                        if st.button("📥 Use Global Index", help="Use the globally selected index for SharePoint"):
                            st.session_state.sp_target_index = st.session_state.selected_index
                            st.rerun()
            
            if not site_domain:
                st.warning("Please enter Site Domain to continue.")
                st.stop()
            
            # Note: site_name can be empty for root site
            
            # Get available drives
            st.subheader("📂 Available Document Libraries")
            drives = sp_manager.get_sharepoint_drives(site_domain, site_name)
            
            if not drives:
                st.error("No drives/libraries found. Please check your site configuration.")
                st.stop()
            
            # Display drives
            drive_options = [""] + [f"{drive['name']} ({drive['driveType']})" for drive in drives]
            selected_drive_display = st.selectbox("Select Document Library", drive_options)
            
            if selected_drive_display:
                selected_drive = selected_drive_display.split(" (")[0]
            else:
                selected_drive = drive_name
            
            # Folder Tree Selection
            if selected_drive:
                st.subheader("📁 Select Folders to Index")
                
                # Performance controls
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown("*Click 📁 to expand folders, ☑️ to select for indexing*")
                with col2:
                    if st.button("🔄 Refresh Cache", help="Clear cache and reload folder structure"):
                        sp_manager.clear_cache()
                        # Clear session state
                        for key in list(st.session_state.keys()):
                            if key.startswith("sp_folders_loaded_") or key.startswith("sp_expanded_"):
                                del st.session_state[key]
                        st.rerun()
                with col3:
                    cache_stats = sp_manager.get_cache_stats()
                    st.caption(f"Cache: {cache_stats['cached_folders']} folders")
                
                # Initialize selected folders in session state
                if "sp_selected_folders" not in st.session_state:
                    st.session_state.sp_selected_folders = []
                
                # Add performance tips
                with st.expander("💡 Performance Tips", expanded=False):
                    st.markdown("""
                    - **Lazy Loading**: Folders load only when expanded to improve speed
                    - **Caching**: Folder structures are cached to reduce API calls
                    - **Depth Limit**: Deep folder structures are limited to prevent slowdown
                    - **Click 📁/📂**: Click folder icons to expand/collapse subfolders
                    - **Batch Selection**: Select multiple folders for efficient indexing
                    - **Refresh Cache**: Use the refresh button if folders don't appear up-to-date
                    """)
                
                # Render folder tree with loading indicator
                with st.container():
                    st.markdown("**Available Folders:**")
                    
                    # Show loading spinner for initial load
                    if f"sp_folders_loaded_{selected_drive}" not in st.session_state:
                        with st.spinner("Loading folder structure..."):
                            # Preload for better performance
                            sp_manager.preload_folder_structure(site_domain, site_name, selected_drive, max_depth=2)
                            
                            updated_selection = sp_manager.render_folder_tree(
                                site_domain, 
                                site_name, 
                                selected_drive,
                                st.session_state.sp_selected_folders
                            )
                            st.session_state.sp_selected_folders = updated_selection
                            st.session_state[f"sp_folders_loaded_{selected_drive}"] = True
                    else:
                        # Subsequent renders without spinner
                        updated_selection = sp_manager.render_folder_tree(
                            site_domain, 
                            site_name, 
                            selected_drive,
                            st.session_state.sp_selected_folders
                        )
                        st.session_state.sp_selected_folders = updated_selection
                
                # Show selected folders summary
                if st.session_state.sp_selected_folders:
                    st.subheader("✅ Selected Folders")
                    
                    # Get folder info with caching
                    try:
                        folder_info = sp_manager.get_selected_folder_info(st.session_state.sp_selected_folders)
                        
                        if folder_info:
                            # Display in a more compact format
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                for folder in folder_info:
                                    st.write(f"📁 {folder['display_name']}")
                            with col2:
                                st.metric("Selected", len(folder_info))
                        else:
                            st.info("No folders selected for indexing")
                    except Exception as e:
                        st.error(f"Error loading selected folders: {str(e)}")
                        # Clear selection on error
                        st.session_state.sp_selected_folders = []
                    
                    # Index Selection and Scheduler
                    # Determine target index (SharePoint-specific or global)
                    target_index = getattr(st.session_state, 'sp_target_index', None) or st.session_state.selected_index
                    
                    if not target_index:
                        st.warning("⚠️ Please select a target index above to continue with indexing operations.")
                        st.info("💡 You can select an index specifically for SharePoint operations, or use the global index from the 'Manage Index' tab.")
                    else:
                        st.subheader("🚀 Indexing Operations")
                        
                        # Show which index will be used
                        index_source = "SharePoint-specific" if hasattr(st.session_state, 'sp_target_index') and st.session_state.sp_target_index else "Global"
                        st.info(f"Will index into: **{target_index}** ({index_source} selection)")
                        
                        # Parse file types
                        file_type_list = [ft.strip() for ft in file_types.split(",") if ft.strip()] if file_types else None
                        
                        # Create tabs for Manual and Scheduled operations
                        manual_tab, scheduler_tab, reports_tab = st.tabs(["Manual Index", "Scheduler", "Reports"])
                        
                        with manual_tab:
                            st.markdown("### � Manual Indexing")
                            
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.markdown("Run indexing operation immediately on selected folders")
                            with col2:
                                parallel_files = st.select_slider(
                                    "Parallel Files",
                                    options=[1, 2, 3, 4, 5],
                                    value=3,
                                    help="Number of files to process in parallel (1-5)"
                                )
                            
                            if st.button("🔗 Run Index Now", type="primary"):
                                with st.spinner("Indexing SharePoint folders..."):
                                    try:
                                        # Initialize scheduler for parallel processing
                                        from sharepoint_scheduler import SharePointScheduler
                                        scheduler = SharePointScheduler()
                                        
                                        # Run indexing with parallel processing
                                        result = scheduler.run_now(
                                            selected_folders=st.session_state.sp_selected_folders,
                                            config={
                                                'index_name': target_index,
                                                'file_types': file_type_list,
                                                'max_parallel_files': parallel_files
                                            }
                                        )
                                        
                                        if result['success']:
                                            st.success(f"✅ {result['message']}")
                                            if 'files_successful' in result:
                                                col1, col2, col3 = st.columns(3)
                                                with col1:
                                                    st.metric("Files Processed", result['files_successful'])
                                                with col2:
                                                    st.metric("Files Failed", result['files_failed'])
                                                with col3:
                                                    st.metric("Chunks Created", result['chunks_created'])
                                        else:
                                            st.error(f"❌ {result['message']}")
                                            
                                    except Exception as e:
                                        st.error(f"❌ Manual indexing failed: {str(e)}")
                        
                        with scheduler_tab:
                            st.markdown("### ⏰ Scheduled Indexing")
                            
                            # Initialize scheduler (using singleton pattern)
                            try:
                                from sharepoint_scheduler import SharePointScheduler
                                scheduler = SharePointScheduler.get_instance()
                                
                                # Scheduler controls
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.markdown("**Schedule Configuration**")
                                    
                                    # Interval selection (1 min to 24 hours = 1440 minutes)
                                    interval_minutes = st.select_slider(
                                        "Indexing Interval",
                                        options=[1, 5, 10, 15, 30, 60, 120, 240, 480, 720, 1440],
                                        value=5,
                                        format_func=lambda x: f"{x} min" if x < 60 else f"{x//60} hour{'s' if x//60 > 1 else ''}",
                                        help="How often to run automatic indexing"
                                    )
                                    
                                    parallel_files_scheduler = st.select_slider(
                                        "Parallel Files (Scheduler)",
                                        options=[1, 2, 3, 4, 5],
                                        value=3,
                                        help="Number of files to process in parallel during scheduled runs"
                                    )
                                    
                                    # Auto-purge configuration
                                    auto_purge_enabled = st.checkbox(
                                        "🗑️ Auto-purge after indexing",
                                        value=True,
                                        help="Automatically run purge to remove orphaned files after each indexing job"
                                    )
                                
                                with col2:
                                    st.markdown("**Status**")
                                    
                                    # Always get fresh status from scheduler
                                    status = scheduler.get_status()
                                    st.session_state.scheduler_status = status
                                    
                                    if status['is_running']:
                                        st.success("🟢 Running")
                                        if status['next_run']:
                                            next_run = datetime.fromisoformat(status['next_run'])
                                            now = datetime.now()
                                            time_until = (next_run - now).total_seconds()
                                            if time_until > 0:
                                                minutes = int(time_until // 60)
                                                seconds = int(time_until % 60)
                                                st.caption(f"Next: {next_run.strftime('%H:%M:%S')} (in {minutes}m {seconds}s)")
                                            else:
                                                st.caption(f"Next: {next_run.strftime('%H:%M:%S')} (overdue)")
                                    else:
                                        st.info("🔴 Stopped")
                                    
                                    st.metric("Interval", f"{status['interval_minutes']} min")
                                    st.metric("Selected Folders", status['selected_folders_count'])
                                    st.metric("Last Job", status.get('last_job_status', 'No jobs yet'))
                                    
                                    # Show recent job history
                                    if status.get('recent_reports'):
                                        with st.expander("📈 Recent Jobs", expanded=False):
                                            for report in status['recent_reports']:
                                                report_status = report.get('status', 'unknown')
                                                report_type = report.get('type', 'unknown')
                                                start_time = report.get('start_time', '')
                                                if start_time:
                                                    try:
                                                        dt = datetime.fromisoformat(start_time)
                                                        time_str = dt.strftime('%H:%M:%S')
                                                    except:
                                                        time_str = start_time
                                                else:
                                                    time_str = 'Unknown'
                                                
                                                status_icon = "✅" if report_status == "completed" else "❌" if report_status == "failed" else "🔄"
                                                st.caption(f"{status_icon} {report_type.title()} at {time_str}")
                                
                                # Control buttons
                                st.markdown("**Controls**")
                                button_col1, button_col2 = st.columns(2)
                                
                                with button_col1:
                                    if st.button("▶️ Start Scheduler", disabled=status['is_running']):
                                        config = {
                                            'index_name': target_index,
                                            'file_types': file_type_list,
                                            'max_parallel_files': parallel_files_scheduler,
                                            'auto_purge_enabled': auto_purge_enabled
                                        }
                                        scheduler.set_interval(interval_minutes)
                                        result = scheduler.start_scheduler(st.session_state.sp_selected_folders, config)
                                        
                                        if result['success']:
                                            st.success(result['message'])
                                        else:
                                            st.error(result['message'])
                                        
                                        time.sleep(0.5)  # Brief pause for state to update
                                        st.rerun()
                                
                                with button_col2:
                                    if st.button("⏹️ Stop Scheduler", disabled=not status['is_running']):
                                        result = scheduler.stop_scheduler()
                                        
                                        if result['success']:
                                            st.success(result['message'])
                                        else:
                                            st.error(result['message'])
                                        
                                        time.sleep(0.5)  # Brief pause for state to update
                                        st.rerun()
                                
                                # Note about manual indexing
                                st.info("� **Tip**: Use the 'Manual Indexing' section in the SharePoint tab to run indexing immediately.")
                                
                                # Auto-refresh every 30 seconds (status is now always fresh)
                                st.markdown("*Status updates automatically every page refresh*")
                                
                                # Performance info
                                with st.expander("📊 Performance Features", expanded=False):
                                    st.markdown("""
                                    **Parallel Processing:**
                                    - Process up to 5 files simultaneously
                                    - Configurable per operation
                                    - Reduces overall indexing time
                                    
                                    **Intelligent Scheduling:**
                                    - Flexible intervals (1 min to 24 hours)
                                    - Background processing
                                    - Automatic error handling and retry
                                    
                                    **Resource Management:**
                                    - Memory-efficient processing
                                    - Graceful shutdown capability
                                    - Thread safety and cleanup
                                    """)
                                
                            except ImportError:
                                st.error("❌ Scheduler module not available")
                            except Exception as e:
                                st.error(f"❌ Scheduler error: {str(e)}")
                        
                        with reports_tab:
                            st.markdown("### 📊 Indexing Reports")
                            
                            try:
                                from sharepoint_scheduler import SharePointScheduler
                                scheduler = SharePointScheduler()
                                
                                # Report management buttons
                                report_mgmt_col1, report_mgmt_col2, report_mgmt_col3 = st.columns([2, 1, 1])
                                
                                with report_mgmt_col1:
                                    st.markdown("**Report Management**")
                                
                                with report_mgmt_col2:
                                    if st.button("🔄 Refresh Reports"):
                                        # Use session state to trigger reports refresh without full page reload
                                        if "reports_refresh_counter" not in st.session_state:
                                            st.session_state.reports_refresh_counter = 0
                                        st.session_state.reports_refresh_counter += 1
                                        st.success("Reports refreshed!", icon="✅")
                                
                                with report_mgmt_col3:
                                    # Initialize delete confirmation state
                                    if "delete_all_reports_confirm" not in st.session_state:
                                        st.session_state.delete_all_reports_confirm = False
                                    
                                    if not st.session_state.delete_all_reports_confirm:
                                        if st.button("🗑️ Delete All Reports"):
                                            st.session_state.delete_all_reports_confirm = True
                                    else:
                                        col_a, col_b = st.columns(2)
                                        with col_a:
                                            if st.button("✅ Confirm", type="primary"):
                                                result = scheduler.delete_all_reports()
                                                if result["success"]:
                                                    st.success(f"✅ {result['message']}")
                                                    st.balloons()
                                                    st.session_state.delete_all_reports_confirm = False
                                                    # Invalidate reports cache
                                                    st.session_state.reports_data = None
                                                    time.sleep(1)
                                                    # Increment refresh counter to trigger reload
                                                    if "reports_refresh_counter" not in st.session_state:
                                                        st.session_state.reports_refresh_counter = 0
                                                    st.session_state.reports_refresh_counter += 1
                                                else:
                                                    st.error(f"❌ {result['message']}")
                                                    st.session_state.delete_all_reports_confirm = False
                                        with col_b:
                                            if st.button("❌ Cancel"):
                                                st.session_state.delete_all_reports_confirm = False
                                
                                st.divider()
                                
                                # Initialize reports refresh system
                                if "reports_data" not in st.session_state:
                                    st.session_state.reports_data = None
                                    st.session_state.reports_last_refresh = 0
                                
                                # Check if we need to refresh reports data
                                current_refresh_counter = st.session_state.get("reports_refresh_counter", 0)
                                if (st.session_state.reports_data is None or 
                                    current_refresh_counter > st.session_state.reports_last_refresh):
                                    # Load fresh reports data
                                    st.session_state.reports_data = scheduler.get_reports()
                                    st.session_state.reports_last_refresh = current_refresh_counter
                                
                                # Use cached reports data
                                reports = st.session_state.reports_data
                                
                                if not reports:
                                    st.info("No indexing reports available yet. Run some indexing operations to see reports here.")
                                else:
                                    # Reports summary
                                    col1, col2, col3, col4 = st.columns(4)
                                    
                                    successful_reports = [r for r in reports if r.get('status') == 'completed']
                                    failed_reports = [r for r in reports if r.get('status') == 'error']
                                    running_reports = [r for r in reports if r.get('status') == 'running']
                                    
                                    with col1:
                                        st.metric("Total Reports", len(reports))
                                    with col2:
                                        st.metric("Successful", len(successful_reports))
                                    with col3:
                                        st.metric("Failed", len(failed_reports))
                                    with col4:
                                        st.metric("Running", len(running_reports))
                                    
                                    # Reports list
                                    st.markdown("**Report History**")
                                    
                                    for report in reports[:10]:  # Show last 10 reports
                                        with st.container():
                                            report_col1, report_col2, report_col3 = st.columns([3, 1, 1])
                                            
                                            with report_col1:
                                                start_time = datetime.fromisoformat(report['start_time'])
                                                status_icon = {
                                                    'completed': '✅',
                                                    'error': '❌',
                                                    'running': '🔄'
                                                }.get(report.get('status', 'unknown'), '❓')
                                                
                                                st.write(f"{status_icon} {start_time.strftime('%Y-%m-%d %H:%M:%S')} - {report.get('type', 'unknown').title()}")
                                                if report.get('status') == 'completed':
                                                    caption_text = f"Files: {report.get('files_successful', 0)}/{report.get('files_processed', 0)} | Chunks: {report.get('chunks_created', 0)}"
                                                    
                                                    # Add purge info if available
                                                    if report.get('purge_results'):
                                                        purge_deleted = report['purge_results'].get('documents_deleted', 0)
                                                        if purge_deleted > 0:
                                                            caption_text += f" | Purged: {purge_deleted} docs"
                                                        else:
                                                            caption_text += " | Purged: none"
                                                    elif report.get('auto_purge_enabled'):
                                                        caption_text += " | Auto-purge: enabled"
                                                    
                                                    st.caption(caption_text)
                                            
                                            with report_col2:
                                                # View report details
                                                if st.button("👁️ View", key=f"view_{report['id']}"):
                                                    st.session_state[f"show_report_{report['id']}"] = True
                                            
                                            with report_col3:
                                                # Delete report
                                                if st.button("🗑️ Delete", key=f"delete_{report['id']}"):
                                                    result = scheduler.delete_report(report['id'])
                                                    if result['success']:
                                                        st.success(f"Report deleted: {report['id']}")
                                                        # Invalidate reports cache
                                                        st.session_state.reports_data = None
                                                        # Increment refresh counter to trigger reload
                                                        if "reports_refresh_counter" not in st.session_state:
                                                            st.session_state.reports_refresh_counter = 0
                                                        st.session_state.reports_refresh_counter += 1
                                                    else:
                                                        st.error(result['message'])
                                        
                                        # Show report details if requested
                                        if st.session_state.get(f"show_report_{report['id']}", False):
                                            with st.expander(f"📋 Report Details - {report['id']}", expanded=True):
                                                
                                                # Close button
                                                if st.button("❌ Close", key=f"close_{report['id']}"):
                                                    st.session_state[f"show_report_{report['id']}"] = False
                                                    st.rerun()
                                                
                                                # Report details
                                                detail_col1, detail_col2 = st.columns(2)
                                                
                                                with detail_col1:
                                                    st.markdown("**General Info**")
                                                    st.write(f"**Report ID:** {report['id']}")
                                                    st.write(f"**Type:** {report.get('type', 'unknown').title()}")
                                                    st.write(f"**Status:** {report.get('status', 'unknown').title()}")
                                                    st.write(f"**Start Time:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                                    
                                                    if report.get('end_time'):
                                                        end_time = datetime.fromisoformat(report['end_time'])
                                                        duration = (end_time - start_time).total_seconds()
                                                        st.write(f"**Duration:** {duration:.1f} seconds")
                                                
                                                with detail_col2:
                                                    st.markdown("**Processing Summary**")
                                                    st.write(f"**Files Processed:** {report.get('files_processed', 0)}")
                                                    st.write(f"**Files Successful:** {report.get('files_successful', 0)}")
                                                    st.write(f"**Files Failed:** {report.get('files_failed', 0)}")
                                                    st.write(f"**Chunks Created:** {report.get('chunks_created', 0)}")
                                                
                                                # Folders
                                                if report.get('folders'):
                                                    st.markdown("**Folders Processed**")
                                                    for folder in report['folders']:
                                                        st.write(f"📁 {folder}")
                                                
                                                # Processing details
                                                if report.get('processing_details'):
                                                    st.markdown("**File Processing Details**")
                                                    for detail in report['processing_details']:
                                                        if detail.get('status') == 'success':
                                                            st.write(f"✅ {detail['file']} - {detail.get('chunks', 0)} chunks ({detail.get('method', 'unknown')})")
                                                        else:
                                                            st.write(f"❌ {detail['file']} - {detail.get('error', 'Unknown error')}")
                                                
                                                # Errors
                                                if report.get('errors'):
                                                    st.markdown("**Errors**")
                                                    for error in report['errors']:
                                                        st.error(error)
                                                
                                                # Auto-purge results
                                                if report.get('purge_results'):
                                                    st.markdown("**🗑️ Auto-Purge Results**")
                                                    purge_results = report['purge_results']
                                                    
                                                    purge_col1, purge_col2 = st.columns(2)
                                                    
                                                    with purge_col1:
                                                        st.write(f"**Purge Success:** {'✅ Yes' if purge_results.get('success') else '❌ No'}")
                                                        st.write(f"**Documents Checked:** {purge_results.get('documents_checked', 0)}")
                                                        st.write(f"**Files Checked:** {purge_results.get('files_checked', 0)}")
                                                    
                                                    with purge_col2:
                                                        st.write(f"**Files Not Found:** {purge_results.get('files_not_found', 0)}")
                                                        st.write(f"**Documents Deleted:** {purge_results.get('documents_deleted', 0)}")
                                                        st.write(f"**Purge Message:** {purge_results.get('message', 'No message')}")
                                                    
                                                    if purge_results.get('errors'):
                                                        st.markdown("**Purge Errors**")
                                                        for error in purge_results['errors']:
                                                            st.error(f"Purge: {error}")
                                                elif report.get('auto_purge_enabled'):
                                                    st.info("🗑️ Auto-purge was enabled but no purge results available (likely due to indexing failure)")
                                                else:
                                                    st.info("🗑️ Auto-purge was disabled for this operation")
                                        
                                        st.divider()
                            
                            except ImportError:
                                st.error("❌ Reports module not available")
                            except Exception as e:
                                st.error(f"❌ Reports error: {str(e)}")
                        
                        # Add Purge Deleted Files section
                        st.divider()
                        st.subheader("🗑️ Purge Deleted Files")
                        
                        with st.expander("💡 About File Deletion Purging", expanded=False):
                            st.markdown("""
                            **What this does:**
                            - Scans your Azure Search index for SharePoint documents
                            - Checks if each file still exists in SharePoint
                            - Removes orphaned documents (files that were deleted from SharePoint but still exist in the index)
                            
                            **When to use:**
                            - After deleting files from SharePoint
                            - When you notice search results showing files that no longer exist
                            - As periodic maintenance to keep the index clean
                            
                            **How it works:**
                            - Uses Microsoft Graph API to verify file existence
                            - Processes files in batches for efficiency
                            - Provides detailed logging of deletion operations
                            """)
                        
                        # Purge controls
                        purge_col1, purge_col2 = st.columns([2, 1])
                        
                        with purge_col1:
                            st.markdown("**Run deletion purge for the current index:**")
                            st.info(f"🎯 Target index: **{target_index}**")
                            
                            # Show which folder will be used for folder-specific purging
                            if hasattr(st.session_state, 'sp_selected_folders') and st.session_state.sp_selected_folders:
                                raw_folder = st.session_state.sp_selected_folders[0]
                                # Parse folder path to extract just the folder part
                                if '|' in raw_folder:
                                    target_folder = raw_folder.split('|')[-1]
                                else:
                                    target_folder = raw_folder
                                st.info(f"📁 Target folder: **{target_folder}** (folder-specific purging)")
                                st.caption("Only files missing from this specific folder will be considered orphaned")
                            else:
                                st.info(f"📁 Target folder: **/ppt** (default folder-specific purging)")
                                st.caption("Only files missing from the /ppt folder will be considered orphaned")
                            
                            # Show warning about the operation
                            st.warning("⚠️ This will permanently delete orphaned documents from the search index. Make sure you have backups if needed.")
                            
                            # Purge options
                            show_preview = st.checkbox("Preview orphaned files before deletion", value=True)
                            
                        with purge_col2:
                            st.markdown("**Purge Status**")
                            
                            # Initialize purge status in session state
                            if "purge_status" not in st.session_state:
                                st.session_state.purge_status = {
                                    "is_running": False,
                                    "last_run": None,
                                    "last_result": None
                                }
                            
                            status = st.session_state.purge_status
                            
                            if status["is_running"]:
                                st.info("🔄 Purge Running...")
                            elif status["last_run"]:
                                st.success("✅ Last Run Complete")
                                st.caption(f"Time: {status['last_run']}")
                            else:
                                st.info("🟡 Ready to Run")
                        
                        # Purge action buttons
                        st.markdown("---")
                        purge_action_col1, purge_action_col2 = st.columns(2)
                        
                        with purge_action_col1:
                            if st.button("🔍 Preview Orphaned Files", disabled=status["is_running"]):
                                with st.spinner("Scanning for orphaned files..."):
                                    try:
                                        # Import and use the purger for preview
                                        import asyncio
                                        from connectors.sharepoint.sharepoint_deleted_files_purger import SharepointDeletedFilesPurger
                                        
                                        # Get the target folder path from session state or use /ppt as default
                                        target_folder_path = None
                                        if hasattr(st.session_state, 'sp_selected_folders') and st.session_state.sp_selected_folders:
                                            # Parse the first selected folder path to extract just the folder part
                                            raw_folder = st.session_state.sp_selected_folders[0]
                                            # Format: domain||site|folder_path - extract just the folder_path
                                            if '|' in raw_folder:
                                                target_folder_path = raw_folder.split('|')[-1]  # Get the last part
                                            else:
                                                target_folder_path = raw_folder
                                        else:
                                            # Default to /ppt folder for folder-specific purging
                                            target_folder_path = "/ppt"
                                        
                                        # Initialize and run the purger in preview mode with UI-selected index and folder
                                        purger = SharepointDeletedFilesPurger(index_name=target_index, target_folder_path=target_folder_path)
                                        
                                        # Run the async preview operation
                                        async def run_preview():
                                            return await purger.preview_deleted_files()
                                        
                                        # Execute the preview and get results
                                        preview_result = asyncio.run(run_preview())
                                        
                                        if preview_result["success"]:
                                            st.success("✅ Preview completed successfully!")
                                            
                                            # Show preview results
                                            col1, col2, col3 = st.columns(3)
                                            with col1:
                                                st.metric("Files Checked", preview_result["files_checked"])
                                            with col2:
                                                st.metric("Orphaned Files", preview_result["files_not_found"])
                                            with col3:
                                                st.metric("Chunks to Delete", preview_result["would_delete_count"])
                                            
                                            st.info(f"� {preview_result['message']}")
                                            
                                            # Show orphaned files details if any
                                            if preview_result["orphaned_files"]:
                                                st.markdown("**🗑️ Orphaned Files (would be deleted):**")
                                                
                                                for i, file_info in enumerate(preview_result["orphaned_files"][:10]):  # Show max 10
                                                    with st.expander(f"📄 {file_info['file_name']} ({file_info['chunk_count']} chunks)", expanded=False):
                                                        st.write(f"**File:** {file_info['file_name']}")
                                                        st.write(f"**Path:** {file_info['file_path']}")
                                                        st.write(f"**Parent ID:** {file_info['parent_id']}")
                                                        st.write(f"**Chunks:** {file_info['chunk_count']}")
                                                        st.caption("This file no longer exists in SharePoint but has indexed chunks in the search index.")
                                                
                                                if len(preview_result["orphaned_files"]) > 10:
                                                    st.caption(f"... and {len(preview_result['orphaned_files']) - 10} more files")
                                                
                                                st.warning("⚠️ These files would be permanently deleted from the search index if you run the purge.")
                                            else:
                                                st.success("🎉 No orphaned files found! Your index is clean.")
                                        else:
                                            st.error(f"❌ Preview failed: {preview_result['message']}")
                                            
                                            # Show error details
                                            if preview_result.get("errors"):
                                                st.markdown("**Error Details:**")
                                                for error in preview_result["errors"]:
                                                    st.error(f"• {error}")
                                        
                                    except Exception as e:
                                        st.error(f"❌ Preview failed: {str(e)}")
                                        st.markdown("""
                                        **Troubleshooting:**
                                        - Check SharePoint authentication credentials in `.env` file:
                                          - `SHAREPOINT_CONNECTOR_ENABLED=true`
                                          - `SHAREPOINT_TENANT_ID=your-tenant-id`
                                          - `SHAREPOINT_CLIENT_ID=your-client-id`
                                          - `SHAREPOINT_CLIENT_SECRET=your-client-secret`
                                          - `SHAREPOINT_SITE_DOMAIN=your-domain.sharepoint.com`
                                          - `SHAREPOINT_SITE_NAME=your-site-name` (optional for root site)
                                        - Verify Azure Search index permissions
                                        - Verify the search index contains SharePoint documents with `source='sharepoint'`
                                        - Index name is taken from UI selection: **{}**
                                        """.format(target_index))
                        
                        with purge_action_col2:
                            if st.button("🗑️ Run Purge Now", type="primary", disabled=status["is_running"]):
                                print("🚀 [UI DEBUG] PURGE BUTTON CLICKED! Starting purge directly...")
                                
                                # Show warning but proceed directly
                                if show_preview:
                                    st.warning("⚠️ Running purge - this will delete orphaned files from the search index.")
                                
                                # Run the actual purge
                                print("🚀 [UI DEBUG] Setting purge_status is_running = True")
                                st.session_state.purge_status["is_running"] = True
                                
                                with st.spinner("🗑️ Running deletion purge... This may take a few minutes."):
                                    try:
                                        import asyncio
                                        from connectors.sharepoint.sharepoint_deleted_files_purger import SharepointDeletedFilesPurger
                                        
                                        # Get the target folder path from session state or use /ppt as default
                                        target_folder_path = None
                                        if hasattr(st.session_state, 'sp_selected_folders') and st.session_state.sp_selected_folders:
                                            # Parse the first selected folder path to extract just the folder part
                                            raw_folder = st.session_state.sp_selected_folders[0]
                                            # Format: domain||site|folder_path - extract just the folder_path
                                            if '|' in raw_folder:
                                                target_folder_path = raw_folder.split('|')[-1]  # Get the last part
                                            else:
                                                target_folder_path = raw_folder
                                        else:
                                            # Default to /ppt folder for folder-specific purging
                                            target_folder_path = "/ppt"
                                        
                                        # Initialize and run the purger with UI-selected index and folder
                                        print(f"🚀 [UI DEBUG] STARTING PURGE FROM UI:")
                                        print(f"🚀 [UI DEBUG] Target index: {target_index}")
                                        print(f"🚀 [UI DEBUG] Target folder: {target_folder_path}")
                                        print(f"🚀 [UI DEBUG] Creating SharepointDeletedFilesPurger...")
                                        
                                        purger = SharepointDeletedFilesPurger(index_name=target_index, target_folder_path=target_folder_path)
                                        
                                        # Run the async purge operation and capture result
                                        async def run_purge():
                                            print(f"🚀 [UI DEBUG] About to call purge_deleted_files()...")
                                            result = await purger.purge_deleted_files()
                                            print(f"🚀 [UI DEBUG] Purge operation returned: {result}")
                                            return result
                                        
                                        # Execute the purge and get results
                                        print(f"🚀 [UI DEBUG] Running asyncio.run(run_purge())...")
                                        purge_result = asyncio.run(run_purge())
                                        print(f"🚀 [UI DEBUG] Purge completed, result: {purge_result}")
                                        
                                        # Update status based on result
                                        if purge_result["success"]:
                                            st.session_state.purge_status.update({
                                                "is_running": False,
                                                "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "last_result": "success"
                                            })
                                            
                                            # Store detailed results for history display
                                            st.session_state.last_purge_details = {
                                                'files_checked': purge_result["files_checked"],
                                                'files_not_found': purge_result["files_not_found"],
                                                'documents_deleted': purge_result["documents_deleted"],
                                                'documents_checked': purge_result["documents_checked"]
                                            }
                                            
                                            st.success("✅ Purge completed successfully!")
                                            
                                            # Show detailed results
                                            col1, col2, col3, col4 = st.columns(4)
                                            with col1:
                                                st.metric("Documents Checked", purge_result["documents_checked"])
                                            with col2:
                                                st.metric("Files Checked", purge_result["files_checked"])
                                            with col3:
                                                st.metric("Files Not Found", purge_result["files_not_found"])
                                            with col4:
                                                st.metric("Chunks Deleted", purge_result["documents_deleted"])
                                            
                                            st.info(f"📊 {purge_result['message']}")
                                            
                                            # Show next steps
                                            st.markdown("""
                                            **What happened:**
                                            - Scanned SharePoint documents in the search index
                                            - Checked each file's existence in SharePoint using Microsoft Graph API
                                            - Removed orphaned documents from the search index
                                            
                                            **Next steps:**
                                            - Run a test search to verify cleanup
                                            - Monitor your search index size for space savings
                                            """)
                                        else:
                                            # Handle failure case
                                            st.session_state.purge_status.update({
                                                "is_running": False,
                                                "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "last_result": f"error: {purge_result['message']}"
                                            })
                                            
                                            st.error(f"❌ Purge failed: {purge_result['message']}")
                                            
                                            # Show error details
                                            if purge_result.get("errors"):
                                                st.markdown("**Error Details:**")
                                                for error in purge_result["errors"]:
                                                    st.error(f"• {error}")
                                        
                                    except Exception as e:
                                        # Update status with error
                                        st.session_state.purge_status.update({
                                            "is_running": False,
                                            "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "last_result": f"error: {str(e)}"
                                        })
                                        
                                        st.error(f"❌ Purge failed: {str(e)}")
                                        
                                        # Show troubleshooting tips
                                        st.markdown("""
                                        **Troubleshooting:**
                                        - Check SharePoint authentication credentials in `.env` file:
                                          - `SHAREPOINT_CONNECTOR_ENABLED=true`
                                          - `SHAREPOINT_TENANT_ID=your-tenant-id`
                                          - `SHAREPOINT_CLIENT_ID=your-client-id`
                                          - `SHAREPOINT_CLIENT_SECRET=your-client-secret`
                                          - `SHAREPOINT_SITE_DOMAIN=your-domain.sharepoint.com`
                                          - `SHAREPOINT_SITE_NAME=your-site-name` (optional for root site)
                                        - Verify Azure Search index permissions
                                        - Verify the search index contains SharePoint documents with `source='sharepoint'`
                                        - Index name is taken from UI selection: **{}**
                                        """.format(target_index))
                                
                                st.rerun()
                        
                        # Show purge history if available
                        if status["last_result"]:
                            with st.expander("📊 Purge History", expanded=False):
                                if status["last_result"] == "success":
                                    st.success(f"✅ Last purge successful at {status['last_run']}")
                                    
                                    # Try to show additional details if they exist in session state
                                    if hasattr(st.session_state, 'last_purge_details'):
                                        details = st.session_state.last_purge_details
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Files Checked", details.get('files_checked', 'N/A'))
                                        with col2:
                                            st.metric("Files Deleted", details.get('files_not_found', 'N/A'))
                                        with col3:
                                            st.metric("Chunks Removed", details.get('documents_deleted', 'N/A'))
                                else:
                                    st.error(f"❌ Last purge failed at {status['last_run']}")
                                    st.error(f"Error: {status['last_result']}")
                                
                                st.markdown("""
                                **For detailed purge logs:**
                                - Check the application console output
                                - Look for `[sharepoint_purge_deleted_files]` log entries
                                - Monitor Azure Search index size before/after purge
                                
                                **Understanding the results:**
                                - **Files Checked**: Number of unique SharePoint files found in the index
                                - **Files Deleted**: Number of files that no longer exist in SharePoint
                                - **Chunks Removed**: Number of document chunks purged from the search index
                                """)
                
                else:
                    st.info("Select folders to index using the checkboxes above.")
        
        except ImportError:
            st.error("❌ SharePoint connector not available. Please install required dependencies.")
            st.markdown("""
            **Missing Dependencies:**
            - SharePoint Index Manager
            - SharePoint Data Reader
            - SharePoint Deleted Files Purger
            
            **To install:**
            ```bash
            pip install -r requirements.txt
            ```
            """)

    # ─────────────────── Tab 5 – Test Retrieval ──────────────────────────
    with tab_test:
        health_block()
        st.header("🔍 Test Retrieval")
        
        # Test retrieval functionality
        if not st.session_state.selected_index:
            st.warning("Please select an index first in the 'Manage Index' tab.")
        else:
            st.success(f"Testing retrieval from index: **{st.session_state.selected_index}**")
            
            test_query = st.text_input("Test Query", placeholder="Enter a search query to test retrieval")
            
            if test_query and st.button("🔍 Test Search"):
                with st.spinner("Searching..."):
                    try:
                        # Test the search functionality
                        search_client, _ = init_search_client()
                        results = search_client.search(
                            search_text=test_query,
                            top=st.session_state.get('top_k', 5),
                            include_total_count=True
                        )
                        
                        search_results = list(results)
                        
                        if search_results:
                            st.success(f"Found {len(search_results)} results")
                            
                            for i, result in enumerate(search_results):
                                with st.expander(f"Result {i+1}: {result.get('source_file', 'Unknown')} (Score: {result['@search.score']:.3f})"):
                                    st.write(f"**Content:** {result.get('content', result.get('page_chunk', 'No content'))[:500]}...")
                                    st.write(f"**Source:** {result.get('source_file', 'Unknown')}")
                                    st.write(f"**URL:** {result.get('url', 'No URL')}")
                                    st.write(f"**Page:** {result.get('page_number', 'Unknown')}")
                        else:
                            st.info("No results found for this query.")
                            
                    except Exception as e:
                        st.error(f"Search failed: {str(e)}")

    # ─────────────────── Tab 6 – Function Config ─────────────────────────
    with tab_cfg:
        health_block()
        st.header("⚙️ Azure Function Configuration")
        
        # Load environment variables
        env_vars = {}
        for key in [
            "INDEX_NAME", "AGENT_NAME", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY",
            "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_CHAT_DEPLOYMENT",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "AZURE_SEARCH_ENDPOINT",
            "AZURE_SEARCH_KEY"
        ]:
            env_vars[key] = os.getenv(key, "")

        st.markdown("Configure environment variables for Azure Function deployment.")

        # Index selection for function config
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

        # Try to pre‑fill subscription from az cli
        cli_sub = get_azure_subscription()
        sub_id = st.text_input("Subscription ID", cli_sub)

        # List Function Apps in this subscription
        func_choices, func_map = list_function_apps(sub_id)
        
        if not func_choices and sub_id:
            st.warning("⚠️ Could not list Function Apps automatically; fill manually.")

        func_sel_lbl = st.selectbox(
            "Choose Function App",
            ["-- manual input --"] + func_choices,
            index=0
        )
        st.session_state["func_map"] = func_map
        st.session_state["func_choices"] = func_choices
        
        if func_sel_lbl != "-- manual input --":
            app, rg = func_map[func_sel_lbl]
        else:
            rg = st.text_input("Resource Group", os.getenv("AZURE_RG", ""))
            app = st.text_input("Function App name", os.getenv("AZURE_FUNCTION_APP", ""))
        
        # Normalise variable names (func_name / func_rg) and keep old aliases
        func_name = app
        func_rg = rg

        if not all((sub_id, rg, app)):
            st.info("Fill subscription / RG / Function-App and click 🔄 Load settings.")
        else:
            if "func_raw" not in st.session_state:
                st.session_state.func_raw = {}
            if "func_df" not in st.session_state:
                st.session_state.func_df = pd.DataFrame(columns=["key", "value"])

            if st.button("🔄 Load settings"):
                success, df, raw, error_msg = load_function_settings(rg, app, sub_id, env_vars)
                if success:
                    st.session_state.func_raw = raw
                    st.session_state.func_df = df
                    st.success(f"Loaded & merged {len(df)} setting(s).")
                else:
                    st.error(f"Failed to load: {error_msg}")

        # Show editable table on every render once loaded
        if st.session_state.get("func_df") is not None and not st.session_state.func_df.empty:
            st.markdown("#### Function App Settings")
            st.session_state.func_df = _st_data_editor(
                st.session_state.func_df,
                num_rows="dynamic",
                use_container_width=True,
                key="func_editor",
            )

            # Push edited settings back to the Function App
            st.divider()
            if st.button("💾 Push settings to Function"):
                success, message = push_function_settings(
                    func_rg, 
                    func_name, 
                    sub_id, 
                    st.session_state.func_df,
                    st.session_state.func_raw
                )
                if success:
                    st.success(f"✅ {message} on **{func_name}**")
                else:
                    st.error(f"Failed to update Function settings:\n{message}")

        # Deploy local ./function code to this Function App
        st.divider()
        if st.button("🚀 Deploy local code to Function"):
            with st.spinner("⏳ Zipping and deploying, please wait…"):
                success, message, stdout = deploy_function_code(func_rg, func_name, sub_id)
                if success:
                    st.success(f"✅ {message}")
                    if stdout:
                        st.text(stdout)
                else:
                    st.error(message)

    # ─────────────────── Tab 6 – AI Foundry Agent ────────────────────────
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
            st.error("🔑 Run `az login` before using this feature.")
            st.stop()

        projects = get_ai_foundry_projects(cli_cred)
        
        # If no projects found, show helpful message
        if not projects:
            st.warning("No AI Foundry projects found via Azure CLI.")
            
            # Check for PROJECT_ENDPOINT in .env
            project_endpoint_env = os.getenv("PROJECT_ENDPOINT", "").strip()
            if project_endpoint_env:
                projects = [{
                    "name": project_endpoint_env.split('/')[-1][:30] or "env-project",
                    "location": "env",
                    "endpoint": project_endpoint_env,
                    "resource_group": "env",
                    "hub_name": "env",
                }]
                st.success(f"Using PROJECT_ENDPOINT from .env: {project_endpoint_env}")
            else:
                # Allow manual entry
                st.info(
                    "You can either:\n"
                    "1. Create a project in Azure AI Studio\n"
                    "2. Set the PROJECT_ENDPOINT environment variable in your .env file\n"
                    "3. Make sure you have access to at least one AI Foundry project"
                )
                
                manual_endpoint = st.text_input(
                    "Or enter Project Endpoint manually:",
                    placeholder="https://my-project.api.region.ai.azure.com/"
                )
                if manual_endpoint:
                    projects = [{
                        "name": "manual-project",
                        "location": "manual",
                        "endpoint": manual_endpoint,
                        "resource_group": "manual",
                        "hub_name": "manual",
                    }]
                else:
                    st.stop()

        proj_labels = [f"{p['name']} – {p['location']}" for p in projects]
        sel = st.selectbox("Choose Foundry project", proj_labels, index=0)
        project_endpoint = projects[proj_labels.index(sel)]['endpoint']
        st.caption(f"🔗 Endpoint: {project_endpoint}")

        agent_name = st.text_input("Agent name", placeholder="function‑assistant")
        if st.button("🚀 Create Agent") and agent_name:
            # Use the refactored function instead of inline code
            success, message, agent = create_ai_foundry_agent(
                project_endpoint=project_endpoint,
                agent_name=agent_name,
                base_url=base_url,
                function_key=FUNCTION_KEY
            )
            
            if success:
                st.success(f"✅ Agent **{agent.name}** created (ID: {agent.id})")
            else:
                st.error("Failed to create agent via SDK:")
                st.error(message)

    # ── Studio2Foundry Tab ────────────────────────────────────────────────
    with tab_studio2foundry:
        render_studio2foundry_tab()

##############################################################################
# Main entry point
##############################################################################

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "question",
        nargs="?",
        help="Your question (e.g. 'What is Azure AI Search?')"
    )
    parser.add_argument(
        "--model",
        choices=["o3", "4o", "41"],
        default="41",
        help="Model variant: o3 | 4o | 41 (default: 41)"
    )
    args = parser.parse_args()

    # If no question provided or running under Streamlit, show UI
    if not args.question or _st_in_runtime():
        run_streamlit_ui()
        return

    # CLI mode - process the question
    oai_client, chat_params = init_openai(args.model)
    search_client, _ = init_search_client(os.getenv("INDEX_NAME", "agentic-vectors"))

    # Plan queries
    queries = plan_queries(args.question, oai_client, chat_params)
    print(f"📋 Planned queries: {queries}")

    # Retrieve documents
    docs = retrieve(queries, search_client)
    print(f"📚 Retrieved {len(docs)} documents")

    # Build context and answer
    ctx = build_context(docs)
    final_answer, tokens = answer(args.question, ctx, oai_client, chat_params)
    
    print("\n" + "="*80)
    print(f"💬 Answer ({tokens} tokens):\n")
    print(final_answer)
    print("="*80 + "\n")

if __name__ == "__main__":
    main()