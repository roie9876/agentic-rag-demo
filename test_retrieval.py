"""
Test Retrieval module - handles the Test Retrieval tab functionality
"""
import os
import json as local_json
import streamlit as st
from typing import Dict, Callable, Any
import traceback

from azure.search.documents.agent.models import (
    KnowledgeAgentRetrievalRequest,
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    KnowledgeAgentIndexParams,
)

# ---------- robust import for KnowledgeAgentRequestLimits ----------
try:
    # Newer SDKs
    from azure.search.documents.agent.models import KnowledgeAgentRequestLimits
except ImportError:                           # pragma: no cover
    try:
        # Some previews expose it one level higher
        from azure.search.documents.agent import KnowledgeAgentRequestLimits  # type: ignore
    except ImportError:
        # Fallback shim for very old builds – keeps the rest of the code working
        class KnowledgeAgentRequestLimits:    # type: ignore
            def __init__(self, max_output_size: int = 6000):
                self.max_output_size = max_output_size
# -------------------------------------------------------------------

def render_test_retrieval_tab(
    tab_test: Any,
    health_block: Callable,
    session_state: dict,
    init_agent_client: Callable,
    init_search_client: Callable,
    env: Callable,
    search_credential_fn: Callable
):
    """
    Render the Test Retrieval tab UI with full functionality
    
    Parameters:
    - tab_test: Streamlit tab container
    - health_block: Health check UI function
    - session_state: Streamlit session state
    - init_agent_client: Function to initialize agent client
    - init_search_client: Function to initialize search client
    - env: Function to fetch environment variables
    - search_credential_fn: Function to get search credentials
    """
    with tab_test:
        health_block()
        st.header("🧪 Test Retrieval Without Foundry")
        if not session_state.selected_index:
            st.info("Select or create an index in the previous tabs.")
        else:
            search_client, _ = init_search_client(session_state.selected_index)

            # History
            for turn in session_state.history:
                with st.chat_message(turn["role"]):
                    st.markdown(f'<div class="ltr">{turn["content"]}</div>', unsafe_allow_html=True)

            user_query = st.chat_input("Ask your question…")
            if user_query:
                session_state.history.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.markdown(f'<div class="ltr">{user_query}</div>', unsafe_allow_html=True)

                agent_name = f"{session_state.selected_index}-agent"
                
                # Try to check if agent exists (note: older SDK versions might not support this)
                try:
                    # Import what we need for agent check
                    from azure.search.documents.aio import SearchServiceClient
                    import asyncio
                    
                    async def check_agent_exists(name):
                        try:
                            cred = search_credential_fn()
                            service_client = SearchServiceClient(
                                endpoint=env("AZURE_SEARCH_ENDPOINT"),
                                credential=cred
                            )
                            # Check if get_agents method exists
                            if hasattr(service_client, 'get_agents'):
                                agents = [a async for a in service_client.get_agents()]
                                agent_names = [a.name for a in agents]
                                await service_client.close()
                                return name in agent_names
                            else:
                                return "Unknown (SDK doesn't support agent listing)"
                        except Exception as e:
                            return f"Error checking: {str(e)}"
                    
                    agent_status = asyncio.run(check_agent_exists(agent_name))
                    if isinstance(agent_status, bool):
                        st.write(f"Agent Check: {'Exists' if agent_status else 'Not Found'} - {agent_name}")
                        if not agent_status:
                            st.warning(f"The agent '{agent_name}' does not exist. You may need to create it first.")
                            st.info("Go to the 'Create Agent' section and create an agent with this name.")
                    else:
                        st.write(f"Agent Status: {agent_status}")
                except Exception as ex:
                    st.write(f"Agent Check: Unable to verify (requires newer SDK)")
                    st.caption(f"If retrieval fails, ensure agent '{agent_name}' exists")
                
                agent_client = init_agent_client(agent_name)
                if not session_state.agent_messages:
                    session_state.agent_messages = [{"role": "assistant", "content": "Answer with sources."}]
                session_state.agent_messages.append({"role": "user", "content": user_query})

                ka_msgs = [
                    KnowledgeAgentMessage(
                        role=m["role"],
                        content=[KnowledgeAgentMessageTextContent(text=m["content"])]
                    )
                    for m in session_state.agent_messages
                ]

                # Create a base request with only the most essential parameters
                ka_req_params = {
                    "messages": ka_msgs,
                    "target_index_params": [
                        # Create index params with only the essential parameters
                        KnowledgeAgentIndexParams(
                            index_name=session_state.selected_index,
                            reranker_threshold=float(session_state.rerank_thr),
                        )
                    ],
                    "request_limits": KnowledgeAgentRequestLimits(
                        max_output_size=int(session_state.max_output_size)
                    )
                }
                
                # Try to add optional parameters that might not be supported in all SDK versions
                try:
                    # Create a test instance to check supported parameters
                    test_req = KnowledgeAgentRetrievalRequest(messages=ka_msgs)
                    
                    # Check if citation_field_name is supported
                    if hasattr(test_req, "citation_field_name"):
                        ka_req_params["citation_field_name"] = "source_file"
                    
                    # Check if response_fields is supported
                    if hasattr(test_req, "response_fields"):
                        ka_req_params["response_fields"] = ["id", "text", "source_file", "url", "doc_key"]
                        
                    # Add any other potentially unsupported parameters here
                except Exception as e:
                    st.caption(f"Note: Some advanced retrieval features may not be available in your SDK version.")
                
                # Create the actual request
                ka_req = KnowledgeAgentRetrievalRequest(**ka_req_params)

                # ── Debug info ─────────────────────────────
                st.markdown("---")
                st.markdown("#### 🐞 Debug Info")
                st.write({
                    "AZURE_SEARCH_ENDPOINT": os.getenv("AZURE_SEARCH_ENDPOINT"),
                    "AZURE_SEARCH_KEY": os.getenv("AZURE_SEARCH_KEY"),
                    "Selected Index": session_state.selected_index,
                    "Auth Mode": "API Key" if os.getenv("AZURE_SEARCH_KEY") else "RBAC",
                    "Request Payload": ka_req.dict() if hasattr(ka_req, 'dict') else str(ka_req)
                })
                st.markdown("---")

                with st.spinner("Retrieving…"):
                    try:
                        # ---------- SDK call: retrieve chunks --------------------
                        # Show the full request for debugging
                        debug_info = {
                            "agent_name": agent_name,
                            "endpoint": os.getenv("AZURE_SEARCH_ENDPOINT"),
                            "credential_type": type(search_credential_fn()).__name__,
                            "messages": [{"role": m.role, "content": [c.text for c in m.content]} for m in ka_msgs],
                            "target_index": ka_req.target_index_params[0].index_name if ka_req.target_index_params else "None",
                            "ka_req_attributes": [attr for attr in dir(ka_req) if not attr.startswith('_')],
                            "applied_parameters": ka_req_params.keys()
                        }
                        
                        # Safely add optional parameters if they exist
                        for param in ["citation_field_name", "response_fields"]:
                            if hasattr(ka_req, param):
                                debug_info[param] = getattr(ka_req, param)
                                
                        st.expander("Debug Request").write(debug_info)
                        
                        result = agent_client.knowledge_retrieval.retrieve(
                            retrieval_request=ka_req
                        )
                        
                        # Debug result structure
                        debug_info = {
                            "result_type": type(result).__name__,
                            "available_attributes": [attr for attr in dir(result) if not attr.startswith('_')],
                        }
                        
                        # Safely add response info if available
                        if hasattr(result, "response"):
                            debug_info["response_count"] = len(result.response)
                            if result.response:
                                debug_info["first_response_type"] = type(result.response[0]).__name__
                                debug_info["first_response_attrs"] = [attr for attr in dir(result.response[0]) if not attr.startswith('_')]
                        
                        # Check for other common attributes
                        for attr in ["chunks", "raw_response", "references"]:
                            debug_info[f"has_{attr}"] = hasattr(result, attr)
                            
                        st.expander("Debug Response").write(debug_info)
                        
                    except Exception as ex:
                        st.error(f"Retrieval failed: {ex}")
                        st.code(traceback.format_exc())
                        st.stop()

                # Build chunks directly from the structured Message → Content objects
                chunks = []
                
                try:
                    # Extract chunks from response structure if available
                    if hasattr(result, "chunks"):
                        # If chunks attribute exists directly, use it
                        raw_chunks = result.chunks
                        for c in raw_chunks:
                            # Convert any objects to dicts by getting their __dict__ if available
                            chunk_dict = {}
                            if hasattr(c, "__dict__"):
                                # Get attributes from object
                                chunk_dict = {k: v for k, v in c.__dict__.items() if not k.startswith('_')}
                            elif isinstance(c, dict):
                                # If it's already a dict, use it directly
                                chunk_dict = c
                            else:
                                # For anything else, try to convert it to a string and use as content
                                chunk_dict = {"content": str(c), "ref_id": len(chunks)}
                                
                            chunks.append(chunk_dict)
                    
                    # If no chunks directly available, extract from response
                    if not chunks and hasattr(result, "response"):
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
                                
                    # If we still don't have chunks, try to extract from raw_response
                    if not chunks and hasattr(result, "raw_response"):
                        try:
                            # Try to parse raw response JSON
                            if isinstance(result.raw_response, str):
                                raw_data = local_json.loads(result.raw_response)
                                if "chunks" in raw_data:
                                    chunks = raw_data["chunks"]
                        except:
                            # Silently continue if parsing fails
                            pass
                            
                    # If still empty, create at least one empty chunk so UI doesn't break
                    if not chunks:
                        chunks = [{"ref_id": 0, "content": "No content retrieved", "source_file": "unknown", "doc_key": "", "url": ""}]
                        
                except Exception as chunk_ex:
                    # If anything goes wrong, ensure we have at least one chunk for the UI
                    st.warning(f"Error parsing chunks: {str(chunk_ex)}")
                    chunks = [{"ref_id": 0, "content": f"Error parsing retrieval results: {str(chunk_ex)}", "source_file": "error", "doc_key": "", "url": ""}]
                
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
                        extracted_src = content[1:content.find('')]
                    
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
                
                # Try direct search to check if index has content
                try:
                    direct_results = search_client.search(search_text=user_query, top=3)
                    direct_hits = [doc for doc in direct_results]
                    st.expander("Direct Search Results").write({
                        "query": user_query,
                        "hits_count": len(direct_hits),
                        "first_hit": direct_hits[0] if direct_hits else "No results found",
                        "index_name": session_state.selected_index
                    })
                except Exception as ex:
                    st.expander("Direct Search Error").write(f"Error performing direct search: {str(ex)}")
                
                # Format each chunk with its source file for better readability
                formatted_chunks = []
                
                for i, c in enumerate(chunks):
                    try:
                        # Step 1: Ensure we're working with a dictionary
                        chunk_dict = c
                        if isinstance(c, str):
                            if c.startswith('{'):
                                try:
                                    chunk_dict = local_json.loads(c)
                                except:
                                    chunk_dict = {"content": c, "ref_id": i}
                            else:
                                chunk_dict = {"content": c, "ref_id": i}
                                
                        # Step 2: Extract source information
                        source = None
                        if isinstance(chunk_dict, dict):
                            source_candidates = ["source_file", "doc_key", "source", "filename"]
                            for field in source_candidates:
                                if field in chunk_dict and chunk_dict[field]:
                                    source = chunk_dict[field]
                                    if isinstance(source, str) and source.endswith('.docx'):
                                        # Found a good filename, stop searching
                                        break
                            
                            if not source:
                                source = f"doc{chunk_dict.get('ref_id', i)}"
                        else:
                            source = f"doc{i}"
                            
                        # Step 3: Extract content
                        content = ""
                        if isinstance(chunk_dict, dict):
                            content = chunk_dict.get("content", str(chunk_dict))
                        else:
                            content = str(chunk_dict)
                                
                        # Step 4: Parse [filename] prefix in content if present
                        if isinstance(content, str) and content.startswith('[') and ']' in content:
                            filename = content[1:content.find('')]
                            if filename and (not source or source.startswith('doc')):
                                source = filename
                            # Remove the prefix from content
                            content = content[content.find(']')+1:].strip()
                        
                        # Step 5: Process escape sequences (like \n) to make content readable
                        if isinstance(content, str):
                            # Process common escape sequences properly
                            try:
                                # Handle common escape sequences
                                content = content.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'")
                                
                                # Handle further nested escapes if present (e.g., JSON within JSON)
                                if '\\\\' in content or '\\u' in content:
                                    # Use the json module to properly unescape Unicode characters
                                    import json as stdlib_json
                                    # Wrap the string in quotes for json.loads to work
                                    # This handles Unicode escape sequences like \u05D0 (Hebrew)
                                    escaped_content = "\"" + content.replace("\"", "\\\"") + "\""
                                    try:
                                        content = stdlib_json.loads(escaped_content)
                                    except:
                                        # If that fails, keep what we have
                                        pass
                            except Exception as decode_ex:
                                st.expander("Debug Decode Error").write(str(decode_ex))
                                
                        # If source is a complex object, simplify it
                        if isinstance(source, dict):
                            # Try to get the source_file from the dictionary
                            source = source.get("source_file", str(source)[:30])
                        elif isinstance(source, str) and source.startswith('{'):
                            # Try to parse JSON string
                            try:
                                source_obj = local_json.loads(source)
                                if isinstance(source_obj, dict):
                                    source = source_obj.get("source_file", source_obj.get("content", "unknown file"))
                                    # If content has a [filename], extract it
                                    if isinstance(source, str) and source.startswith('[') and ']' in source:
                                        source = source[1:source.find('')]
                            except:
                                # If parsing fails, use a simple string
                                source = "unknown file"
                        
                        # Detect Enterprice Chat.docx from the content
                        if isinstance(content, str) and content.find("Enterprice Chat.docx") >= 0:
                            source = "Enterprice Chat.docx"
                                
                        # Clean up source by extracting just the filename if it's a path
                        if source and isinstance(source, str) and ('/' in source or '\\' in source):
                            # Extract just the filename from the path
                            source = os.path.basename(source)
                            
                        # Debug output to help track what's being processed
                        st.expander(f"Debug Chunk {i}").write({
                            "original_type": type(c).__name__,
                            "processed_source": source,
                            "content_preview": content[:100] if isinstance(content, str) else str(content)[:100],
                        })
                            
                        # Format content with proper line breaks for HTML display
                        if isinstance(content, str):
                            # Convert newlines to HTML breaks for proper rendering
                            html_content = content.replace('\n', '<br>')
                            formatted_chunks.append(f"**Source: {source}**\n\n{html_content}\n")
                    except Exception as chunk_ex:
                        # If anything goes wrong with a specific chunk, add error info
                        formatted_chunks.append(f"**Source: Error processing chunk {i}**\n\n{str(chunk_ex)}\nOriginal: {str(c)[:200]}...\n")
                
                answer_text = "\n\n---\n\n".join(formatted_chunks) if chunks else ""
                answer_text = answer_text.strip()
                chunk_count = len(chunks) if chunks else 0

                # Update sidebar diagnostic
                session_state.dbg_chunks = chunk_count

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
                                            # Process escape sequences in chunk content
                                            if isinstance(chunk_content, str):
                                                # Handle common escape sequences
                                                chunk_content = chunk_content.replace('\\n', '\n').replace('\\t', '\t')
                                                
                                                # Handle Unicode escape sequences
                                                if '\\\\' in chunk_content or '\\u' in chunk_content:
                                                    try:
                                                        import json as stdlib_json
                                                        escaped_content = '"' + chunk_content.replace('"', '\\"') + '"'
                                                        chunk_content = stdlib_json.loads(escaped_content)
                                                    except:
                                                        pass
                                                        
                                                # Convert newlines to HTML breaks for proper rendering
                                                html_content = chunk_content.replace('\n', '<br>')
                                                formatted_chunks.append(f"**Source: {src}**\n\n{html_content}")
                                            else:
                                                formatted_chunks.append(f"**Source: {src}**\n\n{chunk_content}")
                                        else:
                                            # Process content without a source too
                                            if isinstance(chunk_content, str):
                                                # Handle common escape sequences
                                                chunk_content = chunk_content.replace('\\n', '\n').replace('\\t', '\t')
                                                
                                                # Convert newlines to HTML breaks for proper rendering
                                                html_content = chunk_content.replace('\n', '<br>')
                                                formatted_chunks.append(html_content)
                                            else:
                                                formatted_chunks.append(str(chunk_content))
                                formatted_answer = "\n\n---\n\n".join(formatted_chunks)
                            elif isinstance(parsed, dict) and 'content' in parsed:
                                formatted_answer = parsed['content']
                        except:
                            # If JSON parsing fails, keep the original text
                            pass
                    
                    # Ensure HTML is rendered properly, especially for line breaks and special characters
                    st.markdown(formatted_answer or "*[לא התקבלה תשובה]*", unsafe_allow_html=True)

                    # Display raw chunks for more in-depth debugging
                    st.expander("Raw Chunks").write(chunks)
                    
                    if sources_data:
                        st.markdown("#### 🗂️ Sources")
                        
                        # First, extract source names from chunks to make sure we catch everything
                        all_sources = []
                        
                        # Add sources from sources_data
                        for src in sources_data:
                            try:
                                # Parse source if it's a string JSON
                                if isinstance(src, str) and src.startswith('{'):
                                    try:
                                        src_dict = local_json.loads(src)
                                    except:
                                        src_dict = {"source_file": src[:100]}
                                elif isinstance(src, dict):
                                    src_dict = src
                                else:
                                    src_dict = {"source_file": str(src)}
                                
                                # Extract name from source object
                                source_name = None
                                
                                # Try standard fields
                                for field in ["source_file", "doc_key", "source", "filename"]:
                                    if field in src_dict and src_dict[field]:
                                        source_name = src_dict[field]
                                        break
                                
                                # If source_file is a JSON string, try to extract filename
                                if isinstance(source_name, str) and source_name.startswith('{'):
                                    try:
                                        name_obj = local_json.loads(source_name)
                                        source_name = name_obj.get("source_file", None)
                                    except:
                                        pass
                                
                                if source_name:
                                    # If source is a path, extract just the filename
                                    if isinstance(source_name, str) and ('/' in source_name or '\\' in source_name):
                                        source_name = os.path.basename(source_name)
                                    
                                    all_sources.append({
                                        "name": source_name, 
                                        "url": src_dict.get("url", "")
                                    })
                            except Exception as e:
                                all_sources.append({"name": f"Error: {str(e)}", "url": ""})
                        
                        # Also extract sources from chunks directly
                        for c in chunks:
                            try:
                                if isinstance(c, dict):
                                    # Get filename from source_file or from content prefix
                                    source_name = None
                                    
                                    # Try standard fields first
                                    for field in ["source_file", "doc_key", "source", "filename"]:
                                        if field in c and c[field]:
                                            source_name = c[field]
                                            break
                                    
                                    # If still no name, check content for [filename] pattern
                                    if not source_name and "content" in c:
                                        content = c.get("content", "")
                                        if isinstance(content, str) and content.startswith('[') and ']' in content:
                                            source_name = content[1:content.find('')].strip()
                                    
                                    if source_name:
                                        # If source is a path, extract just the filename
                                        if isinstance(source_name, str) and ('/' in source_name or '\\' in source_name):
                                            source_name = os.path.basename(source_name)
                                            
                                        all_sources.append({
                                            "name": source_name, 
                                            "url": c.get("url", "")
                                        })
                            except:
                                continue
                        
                        # De-duplicate sources while preserving order
                        displayed_names = set()
                        unique_sources = []
                        
                        for s in all_sources:
                            name = s.get("name", "")
                            if name and name not in displayed_names:
                                displayed_names.add(name)
                                unique_sources.append(s)
                        
                        # Display the sources
                        for s in unique_sources:
                            name = s.get("name", "Unknown")
                            url = s.get("url", "")
                            
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
                                    parsed_itm = local_json.loads(itm)
                                    ref = parsed_itm.get("ref_id", parsed_itm.get("id", '?'))
                                    content = parsed_itm.get("content", "")
                                    
                                    # Process content for better display
                                    if isinstance(content, str):
                                        # Check for [filename] pattern
                                        if content.startswith('[') and ']' in content:
                                            src = content[1:content.find('')]
                                            content = content[content.find(']')+1:].strip()
                                            st.markdown(f"**📄 מקור {ref} - {src}:**")
                                        else:
                                            st.markdown(f"**📄 מקור {ref}:**")
                                        
                                        # Process escape sequences for better display of Hebrew and special chars
                                        import json as stdlib_json
                                        # Handle common escapes first
                                        content = content.replace('\\n', '\n').replace('\\t', '\t')
                                        
                                        # Handle Unicode escape sequences if present
                                        if '\\u' in content:
                                            try:
                                                escaped_content = '"' + content.replace('"', '\\"') + '"'
                                                content = stdlib_json.loads(escaped_content)
                                            except:
                                                pass  # Keep original if this fails
                                    
                                    # Handle content with proper line breaks and special characters
                                    if isinstance(content, str):
                                        # Convert newlines to HTML breaks for proper rendering
                                        html_content = content.replace('\n', '<br>')
                                        st.markdown(html_content, unsafe_allow_html=True)
                                    else:
                                        # Convert newlines to HTML breaks for proper rendering of Hebrew and special chars
                                        if isinstance(content, str):
                                            html_content = content.replace('\n', '<br>')
                                            st.markdown(html_content, unsafe_allow_html=True)
                                        else:
                                            st.write(content)
                                except Exception as ex:
                                    st.warning(f"Error parsing content: {str(ex)[:100]}")
                                    st.write(itm)  # Fallback to raw display
                            else:
                                ref = itm.get("ref_id", itm.get("id", '?'))
                                source = itm.get("source_file", "") or itm.get("doc_key", "")
                                if source:
                                    st.markdown(f"**📄 מקור {ref} - {source}:**")
                                else:
                                    st.markdown(f"**📄 מקור {ref}:**")
                                # Display content with proper line breaks and special characters
                                content = itm.get("content", "")
                                if isinstance(content, str):
                                    # Convert newlines to HTML breaks for proper rendering
                                    html_content = content.replace('\n', '<br>')
                                    st.markdown(html_content, unsafe_allow_html=True)
                                else:
                                    st.write(content)
                            st.markdown("---")

                # ── Raw payload for debugging ───────────────────────────
                if session_state.raw_index_json:
                    with st.expander("📃 מידע גולמי מהאינדקס", expanded=False):
                        try:
                            import json
                            st.json(json.loads(session_state.raw_index_json))
                        except Exception:
                            st.code(session_state.raw_index_json)
