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

import streamlit as st
# Reliable check whether code runs under `streamlit run …`
try:
    from streamlit.runtime import exists as _st_in_runtime
except ImportError:       # fallback for older Streamlit
    _st_in_runtime = lambda: False

import re  # for citation parsing

from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ClientAuthenticationError
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
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
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
        if not page_text:
            continue
        vector = embed_text(oai_client, embed_deployment, page_text)
        doc = {
            "id": hashlib.md5(f"{pdf_file.name}_{page_num}".encode()).hexdigest(),
            "page_chunk": page_text,
            "page_embedding_text_3_large": vector,
            "page_number": page_num + 1,
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
            ],
            vector_search=VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="hnsw_text_3_large",
                        algorithm_configuration_name="alg",
                        vectorizer_name="azure_openai_text_3_large",
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(name="alg")
                ],
                vectorizers=[
                    AzureOpenAIVectorizer(
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
        # Create / update knowledge agent bound to this index + GPT‑4.1
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
    You are an AI assistant grounded in internal knowledge from Azure AI Search.
    • Use **only** the numbered context passages below.  
    • Quote snippets and cite them like [doc#].  
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

# -----------------------------------------------------------------------------
# Streamlit UI wrapper (run with: streamlit run agentic-rag-demo.py)
# -----------------------------------------------------------------------------
def run_streamlit_ui() -> None:
    st.set_page_config(page_title="Agentic RAG Demo", page_icon="📚", layout="wide")

    # --- ensure session keys exist ---
    for k, default in {
        "selected_index": None,
        "available_indexes": [],
        "uploaded_files": [],
        "indexed_documents": {},
        "history": [],
        "use_agentic": True,
        "agent_messages": [],
    }.items():
        st.session_state.setdefault(k, default)

    st.title("📚 Agentic Retrieval‑Augmented Chat")
    # --- global RTL helper class ---
    st.markdown(
        """
        <style>
        .rtl { direction: rtl; text-align: right; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar – choose model
    with st.sidebar:
        st.header("⚙️ Model")
        model_choice = st.selectbox(
            "Azure OpenAI Deployment",
            options=["41", "o3", "4o"],   # 4.1 first → becomes default
            index=0
        )
        # ---------------------------------------------------
        # Single OpenAI client for this UI run (needed by PDF‑ingest too)
        oai_client, chat_params = init_openai(model_choice)
        # ---------------------------------------------------
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
        st.checkbox("🔗 Use Knowledge Agent pipeline", key="use_agentic")
        st.subheader("🛠️ RAG Parameters")
        # How many documents to keep in context
        st.session_state.ctx_size = st.slider("Context chars per chunk",
                                              min_value=300, max_value=2000,
                                              value=600, step=50)
        # How many hits to retrieve per sub‑query
        st.session_state.top_k = st.slider("TOP‑K per query",
                                           min_value=1, max_value=200,
                                           value=5, step=1)
        # Reranker threshold for Knowledge‑Agent
        st.session_state.rerank_thr = st.slider("Reranker threshold",
                                                min_value=0.0, max_value=4.0,
                                                value=2.0, step=0.1)
        # Maximum JSON‑chunk size returned by the Knowledge‑Agent (maxOutputSize)
        st.session_state.max_output_size = st.slider("Knowledge‑agent maxOutputSize",
                                                     min_value=1000, max_value=16000,
                                                     value=5000, step=500)

        # --- Apply new maxOutputSize to existing Knowledge‑Agent -----------------
        if st.session_state.selected_index:
            if st.button("💾 Apply maxOutputSize", help="Update the selected index's Knowledge‑Agent"):
                try:
                    # Fetch current agent, update the request_limits and push the change
                    _, _icl = init_search_client()  # index client for service root
                    agent_name_sel = f"{st.session_state.selected_index}-agent"
                    agent_obj = _icl.get_agent(agent_name_sel)
                    agent_obj.request_limits = KnowledgeAgentRequestLimits(
                        max_output_size=int(st.session_state.max_output_size)
                    )
                    _icl.create_or_update_agent(agent_obj)
                    st.success(f"Knowledge‑Agent **{agent_name_sel}** updated "
                               f"to maxOutputSize = {st.session_state.max_output_size} B")
                except Exception as ex:
                    st.error(f"Failed to update agent limits: {ex}")
        else:
            st.caption("👉 Create / select an index to enable agent‑limit update")

        # Max completion tokens for chat responses
        st.session_state.max_tokens = st.slider("Max completion tokens",
                                                min_value=256, max_value=32768,
                                                value=32768, step=256)

        # Live chunk counter placeholder
        chunks_placeholder = st.empty()
        chunks_placeholder.caption(f"Chunks sent to LLM: {st.session_state.get('dbg_chunks', 0)}")

        # Reload .env button
        if st.button("🔄 Reload .env & restart"):
            _reload_env_and_restart()

        st.divider()
        st.header("🔒 RBAC Helper")

        user_upn, sub_id = _az_logged_user()
        if user_upn:
            st.markdown(f"**Signed‑in user:** {user_upn}")
            st.markdown(f"**Subscription:** {sub_id}")
            with st.expander("Grant 'Search Service Contributor' on this Search service", expanded=False):
                svc_name = env("AZURE_SEARCH_ENDPOINT").split("://")[1].split(".")[0]
                rg_input = st.text_input("Resource Group name", placeholder="my-search-rg", key="search_rg")
                principal = st.text_input("Assignee (leave blank = me)", value=user_upn, key="search_principal")
                if st.button("⚙️ Grant role"):
                    if not rg_input:
                        st.error("Please enter the Resource Group")
                    else:
                        roles = [
                            "Search Service Contributor",
                            "Search Index Data Contributor",
                        ]
                        ok_all = True
                        messages = []
                        for r in roles:
                            ok, msg = _grant_search_role(svc_name, sub_id, rg_input, principal or user_upn, r)
                            ok_all &= ok
                            messages.append(f"{r}: {msg}")
                        if ok_all:
                            st.success("✓ ".join(messages))
                        else:
                            st.error(" | ".join(messages))

            st.divider()
            st.header("🛡️ OpenAI Role Helper")

            # Try to derive account name from endpoint (use 41 as canonical)
            default_ep = os.getenv("AZURE_OPENAI_ENDPOINT_41") or os.getenv("AZURE_OPENAI_ENDPOINT", "")
            default_account = ""
            if default_ep:
                try:
                    default_account = default_ep.split("https://")[1].split(".")[0]
                except Exception:
                    pass

            with st.expander("Grant 'Cognitive Services OpenAI User' on this OpenAI account", expanded=False):
                oai_account = st.text_input("OpenAI account name", value=default_account, placeholder="my-openai")
                oai_rg = st.text_input("Resource Group name", placeholder="my-openai-rg", key="openai_rg")
                oai_principal = st.text_input("Assignee (leave blank = me)", value=user_upn or "", key="openai_principal")
                role_choice = st.selectbox("Role",
                                           options=["Cognitive Services OpenAI User", "Cognitive Services Contributor"],
                                           index=0)
                if st.button("⚙️ Grant OpenAI role"):
                    if not (oai_account and oai_rg):
                        st.error("Enter both Account name and Resource Group.")
                    else:
                        ok, msg = _grant_openai_role(
                            oai_account, sub_id, oai_rg, oai_principal or user_upn, role_choice
                        )
                        (st.success if ok else st.error)(msg)
        else:
            st.info("User not logged via az cli ‑ run `az login` in the terminal.")

    # ---------------- Index management -----------------
    st.header("📚 Index Management")

    # Refresh list of indexes each time sidebar is drawn
    _, sidebar_index_client = init_search_client()   # no index yet
    # After refreshing, show warning if no indexes found
    if not st.session_state.available_indexes:
        st.warning("⚠️ No indexes found or insufficient permissions. "
                   "Check Search Index Data Reader role.")

    col1, col2 = st.columns(2)
    with col1:
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

    with col2:
        new_index_name = st.text_input("New index name", placeholder="e.g. agentic-vectors")
        if st.button("➕ Create new index") and new_index_name:
            if create_agentic_rag_index(sidebar_index_client, new_index_name):
                st.success(f"Created index '{new_index_name}'")
                st.session_state.selected_index = new_index_name
                st.session_state.available_indexes.append(new_index_name)

    # ---------------- PDF uploader -----------------
    st.subheader("📄 Upload PDFs to index")
    if not st.session_state.selected_index:
        st.info("Select or create an index first.")
    else:
        uploaded = st.file_uploader("Choose PDF files", type=["pdf"], accept_multiple_files=True)
        if uploaded:
            if st.button("🚀 Ingest PDFs"):
                with st.spinner("Embedding and uploading..."):
                    _, iclient = init_search_client(st.session_state.selected_index)
                    sender = SearchIndexingBufferedSender(
                        endpoint=env("AZURE_SEARCH_ENDPOINT"),
                        index_name=st.session_state.selected_index,
                        credential=_search_credential(),
                    )
                    embed_deploy = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
                    total = 0
                    for pf in uploaded:
                        docs = pdf_to_documents(pf, oai_client, embed_deploy)
                        sender.upload_documents(documents=docs)
                        total += len(docs)
                    sender.close()
                    st.success(f"Uploaded {total} pages into '{st.session_state.selected_index}'.")

    #--- build / refresh clients ------------------------------------------------
    search_client, _ = init_search_client(st.session_state.selected_index)

    # Chat history
    if "history" not in st.session_state:
        st.session_state.history = []

    # Display history
    for turn in st.session_state.history:
        with st.chat_message(turn["role"]):
            st.markdown(f'<div class="rtl">{turn["content"]}</div>', unsafe_allow_html=True)

    user_query = st.chat_input("Ask your question…")
    if user_query:
        st.session_state.history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(f'<div class="rtl">{user_query}</div>', unsafe_allow_html=True)

        if st.session_state.use_agentic and st.session_state.selected_index:
            with st.spinner("Knowledge‑agent retrieval…"):
                agent_name = f"{st.session_state.selected_index}-agent"
                agent_client = init_agent_client(agent_name)

                # ------------------------------------------------------------------
                # Conversational instructions (persist for the whole session)
                instr = (
                    "Answer the question based only on the indexed sources. "
                    "Cite ref_id in square brackets. If unknown, answer \"I don't know\"."
                )

                # 1️⃣  Build / update running message history
                if not st.session_state.agent_messages:
                    # first turn – seed with system‑style assistant instruction
                    st.session_state.agent_messages = [
                        {"role": "assistant", "content": instr}
                    ]

                # append current user question
                st.session_state.agent_messages.append(
                    {"role": "user", "content": user_query}
                )

                # convert to SDK objects
                message_objs = [
                    KnowledgeAgentMessage(
                        role=m["role"],
                        content=[KnowledgeAgentMessageTextContent(text=m["content"])]
                    )
                    for m in st.session_state.agent_messages
                ]

                ka_req = KnowledgeAgentRetrievalRequest(
                    messages=message_objs,
                    target_index_params=[
                        KnowledgeAgentIndexParams(
                            index_name=st.session_state.selected_index,
                            reranker_threshold=float(st.session_state.rerank_thr)
                        )
                    ],
                    request_limits=KnowledgeAgentRequestLimits(
                        max_output_size=int(st.session_state.max_output_size)
                    ),
                )
                try:
                    result = agent_client.knowledge_retrieval.retrieve(retrieval_request=ka_req)
                except ClientAuthenticationError as err:
                    st.error(
                        "❌ Unauthorized (401).\n\n"
                        "• Make sure **Role‑based access control** is enabled on the service.\n"
                        "• Assign yourself **Search Service Contributor** and "
                        "**Search Index Data Contributor** roles.\n"
                        "• Or temporarily set an Admin key in `AZURE_SEARCH_KEY`."
                    )
                    st.exception(err)
                    return
                # ------------------------------------------------------------------
                # 1) Low‑level response (chunks) -----------------------------------
                raw_text = result.response[0].content[0].text   # JSON or plain text

                # Persist chunks as the assistant's turn for future questions
                st.session_state.agent_messages.append(
                    {"role": "assistant", "content": raw_text}
                )

                # Try to parse the JSON list that the knowledge‑agent usually emits
                try:
                    parsed = json.loads(raw_text)
                    if isinstance(parsed, list):
                        ctx_for_llm = "\n\n".join(
                            f"[doc{item.get('ref_id')}] {item.get('content','')}"
                            for item in parsed
                        )
                    else:
                        # agent returned plain text – use as is
                        ctx_for_llm = parsed
                except Exception:
                    ctx_for_llm = raw_text

                # ------------------------------------------------------------------
                # 2) Pass the chunks to OpenAI for **final answer generation**
                num_chunks = len(result.response)
                st.session_state.dbg_chunks = num_chunks
                chunks_placeholder.caption(f"Chunks sent to LLM: {num_chunks}")
                answer_text, usage_tok = answer(user_query, ctx_for_llm, oai_client, chat_params)

                # ------------------------------------------------------------------
                # 3) Build docs list for “Sources” pane from result.references
                docs = [
                    {"id": i + 1, "url": ref.doc_key, "page_chunk": ""}
                    for i, ref in enumerate(result.references)
                ]
                # --- low‑level reference diagnostics ---
                for ref in result.references:
                    logging.warning(
                        "KA ref: doc_key=%s  reranker_score=%s",
                        getattr(ref, "doc_key", None),
                        getattr(ref, "reranker_score", None),
                    )
                logging.warning("KA references returned: %s", len(result.references))
                # --- diagnostics ---
                unique_sources = {ref.doc_key for ref in result.references}
                st.caption(f" Unique sources in answer: {len(unique_sources)}")

                chunk_bytes = len(raw_text.encode("utf-8"))
                logging.warning("KA output size: %s bytes", chunk_bytes)

                # 4) Optional: expose Activity & Results in UI
                with st.expander("⚙️  Retrieval activity"):
                    st.json([a.as_dict() for a in result.activity], expanded=False)

                with st.expander("📑  Raw references"):
                    st.json([r.as_dict() for r in result.references], expanded=False)
        else:
            with st.spinner("Planning, searching, answering…"):
                # 🔀 Split multi‑line or multi‑sentence questions so each line
                #     is planned separately, then flatten the resulting lists
                user_parts = [p.strip() for p in user_query.split("\n") if p.strip()]
                sub_q = []
                for part in user_parts:
                    sub_q.extend(plan_queries(part, oai_client, chat_params))

                docs = retrieve(sub_q, search_client)
                num_chunks = len(docs)
                st.session_state.dbg_chunks = num_chunks
                chunks_placeholder.caption(f"Chunks sent to LLM: {num_chunks}")
                ctx = build_context(docs)
                answer_text, usage_tok = answer(user_query, ctx, oai_client, chat_params)

        with st.chat_message("assistant"):
            st.markdown(f'<div class="rtl">{answer_text}</div>', unsafe_allow_html=True)
            if 'usage_tok' in locals():
                st.caption(f"_Tokens used: {usage_tok}_")

        # ---- Sources block -------------------------------------------------
        cited_ids = {int(m.group(1)) for m in re.finditer(r"\[doc(\d+)]", answer_text)}
        if cited_ids:
            with st.expander("📚 Sources", expanded=False):
                for cid in sorted(cited_ids):
                    doc = next((d for d in docs if d["id"] == cid), None)
                    if not doc:
                        continue
                    page = doc.get("page_number", "")
                    page_str = f"(page {page})" if page else ""
                    url = doc.get("url") or doc.get("source", "")
                    if url:
                        st.markdown(f"**doc{cid}** {page_str} — [{url}]({url})")
                    else:
                        st.markdown(f"**doc{cid}** {page_str}")
                    st.write(doc.get("page_chunk", doc.get("content", ""))[:500] + "…")
                    st.divider()

        # --------------------------------------------------------------------

        st.session_state.history.append({"role": "assistant", "content": answer_text})

        with st.expander("🔍 Debug info"):
            st.subheader("Queries")
            st.write(sub_q if not st.session_state.use_agentic or not st.session_state.selected_index else "N/A (agentic)")
            st.subheader("Context")
            st.write(ctx if not st.session_state.use_agentic or not st.session_state.selected_index else "N/A (agentic)")


def main() -> None:
    # Detect if we were launched via Streamlit
    if _st_in_runtime():
        run_streamlit_ui()
        return

    parser = argparse.ArgumentParser(description="Agentic RAG demo (SDK‑1.x)")
    parser.add_argument("question", nargs="*", help="Question to ask from CLI")
    parser.add_argument("--model", choices=["o3", "4o", "41"], default="41",
                        help="Which deployment suffix to use")
    args = parser.parse_args()

    question = " ".join(args.question) if args.question else input("❓ Ask a question: ")
    if not question:
        sys.exit(0)

    oai_client, chat_params = init_openai(args.model)
    search_client, _ = init_search_client(env("AZURE_SEARCH_INDEX"))

    # Optional: set max_output_size for CLI path
    MAX_OUTPUT_SIZE = int(os.getenv("MAX_OUTPUT_SIZE", 5000))

    print("🧠 Planning queries…", file=sys.stderr, flush=True)
    # Split CLI question on newlines / sentences for independent planning
    user_parts = [p.strip() for p in question.split("\n") if p.strip()]
    sub_q = []
    for part in user_parts:
        sub_q.extend(plan_queries(part, oai_client, chat_params))

    print(f"🔍 Retrieving with {len(sub_q)} sub‑queries…", file=sys.stderr)
    docs = retrieve(sub_q, search_client)
    ctx = build_context(docs)

    print("✍️  Generating answer…", file=sys.stderr)
    result = answer(question, ctx, oai_client, chat_params)
    print("\n" + result + "\n")

    if os.getenv("DEBUG_RAG"):
        print("\n--- SUB‑QUERIES ---")
        print(json.dumps(sub_q, indent=2))
        print("\n--- CONTEXT ---")
        print(ctx)


if __name__ == "__main__":
    main()