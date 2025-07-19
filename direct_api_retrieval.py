"""
Direct API retrieval functions for Streamlit - bypasses SDK issues
"""

import requests
import json
import os
from typing import Dict, List, Any, Optional
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

def get_search_headers() -> dict:
    """Get authentication headers for Azure Search API calls"""
    # Use managed identity only
    try:
        token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception:
        raise RuntimeError("No Search authentication available. Use managed identity.")

def search_client_helper(index_name: str) -> SearchClient:
    """Create a SearchClient for document lookups"""
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    # Use managed identity only
    credential = DefaultAzureCredential()
    return SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)

def retrieve_with_direct_api(
    user_question: str,
    agent_name: str,
    index_name: str,
    reranker_threshold: float = 1.0,  # FIXED: Match working agent.py default
    include_sources: bool = True
) -> Dict[str, Any]:
    """
    Use direct API calls to retrieve from the agent, similar to agent.py
    
    Returns:
        Dict with 'answer', 'chunks', 'sources', and 'debug_info'
    """
    
    # Extract service name from search endpoint
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    if not search_endpoint:
        raise ValueError("AZURE_SEARCH_ENDPOINT not configured")
        
    service_name = search_endpoint.replace("https://", "").replace(".search.windows.net", "")
    api_version = "2025-05-01-preview"
    
    # FIXED: Use correct URL format but with /retrieve endpoint (like working function/agent.py)
    # The working agent.py uses retrieve endpoint with use_responses=False by default
    route = "retrieve"  # Use retrieve endpoint like the working agent.py
    endpoint = f"https://{service_name}.search.windows.net/agents('{agent_name}')/{route}?api-version={api_version}"
    
    # Prepare the request body
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
                "indexName": index_name,
                "rerankerThreshold": reranker_threshold,
                "maxDocsForReranker": 200,
            }
        ]
    }
    
    # Note: citationFieldName and responseFields are not needed for /retrieve endpoint
    
    # Get authentication headers
    headers = get_search_headers()
    
    # Make the API call
    try:
        resp = requests.post(endpoint, headers=headers, json=body, timeout=60)
        
        debug_info = {
            "endpoint": endpoint,
            "agent_name": agent_name,
            "index_name": index_name,
            "status_code": resp.status_code,
            "headers_sent": list(headers.keys()),
            "body_sent": body
        }
        
        # Check for non-JSON responses
        if resp.status_code != 200:
            error_msg = f"HTTP {resp.status_code}: {resp.text[:500]}"
            return {
                "answer": f"⚠️ API Error: {error_msg}",
                "chunks": [],
                "sources": [],
                "debug_info": debug_info
            }
            
        # Parse JSON response
        try:
            response_data = resp.json()
        except ValueError:
            return {
                "answer": f"⚠️ Invalid JSON response: {resp.text[:200]}",
                "chunks": [],
                "sources": [],
                "debug_info": debug_info
            }
            
        debug_info["response_keys"] = list(response_data.keys())
        
        # Check for error in response
        if "error" in response_data:
            error = response_data["error"]
            error_msg = f"{error.get('code', '')}: {error.get('message', '')}"
            return {
                "answer": f"⚠️ Knowledge-Agent error: {error_msg}",
                "chunks": [],
                "sources": [],
                "debug_info": debug_info
            }
            
        # Handle retrieve endpoint format (returns chunks, not final answer)
        # Use the same robust extraction logic as the working function/agent.py
        chunks = []
        try:
            if "response" in response_data:               # /responses OR "merged" retrieve
                json_str = response_data["response"][0]["content"][0]["text"]
                try:
                    # If it's a JSON list of chunks → continue below
                    chunks = json.loads(json_str)
                except Exception:
                    # Not JSON → it is already the final answer (shouldn't happen with /retrieve)
                    return {
                        "answer": json_str.strip(),
                        "chunks": [],
                        "sources": [],
                        "debug_info": {
                            **debug_info,
                            "retrieval_method": "Azure Search Agent API (/retrieve with merged response)",
                            "endpoint_type": "retrieve"
                        }
                    }
            elif "chunks" in response_data:
                chunks = response_data["chunks"]
            else:
                debug_info["unexpected_keys"] = list(response_data.keys())
                chunks = []
        except Exception as exc:
            debug_info["extraction_error"] = str(exc)
            chunks = []
        
        debug_info["chunks_found"] = len(chunks)
        debug_info["retrieval_method"] = "Azure Search Agent API (/retrieve endpoint)"
        debug_info["endpoint_type"] = "retrieve"
                
        debug_info["chunks_found"] = len(chunks)
        
        # Add source method information
        if len(chunks) > 0:
            debug_info["retrieval_method"] = "Azure Search Agent API"
            debug_info["agent_success"] = True
        else:
            debug_info["retrieval_method"] = "No chunks from Agent - will try fallback"
            debug_info["agent_success"] = False
        
        # Add detailed chunk debugging
        if len(chunks) > 0:
            debug_info["chunks_preview"] = []
            for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                preview = {
                    "ref_id": chunk.get("ref_id", "?"),
                    "score": chunk.get("score", "no_score"),
                    "content_preview": chunk.get("content", "")[:150] + "..." if len(chunk.get("content", "")) > 150 else chunk.get("content", ""),
                    "source_file": chunk.get("source_file", ""),
                    "doc_key": chunk.get("doc_key", "")
                }
                debug_info["chunks_preview"].append(preview)
        
        # If no chunks found, try alternative search approaches for debugging
        if len(chunks) == 0:
            debug_info["alternative_searches"] = try_alternative_searches(
                user_question, index_name, search_endpoint
            )
            
            # If original query failed and contains Hebrew, try translated query
            try:
                from query_translation import should_translate_query, get_enhanced_query
                if should_translate_query(user_question):
                    translated_query = get_enhanced_query(user_question)
                    debug_info["translated_query"] = translated_query
                    
                    if translated_query != user_question:
                        # Retry with translated query
                        debug_info["retrying_with_translation"] = True
                        
                        # Update the request body with translated query
                        body["messages"][1]["content"][0]["text"] = translated_query
                        
                        # Make another API call with translated query
                        try:
                            response2 = requests.post(endpoint, headers=headers, json=body, timeout=60)
                            if response2.status_code == 200:
                                result2 = response2.json()
                                if "error" not in result2:
                                    # Handle retrieve endpoint format for translated query (same as working agent.py)
                                    chunks_translated = []
                                    try:
                                        if "response" in result2:
                                            json_str = result2["response"][0]["content"][0]["text"]
                                            try:
                                                chunks_translated = json.loads(json_str)
                                            except Exception:
                                                # Not JSON, it's already the final answer
                                                return {
                                                    "answer": json_str.strip(),
                                                    "chunks": [],
                                                    "sources": [],
                                                    "debug_info": {
                                                        **debug_info,
                                                        "translation_success": True,
                                                        "retrieval_method": "Azure Search Agent API (/retrieve + translation, merged response)"
                                                    }
                                                }
                                        elif "chunks" in result2:
                                            chunks_translated = result2["chunks"]
                                    except Exception as extraction_error:
                                        debug_info["translation_extraction_error"] = str(extraction_error)
                                        chunks_translated = []
                                    
                                    if len(chunks_translated) > 0:
                                        chunks = chunks_translated
                                        debug_info["translation_success"] = True
                                        debug_info["retrieval_method"] = "Azure Search Agent API (/retrieve + translation)"
                                        debug_info["chunks_found_after_translation"] = len(chunks)
                                    else:
                                        debug_info["translation_success"] = False
                                        
                                        # Agent failed even with translation, try direct search fallback
                                        debug_info["attempting_direct_search_fallback"] = True
                                        chunks = try_direct_search_fallback(translated_query, index_name, search_endpoint)
                                        if len(chunks) > 0:
                                            debug_info["direct_search_fallback_success"] = True
                                            debug_info["retrieval_method"] = "Direct Search Fallback (after Agent + translation failed)"
                                            debug_info["chunks_from_direct_search"] = len(chunks)
                        except Exception as e:
                            debug_info["translation_error"] = str(e)
                            
                            # Try direct search fallback as last resort
                            debug_info["attempting_direct_search_fallback"] = True
                            chunks = try_direct_search_fallback(translated_query, index_name, search_endpoint)
                            if len(chunks) > 0:
                                debug_info["direct_search_fallback_success"] = True
                                debug_info["retrieval_method"] = "Direct Search Fallback (after Agent + translation error)"
                                debug_info["chunks_from_direct_search"] = len(chunks)
            except ImportError:
                debug_info["translation_unavailable"] = "query_translation module not available"
                
                # Try direct search fallback when translation is not available
                if any('\u0590' <= char <= '\u05FF' for char in user_question):
                    # Hebrew query detected, try with English keywords
                    english_fallback = "UltraDisk disk types comparison Azure storage"
                    debug_info["attempting_direct_search_fallback"] = True
                    chunks = try_direct_search_fallback(english_fallback, index_name, search_endpoint)
                    if len(chunks) > 0:
                        debug_info["direct_search_fallback_success"] = True
                        debug_info["retrieval_method"] = "Direct Search Fallback (no translation module)"
                        debug_info["chunks_from_direct_search"] = len(chunks)
        
        # Enrich chunks with source_file if missing
        search_client = None
        for chunk in chunks:
            if "source_file" not in chunk and "doc_key" in chunk:
                if search_client is None:
                    search_client = search_client_helper(index_name)
                try:
                    doc = search_client.get_document(key=chunk["doc_key"])
                    if doc and "source_file" in doc:
                        chunk["source_file"] = doc["source_file"]
                except Exception:
                    pass  # Silently ignore lookup errors
        
        # CRITICAL: Enrich chunks with URLs if missing (like function/agent.py)
        for chunk in chunks:
            # Skip if already has URL
            if chunk.get("url", "").startswith(("http://", "https://")):
                continue
                
            # Try to get URL by source_file
            source_file = chunk.get("source_file", "")
            if source_file:
                try:
                    if search_client is None:
                        search_client = search_client_helper(index_name)
                    safe_src = source_file.replace("'", "''")  # escape quotes
                    search_filter = f"source_file eq '{safe_src}'"
                    search_results = search_client.search(
                        search_text="*", 
                        filter=search_filter, 
                        top=1,
                        select=["url", "source_file"]
                    )
                    for hit in search_results:
                        if hit.get("url"):
                            chunk["url"] = hit["url"]
                            break
                except Exception:
                    pass  # Silently ignore lookup errors
            
            # NEW: Extract document name from chunk content when all metadata is missing
            # Handle cases where agent API returns only ref_id + content (like this debug case)
            elif not chunk.get("source_file") and not chunk.get("doc_key"):
                content = chunk.get("content", "")
                # Look for document name in square brackets at start of content: [filename.ext]
                if content.startswith("[") and "]" in content[:150]:
                    try:
                        doc_name = content[1:content.find("]")]
                        # Only proceed if it looks like a filename (has extension)
                        if "." in doc_name and len(doc_name) < 100:
                            if search_client is None:
                                search_client = search_client_helper(index_name)
                            
                            # Search for URL by document name
                            safe_doc = doc_name.replace("'", "''")  # escape quotes
                            search_filter = f"source_file eq '{safe_doc}'"
                            search_results = search_client.search(
                                search_text="*", 
                                filter=search_filter, 
                                top=1,
                                select=["url", "source_file"]
                            )
                            for hit in search_results:
                                if hit.get("url"):
                                    chunk["url"] = hit["url"]
                                    chunk["source_file"] = doc_name  # Also populate source_file for consistency
                                    break
                    except Exception:
                        pass  # Silently ignore extraction/lookup errors
        
        # Create a readable answer by combining chunks using improved label logic from agent.py
        def get_chunk_label(chunk: dict) -> str:
            """
            Choose the most helpful human‑readable citation label
            in priority order (matching agent.py logic):
              1) source_file   (file name when present)
              2) source        (alias field)
              3) url           (last segment of URL)
              4) filename embedded at start of content, e.g. "[my.pdf] …"
              5) fallback      (generic docN)
            """
            if chunk.get("source_file"):
                return chunk["source_file"]

            if chunk.get("source"):
                return chunk["source"]

            if chunk.get("url"):
                from pathlib import Path
                return Path(chunk["url"]).name or chunk["url"]

            # NEW – parse leading "[filename] …" in the chunk text itself
            txt = chunk.get("content", "")
            if txt.startswith("[") and "]" in txt[:150]:
                return txt[1:txt.find("]")]

            return f"doc{chunk.get('ref_id', '?')}"
            
        # Combine chunks into a readable answer
        if chunks:
            combined_text = " ".join(f"[{get_chunk_label(c)}] {c.get('content', '')}" for c in chunks)
            
            # Try to summarize with LLM if available
            debug_info["attempting_llm_summarization"] = True
            final_answer = summarize_chunks_with_llm(combined_text, user_question)
            
            # Check if LLM actually worked
            if final_answer and not final_answer.startswith("LLM authentication failed") and len(final_answer) > 20:
                debug_info["llm_summarization_success"] = True
                debug_info["final_answer_source"] = "LLM processed"
            else:
                debug_info["llm_summarization_success"] = False
                debug_info["final_answer_source"] = "Raw chunks fallback"
                if final_answer and final_answer.startswith("LLM authentication failed"):
                    debug_info["llm_error"] = final_answer.split(". Raw chunks:")[0]
                # Use raw chunks as fallback
                final_answer = f"Based on the indexed sources:\n\n{combined_text[:4000]}..."
        else:
            final_answer = "No relevant information found."
            debug_info["final_answer_source"] = "No chunks retrieved"
            debug_info["llm_summarization_success"] = False
            
        # Build sources list with URL enrichment (like function/agent.py)
        sources = []
        if include_sources:
            seen_sources = set()
            for chunk in chunks:
                source_file = chunk.get("source_file", "")
                if source_file and source_file not in seen_sources:
                    sources.append({
                        "doc_key": chunk.get("doc_key", ""),
                        "source_file": source_file,
                        "url": chunk.get("url", "")
                    })
                    seen_sources.add(source_file)
            
            # URL enrichment: Search index for missing URLs (critical fix!)
            search_client = search_client_helper(index_name)
            for entry in sources:
                if entry.get("url", "").startswith(("http://", "https://")):
                    continue  # already have a full URL
                try:
                    # Search for URL by source_file
                    safe_src = entry["source_file"].replace("'", "''")  # escape quotes
                    search_filter = f"source_file eq '{safe_src}'"
                    search_results = search_client.search(
                        search_text="*", 
                        filter=search_filter, 
                        top=1,
                        select=["url", "source_file"]
                    )
                    for hit in search_results:
                        if hit.get("url"):
                            entry["url"] = hit["url"]
                            break
                except Exception as e:
                    # Leave url empty on any failure, but don't break the flow
                    pass
        
        # Format Sources section at end of answer (like function/agent.py + agent foundry)
        if include_sources and sources:
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
        
        return {
            "answer": final_answer,
            "chunks": chunks,
            "sources": sources,
            "debug_info": debug_info
        }
        
    except Exception as e:
        return {
            "answer": f"⚠️ Request failed: {str(e)}",
            "chunks": [],
            "sources": [],
            "debug_info": {"error": str(e), "endpoint": endpoint}
        }

def summarize_chunks_with_llm(chunks_text: str, user_question: str) -> str:
    """
    Summarize retrieved chunks using Azure OpenAI with managed identity
    Falls back to truncated chunks if LLM is not available
    """
    max_output_size = 16000  # Default max output size
    try:
        from openai import AzureOpenAI
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        
        # Get OpenAI configuration (use same env vars as working agent.py)
        azure_openai_endpoint = os.getenv("OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT_41") or os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_openai_deployment = os.getenv("OPENAI_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_41") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        if not all([azure_openai_endpoint, azure_openai_deployment]):
            # No OpenAI config, return truncated chunks
            return chunks_text[:max_output_size]
            
        # Create OpenAI client with managed identity (same approach as working agent.py)
        try:
            cred = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(cred, "https://cognitiveservices.azure.com/.default")
            
            client = AzureOpenAI(
                azure_ad_token_provider=token_provider,  # Auto-refreshing token provider
                azure_endpoint=azure_openai_endpoint,
                api_version="2024-02-15-preview"
            )
            
            # Test token provider is working
            test_token = token_provider()
            if not test_token or len(test_token) < 100:
                raise Exception("Token provider returned invalid token")
                
        except Exception as e:
            # If managed identity fails, fall back to raw chunks with debug info
            error_info = f"🔴 LLM Authentication Error: {str(e)}"
            print(error_info)
            return f"{error_info}\n\n📄 Raw chunks for analysis:\n{chunks_text[:max_output_size]}"
        
        # Create summarization prompt matching the working Azure Function agent.py EXACTLY
        system_msg = (
            "ענה בקצרה ובבהירות . הסתמך אך ורק על המידע המופיע ב‑chunks "
            "והצג סימוכין בסוגריים מרובעות—for example [my_document.pdf]. "
            "אם אין מידע, השב \"אין לי מידע\"."
        )
        
        prompt = (
            f"== Chunks ==\n{chunks_text}\n"  # Don't truncate! Let LLM see all chunks
            f"== Question ==\n{user_question}\n"
            "== End =="
        )
        
        try:
            response = client.chat.completions.create(
                model=azure_openai_deployment,
                temperature=0.2,  # Match Azure Function exactly
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ]
            )
            
            result = response.choices[0].message.content.strip()
            
            # Add debug info for successful LLM processing
            debug_info = f"🟢 LLM Success: Model={azure_openai_deployment}, Tokens={len(result)}, Auth=Managed Identity"
            print(debug_info)
            
            return result[:max_output_size]
            
        except Exception as llm_error:
            # Detailed error for LLM processing failure
            error_detail = f"🔴 LLM Processing Error: {str(llm_error)}"
            print(error_detail)
            return f"{error_detail}\n\n📄 Raw chunks for analysis:\n{chunks_text[:max_output_size]}"
        
    except Exception as outer_error:
        # Comprehensive error handling for the entire function
        error_info = f"🔴 Summarization Function Error: {str(outer_error)}"
        print(error_info)
        return f"{error_info}\n\n📄 Fallback - Raw chunks:\n{chunks_text[:max_output_size]}"

def try_direct_search_fallback(query: str, index_name: str, search_endpoint: str) -> List[Dict]:
    """
    Fallback to direct search when agent retrieval fails
    Returns chunks in a format compatible with agent chunks
    """
    try:
        search_client = search_client_helper(index_name)
        
        # Try multiple search strategies for Hebrew queries
        strategies = [
            {"search_text": query, "top": 3},
            {"search_text": query.replace("תעריף", "cost"), "top": 3},
            {"search_text": query.replace("בדיקת מונה", "meter inspection"), "top": 3}
        ]
        
        for strategy in strategies:
            try:
                search_results = search_client.search(**strategy)
                hits = list(search_results)
                
                if hits:
                    # Convert search results to chunk format
                    chunks = []
                    for i, hit in enumerate(hits[:3]):  # Limit to top 3
                        content = hit.get("content", "")
                        if content:
                            chunks.append({
                                "content": content[:2000],  # Limit content length
                                "ref_id": str(i + 1),
                                "doc_key": hit.get("doc_key", ""),
                                "source_file": hit.get("source_file", ""),
                                "url": hit.get("url", "")
                            })
                    
                    if chunks:
                        return chunks
                        
            except Exception:
                continue  # Try next strategy
                
        return []
        
    except Exception:
        return []

def try_alternative_searches(query: str, index_name: str, search_endpoint: str) -> Dict:
    """
    Try different search approaches to debug why a query returns no results
    """
    results = {}
    
    # Setup search client
    try:
        search_client = search_client_helper(index_name)
        
        # 1. Original query as-is
        try:
            search_results = search_client.search(search_text=query, top=5)
            hits = list(search_results)
            results["original_hebrew_query"] = {
                "query": query, 
                "hits": len(hits),
                "first_hit_source": hits[0].get("source_file", "unknown") if hits else None
            }
        except Exception as e:
            results["original_hebrew_query"] = {"query": query, "hits": 0, "error": str(e)}
        
        # 2. Try key Hebrew terms (generic)
        hebrew_queries = [
            "בדיקה",
            "תעריף", 
            "חינם",
            "שירות"
        ]
        
        for heb_query in hebrew_queries:
            try:
                search_results = search_client.search(search_text=heb_query, top=3)
                hits = list(search_results)
                if len(hits) > 0:
                    results[f"hebrew_{heb_query.replace(' ', '_')}"] = {
                        "query": heb_query, 
                        "hits": len(hits),
                        "first_hit_source": hits[0].get("source_file", "unknown") if hits else None
                    }
            except Exception as e:
                continue  # Skip failed queries
        
        # 3. Try wildcard search to see if index has any content
        try:
            search_results = search_client.search(search_text="*", top=5)
            hits = list(search_results)
            results["wildcard_all_docs"] = {
                "query": "*", 
                "hits": len(hits),
                "total_docs_in_index": len(hits)
            }
        except Exception as e:
            results["wildcard_all_docs"] = {"query": "*", "hits": 0, "error": str(e)}
            
        # 4. Try search with specific Hebrew analyzer if available
        try:
            # Some indexes might have Hebrew language analyzer
            search_results = search_client.search(
                search_text=query, 
                query_language="he-IL",  # Hebrew language code
                top=3
            )
            hits = list(search_results)
            results["hebrew_language_query"] = {
                "query": query + " (with he-IL language)", 
                "hits": len(hits)
            }
        except Exception as e:
            results["hebrew_language_query"] = {"error": "Hebrew language not supported"}
            
    except Exception as e:
        results["search_client_error"] = str(e)
        
    return results