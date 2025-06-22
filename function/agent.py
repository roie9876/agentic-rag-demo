#!/usr/bin/env python3
"""
agent.py  –  Minimal CLI tester for an Azure AI Search *Knowledge‑Agent*
using the new May‑2025 REST routes (`:retrieve` / `:responses`).

USAGE
-----
python agent.py "השאלה שלי כאן"

The script:
1. Fetches an AAD bearer‑token via `az account get-access-token`
2. Builds the minimal messages array (system‑style assistant instruction +
   the user question from argv)
3. Calls the **responses** endpoint so the service will generate the final,
   merged answer (no extra OpenAI call is required).
4. Prints status, headers, and saves full JSON to *agentic_response.json*
"""

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from textwrap import indent
from typing import Optional, Union

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file if present

import requests
from openai import AzureOpenAI
import os
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")  # ← new optional var
MAX_OUTPUT_SIZE = int(os.getenv("MAX_OUTPUT_SIZE", "16000"))   # ← new
TOP_K_DEFAULT   = int(os.getenv("TOP_K", "50"))        # ← NEW default

# ──────────────────────────────────────────────────────────────────────────────
# ====== EDIT THESE CONSTANTS ==================================================
SERVICE_NAME = os.getenv("SERVICE_NAME")
AGENT_NAME   = os.getenv("AGENT_NAME")
API_VERSION = os.getenv("API_VERSION", "2025-05-01-preview")  # default kept for convenience
# ============================================================================

DEFAULT_AGENT = AGENT_NAME   # keep env value as default

# ----- remove the import-time check ---------------------------------
# missing = [n for n in ("SERVICE_NAME", "AGENT_NAME") if not globals()[n] or "<" in globals()[n]]
# if missing:
#     raise RuntimeError(...)
# --------------------------------------------------------------------


# Build endpoint  (retrieve returns the individual chunks)
ENDPOINT = (
    f"https://{SERVICE_NAME}.search.windows.net"
    f"/agents/{AGENT_NAME}/retrieve"
    f"?api-version={API_VERSION}"
)

# ─────────────────── helper to get bearer token ──────────────────────────────
def get_bearer_token() -> Optional[str]:
    """Return a Managed-Identity token (or None when unavailable)."""
    try:
        return DefaultAzureCredential().get_token(
            "https://search.azure.com/.default"
        ).token
    except Exception:
        return None


def _validate_env() -> None:
    """Raise if critical vars not set; called at run-time."""
    missing = [
        n for n in ("SERVICE_NAME", "AGENT_NAME")
        if not globals()[n] or "<" in globals()[n]
    ]
    if missing:
        raise RuntimeError(
            "Environment variables not set: "
            + ", ".join(missing)
            + ". Edit local.settings.json or export them in your shell."
        )


def _build_search_headers() -> dict[str, str]:
    """
    Determine auth header:
      • use SEARCH_API_KEY if provided
      • else use bearer token from Managed Identity
    """
    if SEARCH_API_KEY:
        return {"api-key": SEARCH_API_KEY, "Content-Type": "application/json"}

    token = get_bearer_token()
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    raise RuntimeError(
        "No Search authentication available. "
        "Set SEARCH_API_KEY or assign a Managed Identity to the Function App."
    )


def _search_client(index_name: str) -> SearchClient:
    """Return a SearchClient for *index_name* using the same auth method as queries."""
    cred = AzureKeyCredential(SEARCH_API_KEY) if SEARCH_API_KEY else DefaultAzureCredential()
    return SearchClient(
        endpoint=f"https://{SERVICE_NAME}.search.windows.net",
        index_name=index_name,
        credential=cred,
    )

# ---------------------------------------------------------------------------
INDEX_NAME          = os.getenv("INDEX_NAME", "agentic-rag")
RERANKER_THRESHOLD  = float(os.getenv("RERANKER_THRESHOLD", "2.5"))

# ---------------------------------------------------------------------------
# ⬇⬇⬇  NEW: lightweight summarizer so /retrieve results can be merged locally
try:
    # Expect these env‑vars when running in Azure Functions
    OPENAI_ENDPOINT    = os.getenv("OPENAI_ENDPOINT")
    OPENAI_KEY         = os.getenv("OPENAI_KEY")
    OPENAI_DEPLOYMENT  = os.getenv("OPENAI_DEPLOYMENT")  # model/deployment name

    if OPENAI_ENDPOINT and OPENAI_KEY and OPENAI_DEPLOYMENT:
        _openai_client = AzureOpenAI(
            api_key=OPENAI_KEY,
            azure_endpoint=OPENAI_ENDPOINT,
            api_version="2024-02-15-preview",   # works for both 3.5/4 turbo
        )
    else:
        _openai_client = None
except Exception:                                # fallback when sdk missing
    _openai_client = None


def summarize_with_llm(chunks_text: str, user_q: str) -> str:
    """
    Merge multiple retrieved chunks into a concise Hebrew answer.

    This helper is used only when the Knowledge‑Agent `/retrieve`
    endpoint is called (i.e. when `use_responses=False`).

    • If an Azure OpenAI client is available → ask the LLM
    • Otherwise → fall back to returning the raw chunks.
    """
    if not _openai_client:                       # no credentials / sdk
        # simple deterministic fallback
        return chunks_text[:MAX_OUTPUT_SIZE]

    system_msg = (
        "ענה בקצרה ובבהירות . הסתמך אך ורק על המידע המופיע ב‑chunks "
        "והצג סימוכין בסוגריים מרובעות—for example [my_document.pdf]. "
        "אם אין מידע, השב \"אין לי מידע\"."
    )
    prompt = (
        f"== Chunks ==\n{chunks_text}\n"
        f"== Question ==\n{user_q}\n"
        "== End =="
    )
    try:
        resp = _openai_client.chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return chunks_text[:MAX_OUTPUT_SIZE]


# ---------------------------------------------------------------------------
def _extract_citation_labels(text: str) -> set[str]:
    """
    Return the set of labels that appear inside square-brackets in *text*,
    e.g. "… כמו [foo.pdf] ו-[bar.docx]" -> {"foo.pdf", "bar.docx"}.
    """
    return {m.strip() for m in re.findall(r"\[([^\[\]]+?)\]", text)}
# ---------------------------------------------------------------------------

def answer_question(
        user_question: str,
        index_name: Optional[str] = None,
        reranker_threshold: Optional[float] = None,
        agent_name: Optional[str] = None,
        max_output_size: Optional[int] = None,
        top_k: Optional[int] = None,          # ← NEW
        use_responses: bool = False,
        debug: bool = False,
        include_sources: bool = False
) -> Union[str, dict]:
    _validate_env()
    headers = _build_search_headers()

    idx   = index_name  or INDEX_NAME
    thres = reranker_threshold if reranker_threshold is not None else RERANKER_THRESHOLD
    agn   = agent_name or DEFAULT_AGENT               # ← pick agent
    max_out = max_output_size or MAX_OUTPUT_SIZE
    tk = top_k if top_k is not None else TOP_K_DEFAULT

    route = "responses" if use_responses else "retrieve"
    endpoint = (
        f"https://{SERVICE_NAME}.search.windows.net"
        f"/agents/{agn}/{route}"
        f"?api-version={API_VERSION}"
    )

    body = {
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Answer the question based only on the indexed sources. "
                            "Cite ref_id in square brackets. If unknown, say \"I don't know\"."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": user_question}],
            },
        ],
        "targetIndexParams": [
            {
                "indexName": idx,
                "rerankerThreshold": thres,
                #"topK": tk,
                # "citationFieldName": "source_file",
            }
        ]
    }
    # Top‑level setting for which field the agent should use as citation label
    
    # Ensure /retrieve returns doc_key so we can look up source_file later

    # When we use the /responses route we can request extra metadata so we can
    # map citations back to the original filename or URL.
    if use_responses:
        body["citationFieldName"] = "source_file"
        body["responseFields"] = ["text", "doc_key", "source_file", "url"]
        # NOTE: maxOutputSize is not a valid parameter for /retrieve API - it's set on the knowledge agent definition

    resp = requests.post(endpoint, headers=headers, json=body, timeout=60)

    if debug:
        # Return raw payload for inspection
        return json.dumps(resp.json(), ensure_ascii=False, indent=2)

    try:
        koa = resp.json()                       # normal JSON path
    except ValueError:
        # Service returned an empty body or non-JSON (HTML, 502, etc.)
        return (
            f"⚠️  Search returned non-JSON (HTTP {resp.status_code}). "
            f"First 200 bytes:\n{resp.text[:200]}"
        )

    if "error" in koa:
        err = koa["error"]
        return f"⚠️  Knowledge-Agent error ({err.get('code','')}: {err.get('message','')})"

    # ---------------- extraction -----------------
    if use_responses:
        try:
            # The service may return one or many text parts
            parts = koa["response"][0]["content"]
            if isinstance(parts, list):
                txt = " ".join(p.get("text", "") for p in parts if isinstance(p, dict))
            else:                       # unexpected, but keep graceful
                txt = str(parts)
            return txt.strip()
        except Exception as exc:
            return f"⚠️  Unexpected /responses payload: {exc}"

    try:
        # -------- schema-agnostic extraction --------------------------------
        if "response" in koa:               # ← /responses OR “merged” retrieve
            json_str = koa["response"][0]["content"][0]["text"]
            try:
                # If it’s a JSON list of chunks → continue below
                chunks = json.loads(json_str)
            except Exception:
                # Not JSON → it is already the final answer
                return json_str.strip()
        elif "chunks" in koa:
            chunks = koa["chunks"]
        else:
            raise KeyError(f"Unexpected keys {list(koa)}")
        # --------------------------------------------------------------------

        # --- ensure source_file is present so citations are meaningful -------
        try:
            sclient = None
            for c in chunks:
                if "source_file" not in c and "doc_key" in c:
                    # lazy create SearchClient only when needed
                    if sclient is None:
                        sclient = _search_client(idx)
                    try:
                        doc = sclient.get_document(key=c["doc_key"])
                        if doc and "source_file" in doc:
                            c["source_file"] = doc["source_file"]
                    except Exception:
                        # silently ignore lookup errors
                        pass
        except Exception:
            # any unexpected failure should not break the main flow
            pass

        # Use the most helpful human‑readable citation label in priority order:
        def _label(chunk: dict) -> str:
            """
            Choose the most helpful human‑readable citation label
            in priority order:
              1) source_file   (file name when present)
              2) source        (alias field)
              3) url           (last segment of URL)
              4) filename embedded at start of content, e.g. “[my.pdf] …”
              5) fallback      (generic docN)
            """
            if chunk.get("source_file"):
                return chunk["source_file"]

            if chunk.get("source"):
                return chunk["source"]

            if chunk.get("url"):
                return Path(chunk["url"]).name or chunk["url"]

            # NEW – parse leading “[filename] …” in the chunk text itself
            txt = chunk.get("content", "")
            if txt.startswith("[") and "]" in txt[:150]:
                return txt[1:txt.find("]")]

            return f"doc{chunk.get('ref_id', '?')}"
        raw_chunks = " ".join(f"[{_label(c)}] {c['content']}" for c in chunks)

        # Summarise the retrieved information with the LLM so we get a
        # coherent answer even when multiple questions are asked together.
        base_answer = summarize_with_llm(raw_chunks, user_question)[:MAX_OUTPUT_SIZE]
        
        # Generate enhanced answer with rich metadata (like Streamlit app)
        if include_sources:
            # Build preliminary sources for enhancement
            preliminary_sources = []
            for c in chunks:
                src_name = (
                    c.get("source_file")
                    or c.get("source")
                    or c.get("url")
                    or _label(c)
                )
                if src_name:
                    preliminary_sources.append({
                        "source_file": src_name,
                        "url": c.get("url", "") if c.get("url", "").startswith(("http://", "https://")) else ""
                    })
            
            # Generate enhanced answer with page numbers, figures, and clickable links
            final_answer = generate_enhanced_answer(base_answer, chunks, preliminary_sources)
        else:
            final_answer = base_answer

        if include_sources:
            # Collect doc_keys from chunks (retrieve) or references (responses)
            doc_keys = set()

            if use_responses and "references" in koa:
                doc_keys.update(r.get("doc_key") for r in koa["references"] if r.get("doc_key"))
            else:
                # chunks path
                for c in chunks:
                    if "doc_key" in c:
                        doc_keys.add(c["doc_key"])

            sources = []
            if doc_keys:
                sclient = _search_client(idx)
                for k in doc_keys:
                    try:
                        doc = sclient.get_document(key=k)
                        sources.append(
                            {
                                "doc_key": k,
                                "source_file": doc.get("source_file", ""),
                                "url": doc.get("url", ""),
                            }
                        )
                    except Exception:
                        sources.append({"doc_key": k, "source_file": "", "url": ""})

            # Fallback: if we still have no sources (e.g. doc_keys were absent
            # or look‑ups failed), build them from whatever identifying data
            # we already have in the retrieved chunks.
            if not sources:
                seen = set()
                for c in chunks:
                    # Prefer explicit filename, else source, else URL, else the generic label
                    src_name = (
                        c.get("source_file")
                        or c.get("source")
                        or c.get("url")
                        or _label(c)
                    )
                    if src_name and src_name not in seen:
                        sources.append(
                            {
                                "doc_key": c.get("doc_key"),
                                "source_file": src_name,
                                "url": (
                                    c["url"]
                                    if c.get("url", "").startswith(("http://", "https://"))
                                    else ""
                                ),
                            }
                        )
                        seen.add(src_name)

            # ---- Best‑effort URL enrichment (if still missing) -----------------
            for entry in sources:
                if entry.get("url", "").startswith(("http://", "https://")):
                    continue  # already have a full URL
                try:
                    # Re‑use previously created SearchClient if available
                    if 'sclient' not in locals() or sclient is None:
                        sclient = _search_client(idx)
                    safe_src = entry["source_file"].replace("'", "''")  # escape single quotes
                    filt = f"source_file eq '{safe_src}'"
                    hits = sclient.search(search_text="*", filter=filt, top=1)
                    for h in hits:
                        if "url" in h and h["url"]:
                            entry["url"] = h["url"]
                            break
                except Exception:
                    # Leave url empty on any failure
                    pass

            # ── NEW: filter out sources that were not cited in the answer ──────
            cited = _extract_citation_labels(final_answer)
            if cited:
                def _match(src: dict) -> bool:
                    fname = src.get("source_file", "")
                    url   = src.get("url", "")
                    url_tail = Path(url).name if url else ""
                    return fname in cited or url_tail in cited
                sources = [s for s in sources if _match(s)]

            # ── NEW: second-pass enrichment to restore missing URLs ───────────
            for entry in sources:
                if entry.get("url"):               # already has one
                    continue
                try:
                    sclient = _search_client(idx)  # reuse helper
                    safe_src = entry["source_file"].replace("'", "''")
                    hits = sclient.search(search_text="*", filter=f"source_file eq '{safe_src}'", top=1)
                    for h in hits:
                        if h.get("url"):
                            entry["url"] = h["url"]
                            break
                except Exception:
                    pass  # leave url empty on error

            # ── NEW: Add Sources section at end of answer (like Streamlit app) ──────
            if sources:
                sources_section = "\nSources:\n"
                for source in sources:
                    source_file = source.get("source_file", "")
                    url = source.get("url", "")
                    if source_file:
                        if url:
                            sources_section += f"• {source_file} – {url}\n"
                        else:
                            sources_section += f"• {source_file}\n"
                final_answer += sources_section
            
            # ←── return JSON object instead of plain text
            return {"answer": final_answer, "sources": sources}

        # return plain answer when include_sources == False
        return final_answer

    except Exception as exc:
        # Gracefully handle any unexpected issues during extraction or summarization
        return f"⚠️  Unexpected processing error: {exc}"


def extract_enhanced_citations(chunks):
    """
    Extract enhanced citation information from chunks to suggest improved answer format
    Similar to test_retrieval.py functionality
    """
    citations = []
    
    if not chunks:
        return citations
    
    # Group chunks by document
    doc_chunks = {}
    for chunk in chunks:
        if isinstance(chunk, dict):
            # Try to get document name from various fields
            doc_name = ""
            content = chunk.get("content", "")
            
            # First try direct metadata fields
            if chunk.get("source_file"):
                doc_name = chunk["source_file"]
            elif chunk.get("filename"):
                doc_name = chunk["filename"]
            elif chunk.get("source"):
                doc_name = chunk["source"]
            # Extract from content if starts with [filename]
            elif content.startswith("[") and "]" in content[:150]:
                doc_name = content[1:content.find("]")]
            
            if doc_name:
                if doc_name not in doc_chunks:
                    doc_chunks[doc_name] = []
                doc_chunks[doc_name].append(chunk)
    
    # Extract metadata for each document
    for doc_name, chunks_list in doc_chunks.items():
        pages = set()
        figures = []
        
        for chunk in chunks_list:
            content = chunk.get("content", "")
            
            # Extract page numbers from various patterns
            import re
            
            # Pattern 1: <!-- PageNumber="X" -->
            page_matches = re.findall(r'<!-- PageNumber="(\d+)" -->', content)
            for match in page_matches:
                try:
                    pages.add(int(match))
                except ValueError:
                    pass
            
            # Pattern 2: Page X, pp. X, עמ' X
            page_patterns = [
                r'(?:Page|pp?\.|עמ\')\s*(\d+)',
                r'(?:page|עמוד)\s+(\d+)',
                r'\bp\.\s*(\d+)\b',
                r'עמ\'\s*(\d+)'
            ]
            
            for pattern in page_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    try:
                        pages.add(int(match))
                    except ValueError:
                        pass
            
            # Extract figures and tables
            figure_patterns = [
                r'Figure\s+\d+[^\n]*',
                r'Table\s+\d+[^\n]*',
                r'<figcaption>([^<]+)</figcaption>',
                r'איור\s+\d+[^\n]*',
                r'טבלה\s+\d+[^\n]*'
            ]
            
            for pattern in figure_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                figures.extend(matches)
        
        if pages or figures:
            citations.append({
                "document": doc_name,
                "pages": sorted(list(pages)),
                "figures": figures[:10]  # Limit to first 10 figures
            })
    
    return citations

def generate_enhanced_answer(original_answer, chunks, sources):
    """
    Generate enhanced answer with page numbers, figures, and clickable links
    Similar to test_retrieval.py generate_improved_answer_suggestion
    """
    enhanced_citations = extract_enhanced_citations(chunks)
    
    if not enhanced_citations:
        return original_answer
    
    # Start with original answer
    enhanced_answer = original_answer.rstrip()
    
    # Add period if missing
    if not enhanced_answer.endswith('.'):
        enhanced_answer += '.'
    
    # Add citation details for the main document
    main_citation = enhanced_citations[0]
    doc_name = main_citation["document"]
    pages = main_citation["pages"]
    figures = main_citation["figures"]
    
    # Get document URL from sources
    doc_url = None
    for source in sources:
        if source.get("source_file") == doc_name and source.get("url"):
            doc_url = source["url"]
            break
    
    # Create citation suffix
    citation_parts = []
    if pages:
        page_list = ", ".join(map(str, pages))
        citation_parts.append(f"עמ' {page_list}")
    
    if figures:
        fig_count = len([f for f in figures if "Figure" in f or "Table" in f])
        if fig_count > 0:
            citation_parts.append(f"כולל {fig_count} איורים")
    
    citation_suffix = f" ({', '.join(citation_parts)}, {doc_name})" if citation_parts else f" ({doc_name})"
    
    # Add clickable URL if available
    if doc_url:
        citation_suffix += f" - 📖 פתח מסמך"
    
    enhanced_answer += citation_suffix
    
    # Add figure details if available
    if figures:
        enhanced_answer += "\n\nאיורים וטבלאות:\n"
        for i, fig in enumerate(figures[:5], 1):  # Limit to first 5 figures
            enhanced_answer += f"• {fig}\n"
            
        if len(figures) > 5:
            remaining = len(figures) - 5
            enhanced_answer += f"• ועוד {remaining} איורים נוספים\n"
    
    return enhanced_answer
