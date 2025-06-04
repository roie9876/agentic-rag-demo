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
TOP_K = int(os.getenv("TOP_K", 5))


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
        temperature=0.2,
        max_tokens=20000,
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
                SearchField(name="page_chunk",
                            type="Edm.String",
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
    into up to three concise Azure AI Search queries. Return **only** a JSON
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
        for res in client.search(q, top=TOP_K):
            docs.append(
                {
                    "id": len(docs) + 1,
                    "query": q,
                    "score": res["@search.score"],
                    "content": res.get("content", str(res))[:4000],
                }
            )
    return docs


def build_context(docs: List[dict]) -> str:
    """
    Build a concise context string:
    • Use only the first TOP_K docs
    • Truncate each chunk to 600 chars (was 2 000)
    """
    return "\n\n".join(
        f"[doc{d['id']}] {d['content'][:600]}…" for d in docs[:TOP_K]
    )


def answer(question: str, ctx: str, client: AzureOpenAI, params: dict) -> str:
    msgs = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "system", "content": f"Context:\n\n{ctx}"},
        {"role": "user", "content": question},
    ]
    resp = client.chat.completions.create(messages=msgs, **params)
    return resp.choices[0].message.content.strip()


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
    }.items():
        st.session_state.setdefault(k, default)

    st.title("📚 Agentic Retrieval‑Augmented Chat")

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
            st.markdown(turn["content"])

    user_query = st.chat_input("Ask your question…")
    if user_query:
        st.session_state.history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        if st.session_state.use_agentic and st.session_state.selected_index:
            with st.spinner("Knowledge‑agent retrieval…"):
                agent_name = f"{st.session_state.selected_index}-agent"
                agent_client = init_agent_client(agent_name)

                instr = (
                    "Answer the question based only on the indexed sources. "
                    "Cite ref_id in square brackets. If unknown, answer \"I don't know\"."
                )

                ka_req = KnowledgeAgentRetrievalRequest(
                    messages=[
                        KnowledgeAgentMessage(
                            role="assistant",
                            content=[KnowledgeAgentMessageTextContent(text=instr)]
                        ),
                        KnowledgeAgentMessage(
                            role="user",
                            content=[KnowledgeAgentMessageTextContent(text=user_query)]
                        ),
                    ],
                    target_index_params=[
                        KnowledgeAgentIndexParams(
                            index_name=st.session_state.selected_index,
                            reranker_threshold=3.0,   # stricter → fewer low‑score passages
                        )
                    ],
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
                raw_text = result.response[0].content[0].text

                # אם ה-agent החזיר מערך JSON של מקטעים – נפרוס אותם לטקסט קריא
                try:
                    parsed = json.loads(raw_text)
                    if isinstance(parsed, list):
                        answer_text = "\n\n".join(
                            f"**[doc{item.get('ref_id')}]**  {item.get('content','')}"
                            for item in parsed
                        )
                    else:
                        answer_text = raw_text
                except Exception:
                    answer_text = raw_text
                # Build minimal docs list from references for the Sources expander
                docs = [
                    {"id": i + 1, "url": ref.doc_key, "page_chunk": ""}
                    for i, ref in enumerate(result.references)
                ]
        else:
            with st.spinner("Planning, searching, answering…"):
                sub_q = plan_queries(user_query, oai_client, chat_params)
                docs = retrieve(sub_q, search_client)
                ctx = build_context(docs)
                answer_text = answer(user_query, ctx, oai_client, chat_params)

        with st.chat_message("assistant"):
            st.markdown(answer_text)

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

    print("🧠 Planning queries…", file=sys.stderr, flush=True)
    sub_q = plan_queries(question, oai_client, chat_params)

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