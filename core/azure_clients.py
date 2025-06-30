"""Azure client initialization functions"""
import os
import streamlit as st
import logging
from typing import Tuple
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.agent import KnowledgeAgentRetrievalClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from utils.azure_helpers import get_search_credential, env

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

def init_search_client(index_name: str | None = None) -> Tuple[SearchClient, SearchIndexClient]:
    """
    Return (search_client, index_client).
    Only API Key authentication is supported for agentic retrieval (see Azure docs).
    `index_name` – if provided, SearchClient will target that index,
    otherwise a dummy client pointing at the service root is returned.
    """
    endpoint = env("AZURE_SEARCH_ENDPOINT")
    credential = get_search_credential()

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

@st.cache_resource
def init_agent_client(agent_name: str) -> KnowledgeAgentRetrievalClient:
    """
    Create KnowledgeAgentRetrievalClient.
    Only API Key authentication is supported for agentic retrieval (see Azure docs).
    """
    cred = get_search_credential()   # Always AzureKeyCredential
    return KnowledgeAgentRetrievalClient(
        endpoint=env("AZURE_SEARCH_ENDPOINT"),
        agent_name=agent_name,
        credential=cred,
    )
