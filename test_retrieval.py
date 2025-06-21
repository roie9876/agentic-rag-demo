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
                        # ---------- Direct API call instead of SDK --------------------
                        from direct_api_retrieval import retrieve_with_direct_api
                        
                        # Use direct API approach that bypasses SDK issues
                        api_result = retrieve_with_direct_api(
                            user_question=user_query,
                            agent_name=agent_name,
                            index_name=session_state.selected_index,
                            reranker_threshold=float(session_state.rerank_thr),
                            max_output_size=int(session_state.max_output_size),
                            include_sources=True
                        )
                        
                        # Extract results
                        answer = api_result.get("answer", "No answer received")
                        chunks = api_result.get("chunks", [])
                        sources = api_result.get("sources", [])
                        debug_info = api_result.get("debug_info", {})
                        
                        # Show debug info
                        st.expander("Debug API Call").write(debug_info)
                        
                        # Check if we got an error
                        if answer.startswith("⚠️"):
                            st.error(f"API call failed: {answer}")
                            st.stop()
                            
                    except Exception as ex:
                        st.error(f"Direct API retrieval failed: {ex}")
                        st.code(traceback.format_exc())
                        st.stop()

                # Sources are already processed by our direct API function
                sources_data = sources
                
                # ---------- Display the answer -------------------------------
                # Debug chunk data
                st.expander("Debug Chunks Data").json(chunks)
                
                # Try direct search to check if index has content
                direct_hits = []
                try:
                    search_client, _ = init_search_client(session_state.selected_index)
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

                # Update sidebar diagnostic
                session_state.dbg_chunks = len(chunks)

                # ---------- Render assistant answer ------------------------------
                with st.chat_message("assistant"):
                    # If agent returned no useful answer but we have direct search results, provide fallback
                    if (not chunks or len(chunks) == 0 or answer == "No relevant information found.") and direct_hits:
                        st.warning("הסוכן לא מצא תוצאות, אך נמצא תוכן רלוונטי בחיפוש ישיר:")
                        
                        # Create a fallback answer from direct search results
                        fallback_content = []
                        for hit in direct_hits[:2]:  # Show top 2 results
                            content = hit.get("content", "")[:500]  # Limit content length
                            source_file = hit.get("source_file", "מסמך לא ידוע")
                            if content:
                                fallback_content.append(f"**[{source_file}]**\n{content}")
                        
                        if fallback_content:
                            st.markdown("\n\n".join(fallback_content))
                        else:
                            st.markdown(answer or "*[לא התקבלה תשובה]*", unsafe_allow_html=True)
                    else:
                        # Display the formatted answer from our direct API
                        st.markdown(answer or "*[לא התקבלה תשובה]*", unsafe_allow_html=True)
                
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
                                    
                                    # Check for and display images from multimodal content
                                    related_images = parsed_itm.get("relatedImages", [])
                                    image_captions = parsed_itm.get("imageCaptions", "")
                                    if related_images:
                                        display_images_from_blob_storage(related_images, image_captions, env)
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
                                
                                # Check for and display images from multimodal content
                                related_images = itm.get("relatedImages", [])
                                image_captions = itm.get("imageCaptions", "")
                                if related_images:
                                    display_images_from_blob_storage(related_images, image_captions, env)
                            st.markdown("---")

                # ── Raw payload for debugging ───────────────────────────
                if session_state.raw_index_json:
                    with st.expander("📃 מידע גולמי מהאינדקס", expanded=False):
                        try:
                            import json
                            st.json(json.loads(session_state.raw_index_json))
                        except Exception:
                            st.code(session_state.raw_index_json)

# -------------------------------------------------------------------

def display_images_from_blob_storage(related_images, image_captions, env_fn):
    """
    Display images from Azure Blob Storage based on relatedImages field.
    
    Parameters:
    - related_images: List of image identifiers from the relatedImages field
    - image_captions: String containing image captions
    - env_fn: Function to get environment variables
    """
    if not related_images or len(related_images) == 0:
        return
        
    try:
        # Get blob storage configuration
        connection_string = env_fn("AZURE_STORAGE_CONNECTION_STRING")
        container_name = env_fn("AZURE_STORAGE_CONTAINER")
        
        if not connection_string or not container_name:
            st.warning("🔧 Azure Blob Storage not configured. Cannot display images.")
            return
            
        # Try to import Azure Storage
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            st.warning("📦 Azure Storage SDK not available. Cannot display images.")
            return
            
        # Initialize blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        st.markdown("### 🖼️ Images from Document")
        
        if image_captions:
            st.markdown(f"**Image Captions:** {image_captions}")
        
        # Display images in columns for better layout
        cols = st.columns(min(len(related_images), 3))  # Max 3 columns
        
        for i, image_id in enumerate(related_images):
            with cols[i % 3]:
                try:
                    # Check if blob exists
                    blob_client = container_client.get_blob_client(image_id)
                    if blob_client.exists():
                        # Get the blob URL
                        image_url = blob_client.url
                        
                        # Display the image
                        st.image(image_url, caption=f"Figure {i+1}: {image_id}", use_column_width=True)
                        
                        # Add a link to view the image in full size
                        st.markdown(f"[View Full Size]({image_url})")
                    else:
                        st.warning(f"Image not found: {image_id}")
                        
                except Exception as img_err:
                    st.warning(f"Error loading image {image_id}: {str(img_err)}")
                    
    except Exception as e:
        st.error(f"Error accessing blob storage: {str(e)}")

# -------------------------------------------------------------------
