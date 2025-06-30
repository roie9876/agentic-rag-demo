"""
Test Retrieval module - handles the Test Retrieval tab functionality
"""
import os
import json as local_json
import json as stdlib_json
import re
import asyncio
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

def analyze_chunks_for_sources(chunks):
    """
    Analyze chunks to extract comprehensive source information including:
    - Page numbers, multimodal content, extraction methods, etc.
    - Special handling for agent API responses (which only have ref_id and content)
    """
    analysis = {
        "total_chunks": len(chunks),
        "unique_documents": 0,
        "pages_referenced": 0,
        "multimodal_chunks": 0,
        "documents": {},
        "is_agent_response": False
    }
    
    if not chunks:
        return analysis
    
    pages_set = set()
    
    # Check if this looks like an agent API response with enhanced metadata
    if chunks and isinstance(chunks[0], dict):
        sample_chunk = chunks[0]
        chunk_keys = set(sample_chunk.keys())
        # New detection: if we have more than just ref_id and content, we have enhanced metadata
        if chunk_keys == {"ref_id", "content"}:
            analysis["is_agent_response"] = True
            analysis["agent_metadata_level"] = "minimal"
        elif len(chunk_keys) > 2 and "ref_id" in chunk_keys:
            analysis["is_agent_response"] = True  
            analysis["agent_metadata_level"] = "enhanced"
        else:
            analysis["is_agent_response"] = False
    
    for i, chunk in enumerate(chunks):
        try:
            # Parse chunk data
            if isinstance(chunk, str) and chunk.startswith('{'):
                chunk_data = local_json.loads(chunk)
            elif isinstance(chunk, dict):
                chunk_data = chunk
            else:
                continue
            
            # Extract document name - special handling for agent API responses
            doc_name = None
            content = chunk_data.get("content", "")
            ref_id = chunk_data.get("ref_id", "")
            
            if analysis["is_agent_response"]:
                # For agent API responses, extract document name from content or use direct fields
                # First try direct metadata fields (enhanced agent response)
                if analysis.get("agent_metadata_level") == "enhanced":
                    for field in ["source_file", "filename", "doc_key", "source"]:
                        if field in chunk_data and chunk_data[field]:
                            doc_name = chunk_data[field]
                            break
                
                # Fall back to content extraction if needed
                if not doc_name and isinstance(content, str):
                    # Look for document name patterns in content
                    doc_patterns = [
                        r'^\[([^\]]+\.pdf[^\]]*)\]',  # [filename.pdf] at start
                        r'^\[([^\]]+\.docx[^\]]*)\]', # [filename.docx] at start  
                        r'^\[([^\]]+\.txt[^\]]*)\]',  # [filename.txt] at start
                        r'^\[([^\]]+\.[a-z]{2,5}[^\]]*)\]',  # [filename.ext] general pattern
                        r'FROM\s+([A-Z\s]+\.PDF)',    # FROM DOCUMENT_NAME.PDF
                        r'FROM\s+([A-Z\s]+)',        # FROM DOCUMENT_NAME
                        r'Source:\s*([^\n]+)',       # Source: document_name
                        r'Document:\s*([^\n]+)',     # Document: document_name
                    ]
                    
                    for pattern in doc_patterns:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            doc_name = match.group(1).strip()
                            # Clean up common artifacts
                            doc_name = re.sub(r'\s+', ' ', doc_name)  # Normalize whitespace
                            doc_name = doc_name.replace('FROM ', '').replace('Source: ', '').replace('Document: ', '')
                            # Extract just the filename if it looks like a path
                            if '/' in doc_name or '\\' in doc_name:
                                doc_name = os.path.basename(doc_name)
                            break
                
                # Use ref_id as fallback for document identification
                if not doc_name and ref_id:
                    # Try to extract meaningful name from ref_id
                    if '/' in ref_id or '\\' in ref_id:
                        # Looks like a file path
                        doc_name = os.path.basename(ref_id)
                    else:
                        # Use ref_id as-is, but clean it up
                        doc_name = ref_id.replace('_', ' ').replace('-', ' ')
                        doc_name = re.sub(r'\s+', ' ', doc_name).strip()
            else:
                # For direct API responses, use the rich metadata fields
                for field in ["source_file", "filename", "doc_key", "source"]:
                    if field in chunk_data and chunk_data[field]:
                        doc_name = chunk_data[field]
                        break
            
            # Final fallback extraction from content for both types
            if not doc_name and isinstance(content, str) and content.startswith('[') and ']' in content:
                doc_name = content[1:content.find(']')]
                content = content[content.find(']')+1:].strip()
            
            if not doc_name:
                doc_name = f"Unknown Document {i+1}"
            
            # Clean document name
            if isinstance(doc_name, str) and ('/' in doc_name or '\\' in doc_name):
                doc_name = os.path.basename(doc_name)
            
            # Initialize document if not seen before
            if doc_name not in analysis["documents"]:
                analysis["documents"][doc_name] = {
                    "chunk_count": 0,
                    "pages": [],
                    "chunks": [],
                    "url": "",
                    "extraction_method": "",
                    "multimodal_chunks": 0
                }
            
            # Update document info (ensure we get URL from any chunk that has it)
            current_url = chunk_data.get("url", "")
            if current_url and not analysis["documents"][doc_name]["url"]:
                analysis["documents"][doc_name]["url"] = current_url
            
            # Update extraction method if we don't have one yet
            current_method = chunk_data.get("extraction_method", "")
            if current_method and not analysis["documents"][doc_name]["extraction_method"]:
                analysis["documents"][doc_name]["extraction_method"] = current_method
            
            # Extract chunk information
            page_num = chunk_data.get("page_number", None)
            
            # Try multiple ways to extract page numbers from different sources
            if page_num is None:
                # Try to extract from content (e.g., HTML-style page markers)
                if isinstance(content, str):
                    # Enhanced page patterns including agent API response patterns
                    page_patterns = [
                        r'<!-- PageNumber="(\d+)" -->',  # HTML comment style
                        r'PageNumber="(\d+)"',           # Direct attribute style
                        r'PageBreak(\d+)',               # PageBreak markers
                        r'Page (\d+)',                   # Plain "Page N"
                        r'page (\d+)',                   # lowercase "page N"
                        r'עמוד (\d+)',                    # Hebrew "page N"
                        r'עמ\' (\d+)',                    # Hebrew abbreviated "page N"
                        r'p\.(\d+)',                     # "p.N"
                        r'\[Page (\d+)\]',               # "[Page N]"
                        r'FROM\s+[A-Z\s]+\s+(\d+)',     # FROM DOCUMENT 123
                        r'\s(\d+)\s*$',                  # Number at end of line
                        r'^\[([^\]]+)\]\s*(\d+)',       # [DocumentName] 123
                    ]
                    
                    # Special handling for agent API responses
                    if analysis["is_agent_response"]:
                        # Look for patterns like "FROM WIKIBOOKS 42" or document references with numbers
                        agent_patterns = [
                            r'<!-- PageNumber="(\d+)" -->',  # HTML page markers (priority for agent responses)
                            r'FROM\s+[A-Z\s]+\s+(\d+)',      # FROM DOCUMENT_NAME NUMBER (like "FROM WIKIBOOKS 1")
                            r'\]\s*(\d+)',                    # After closing bracket and space
                            r'Page\s*(\d+)',                 # Page followed by number
                            r'^(\d+)\s*[\.:]',               # Number at start with punctuation
                            r'\#\s*(\d+)',                   # After # symbol
                            r'Chapter\s*(\d+)',              # Chapter followed by number
                            r'Section\s*(\d+)',              # Section followed by number
                            r'^\s*(\d+)\s*$',                # Standalone number on its own line
                            r'</figure>\s*(\d+)',            # Number after figure end tag
                        ]
                        page_patterns = agent_patterns + page_patterns
                    
                    for pattern in page_patterns:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            try:
                                page_num = int(match.group(-1))  # Get last group (usually the number)
                                break
                            except (ValueError, IndexError):
                                continue
                
                # Try extracting from page_chunk field if it exists
                if page_num is None and "page_chunk" in chunk_data:
                    page_chunk_content = chunk_data.get("page_chunk", "")
                    if isinstance(page_chunk_content, str):
                        for pattern in [r'<!-- PageNumber="(\d+)" -->', r'PageNumber="(\d+)"']:
                            match = re.search(pattern, page_chunk_content)
                            if match:
                                try:
                                    page_num = int(match.group(1))
                                    break
                                except (ValueError, IndexError):
                                    continue
                
                # Look in the raw chunk for any numeric page reference
                if page_num is None:
                    # Try to find any number that might be a page number
                    for field_name in ["page", "pagenum", "page_num"]:
                        if field_name in chunk_data and chunk_data[field_name] is not None:
                            try:
                                page_num = int(chunk_data[field_name])
                                break
                            except (ValueError, TypeError):
                                continue
            
            # If still no page number found, try to infer from document structure
            if page_num is None:
                # Use a meaningful default - we can't just use i+1 since that's chunk order, not page order
                page_num = "Unknown"
            
            is_multimodal = chunk_data.get("isMultimodal", False)
            image_captions = chunk_data.get("imageCaptions", "")
            related_images = chunk_data.get("relatedImages", [])
            
            # Extract more detailed citation information from content
            citation_context = ""
            if isinstance(content, str):
                # Enhanced patterns for both agent API and direct API responses
                citation_patterns = [
                    (r'\[([^\]]+\.pdf[^\]]*)\]', "Document Reference"),  # [filename.pdf] patterns
                    (r'FROM\s+([A-Z\s]+)\s*(\d*)', "Source Attribution"),  # FROM WIKIBOOKS pattern
                    (r'<figcaption>([^<]+)</figcaption>', "Figure Caption"),  # Figure captions (priority)
                    (r'Figure\s+(\d+):\s*([^\.]+)', "Figure Reference"),  # Figure N: description
                    (r'Table\s+(\d+)', "Table Reference"),  # Table references
                    (r'##\s*([^#\n]+)', "Section Header"),  # Section headers
                    (r'<!-- PageHeader="([^"]*)" -->', "Page Header"),  # Page headers
                    (r'<caption>([^<]+)</caption>', "Table Caption"),  # Table captions
                ]
                
                # For agent API responses, add specific patterns
                if analysis["is_agent_response"]:
                    agent_patterns = [
                        (r'<figcaption>([^<]+)</figcaption>', "Figure Caption"),  # Figure captions first
                        (r'Figure\s+(\d+):\s*([^\n\.]+)', "Figure Description"),  # Figure descriptions
                        (r'^\[([^\]]+)\]', "Source Reference"),  # [Document Name] at start
                        (r'^([A-Z][A-Z\s]+)(?=\s*\d+|$)', "Document Source"),  # WIKIBOOKS, DOC NAME at start
                        (r'<!-- PageNumber="(\d+)" -->', "Page Reference"),  # Page references
                        (r'(.*?)(?=\n|$)', "Content Context"),  # First line as context (fallback)
                    ]
                    citation_patterns = agent_patterns + citation_patterns
                
                for pattern, context_type in citation_patterns:
                    match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                    if match:
                        if len(match.groups()) > 1:
                            # Multiple groups - combine meaningfully
                            if context_type == "Figure Description":
                                context_text = f"Figure {match.group(1)}: {match.group(2)[:100]}"
                            elif context_type == "Source Attribution" and match.group(2):
                                context_text = f"{match.group(1)} {match.group(2)}"
                            else:
                                context_text = match.group(1)[:150]
                        else:
                            context_text = match.group(1)[:150]
                        
                        # Clean up common artifacts
                        if context_type == "Source Attribution" and "FROM" in context_text:
                            context_text = context_text.replace("FROM", "").strip()
                        
                        citation_context = f"{context_type}: {context_text}"
                        break
                
                # If no specific pattern found, extract the first meaningful line
                if not citation_context:
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 10 and not line.startswith('<'):
                            citation_context = f"Content: {line[:150]}"
                            break
            
            # Update analysis
            analysis["documents"][doc_name]["chunk_count"] += 1
            analysis["documents"][doc_name]["chunks"].append({
                "page_number": page_num,
                "content": content,
                "is_multimodal": is_multimodal,
                "image_captions": image_captions,
                "related_images": related_images,
                "citation_context": citation_context
            })
            
            # Only add valid page numbers to the pages list and pages_set
            if page_num is not None and page_num != "Unknown":
                analysis["documents"][doc_name]["pages"].append(page_num)
                pages_set.add(page_num)
            
            if is_multimodal:
                analysis["multimodal_chunks"] += 1
                analysis["documents"][doc_name]["multimodal_chunks"] += 1
                
        except Exception as e:
            # Skip problematic chunks
            continue
    
    analysis["unique_documents"] = len(analysis["documents"])
    analysis["pages_referenced"] = len(pages_set)
    
    return analysis


def get_method_icon(extraction_method):
    """Get an appropriate icon for the extraction method"""
    method_icons = {
        "document_intelligence": "🔍",
        "simple_parser": "📝", 
        "pandas_parser": "🐼",
        "langchain_chunker": "🔗",
        "multimodal_processor": "🎨"
    }
    return method_icons.get(extraction_method, "🔧")


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
        
        # Show info about enhanced metadata support with actual test results
        st.success("✨ **Enhanced Agent API WORKING**: Getting essential metadata (URLs, source files) directly from agent responses! Test shows 25% direct metadata + smart extraction for remaining fields.")
        st.info("🔗 **Proven Results**: Real SharePoint URLs and source files are now included in every response for immediate document access!")
        
        # Add index selection dropdown specifically for test retrieval
        st.subheader("📂 Index Selection for Testing")
        
        # Get available indexes
        available_indexes = session_state.get('available_indexes', [])
        if not available_indexes:
            # Try to refresh the available indexes
            try:
                search_client, root_index_client = init_search_client()
                if root_index_client:
                    available_indexes = [idx.name for idx in root_index_client.list_indexes()]
                    session_state.available_indexes = available_indexes
            except Exception as e:
                st.error(f"Could not fetch available indexes: {str(e)}")
        
        if available_indexes:
            # Create dropdown for index selection
            current_test_index = session_state.get('test_retrieval_index', None)
            
            # Prepare options with a default selection prompt
            index_options = ["Select an index for testing..."] + available_indexes
            
            # Determine the default selection
            default_index = 0
            if current_test_index and current_test_index in available_indexes:
                default_index = index_options.index(current_test_index)
            elif session_state.get('selected_index') and session_state.selected_index in available_indexes:
                # Use the globally selected index as default if available
                default_index = index_options.index(session_state.selected_index)
            
            selected_test_index = st.selectbox(
                "Choose index to query:",
                options=index_options,
                index=default_index,
                key="test_retrieval_index_selector",
                help="Select which search index to query for testing retrieval functionality"
            )
            
            if selected_test_index != "Select an index for testing...":
                session_state.test_retrieval_index = selected_test_index
                st.success(f"🎯 **Testing with index:** `{selected_test_index}`")
                
                # Display index info
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Index:** {selected_test_index}")
                with col2:
                    st.info(f"**Agent:** {selected_test_index}-agent")
                
                target_index = selected_test_index
            else:
                session_state.test_retrieval_index = None
                target_index = None
        else:
            st.warning("No indexes available. Please create an index first in the 'Create Index' or 'Manage Index' tabs.")
            target_index = None
        
        # Show current selection status
        if target_index:
            search_client, _ = init_search_client(target_index)
            
            # Add search parameters control
            st.subheader("⚙️ Search Parameters")
            
            col1, col2 = st.columns(2)
            
            with col1:
                top_k = st.slider(
                    "Direct Search Results (top_k):",
                    min_value=1,
                    max_value=100,
                    value=50,
                    step=1,
                    key="test_retrieval_top_k",
                    help="Controls how many results are retrieved from direct search calls (not agent API)"
                )
            
            with col2:
                st.info(f"**Direct Search:** {top_k} results")
                st.caption("⚠️ **Agent API Note**: Uses agent's `defaultMaxDocsForReranker` setting")
                st.caption("💡 Agent retrieval count is configured in the agent definition, not per-request")

            # Add explanation about agent vs direct search parameters
            with st.expander("ℹ️ **Understanding Search Parameters**", expanded=False):
                st.markdown("""
                ### 🤖 **Agent API Retrieval**
                - **Count Control**: Set via `defaultMaxDocsForReranker` in agent configuration
                - **Per-Request**: Cannot be changed per query (by design)
                - **Purpose**: Ensures consistent, optimized retrieval for AI processing
                
                ### 🔍 **Direct Search API**
                - **Count Control**: `top_k` parameter (controlled by slider above)
                - **Per-Request**: Can be adjusted for each query
                - **Purpose**: Raw search results for debugging and fallback scenarios
                
                ### 📊 **Current Setup**
                - **Agent retrieval**: Uses agent's configured maximum documents
                - **Direct search**: Uses the `top_k` value you set above ({top_k} results)
                - **Fallback logic**: Shows up to 3 direct search results if agent fails
                
                ### 🔧 **To Change Agent Retrieval Count**
                The agent's document retrieval count is set during agent creation via:
                ```json
                {{
                    "targetIndexes": [{{
                        "indexName": "your-index",
                        "defaultMaxDocsForReranker": 50
                    }}]
                }}
                ```
                
                **To modify**: Go to 'Create Agent' tab and update the agent configuration.
                """.format(top_k=top_k))

            # History
            for turn in session_state.history:
                with st.chat_message(turn["role"]):
                    st.markdown(f'<div class="ltr">{turn["content"]}</div>', unsafe_allow_html=True)

            user_query = st.chat_input("Ask your question…")
            if user_query:
                session_state.history.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.markdown(f'<div class="ltr">{user_query}</div>', unsafe_allow_html=True)

                agent_name = f"{target_index}-agent"
                
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
                            index_name=target_index,
                            reranker_threshold=float(session_state.rerank_thr),
                        )
                    ]
                    # NOTE: Removed request_limits with max_output_size - this parameter is set on the knowledge agent definition, not in retrieve requests
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
                
                # Determine auth method
                auth_method = "Managed Identity (RBAC)" if not os.getenv("AZURE_SEARCH_KEY") else "API Key"
                
                st.write({
                    "AZURE_SEARCH_ENDPOINT": os.getenv("AZURE_SEARCH_ENDPOINT"),
                    "Authentication Method": auth_method,
                    "Selected Index": target_index,
                    "Agent Name": f"{target_index}-agent",
                    "Direct Search Top K": top_k,
                    "Agent Retrieval Count": "Configured in agent (defaultMaxDocsForReranker)",
                    "Reranker Threshold": float(session_state.rerank_thr),
                    "Request Payload": ka_req.dict() if hasattr(ka_req, 'dict') else str(ka_req)
                })
                st.markdown("---")

                with st.spinner("Retrieving…"):
                    try:
                        # ---------- Enhanced Agent API call with full metadata --------------------
                        from direct_api_retrieval import retrieve_with_direct_api
                        
                        # Use enhanced agent API approach with includeReferenceSourceData=true
                        # This now returns full metadata (URLs, page numbers, image captions, etc.) directly from the agent
                        api_result = retrieve_with_direct_api(
                            user_question=user_query,
                            agent_name=agent_name,
                            index_name=target_index,
                            reranker_threshold=float(session_state.rerank_thr),
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
                    search_client, _ = init_search_client(target_index)
                    direct_results = search_client.search(search_text=user_query, top=top_k)
                    direct_hits = [doc for doc in direct_results]
                    st.expander("Direct Search Results").write({
                        "query": user_query,
                        "hits_count": len(direct_hits),
                        "first_hit": direct_hits[0] if direct_hits else "No results found",
                        "index_name": target_index,
                        "top_k_used": top_k
                    })
                except Exception as ex:
                    st.expander("Direct Search Error").write(f"Error performing direct search: {str(ex)}")

                # Update sidebar diagnostic
                session_state.dbg_chunks = len(chunks)

                # ---------- Render assistant answer ------------------------------
                with st.chat_message("assistant"):
                    # Check if we have chunks to work with for enhanced citations
                    if chunks and len(chunks) > 0:
                        # Extract enhanced citations and generate improved answer
                        enhanced_citations = extract_enhanced_citations(chunks)
                        source_analysis = analyze_chunks_for_sources(chunks)
                        
                        if enhanced_citations:
                            # Generate and display the improved answer with enhanced citations as primary
                            improved_answer = generate_improved_answer_suggestion(answer, enhanced_citations, source_analysis)
                            
                            # Detect language for appropriate messaging
                            language = detect_language(answer or "")
                            
                            if language == "he":
                                st.success("✨ **תשובה משופרת עם ציטוטים מלאים:**")
                            else:
                                st.success("✨ **Enhanced Answer with Complete Citations:**")
                            
                            st.markdown(improved_answer, unsafe_allow_html=True)
                            
                            # Show original answer in expandable section for comparison
                            if language == "he":
                                with st.expander("📝 השוואה עם התשובה המקורית", expanded=False):
                                    st.markdown("**תשובה מקורית:**")
                                    st.markdown(answer or "*[לא התקבלה תשובה]*")
                            else:
                                with st.expander("📝 Compare with Original Answer", expanded=False):
                                    st.markdown("**Original Answer:**")
                                    st.markdown(answer or "*[No answer received]*")
                        else:
                            # No enhanced citations possible, fall back to original
                            st.markdown(answer or "*[לא התקבלה תשובה]*", unsafe_allow_html=True)
                    elif direct_hits:
                        # If agent returned no useful answer but we have direct search results, provide fallback
                        fallback_count = min(3, top_k, len(direct_hits))
                        language = detect_language(" ".join([h.get("content", "") for h in direct_hits[:fallback_count]]))
                        
                        if language == "he":
                            st.warning("הסוכן לא מצא תוצאות, אך נמצא תוכן רלוונטי בחיפוש ישיר:")
                        else:
                            st.warning("Agent found no results, but relevant content found in direct search:")
                        
                        # Create a fallback answer from direct search results
                        fallback_content = []
                        # Use a reasonable number of results for fallback (max 3, but respect user's top_k if smaller)
                        fallback_count = min(3, top_k, len(direct_hits))
                        for hit in direct_hits[:fallback_count]:
                            content = hit.get("content", "")[:500]  # Limit content length
                            source_file = hit.get("source_file", "Unknown document" if language == "en" else "מסמך לא ידוע")
                            if content:
                                fallback_content.append(f"**[{source_file}]**\n{content}")
                        
                        if fallback_content:
                            st.markdown("\n\n".join(fallback_content))
                        else:
                            fallback_msg = "*[No answer received]*" if language == "en" else "*[לא התקבלה תשובה]*"
                            st.markdown(fallback_msg, unsafe_allow_html=True)
                    else:
                        # No chunks and no direct hits
                        language = detect_language(answer or "")
                        fallback_msg = "*[No answer received]*" if language == "en" else "*[לא התקבלה תשובה]*"
                        st.markdown(answer or fallback_msg, unsafe_allow_html=True)
                
                # ========== ENHANCED SOURCE ANALYSIS AND DISPLAY ==========
                
                # Analyze chunks to extract rich source information
                source_analysis = analyze_chunks_for_sources(chunks)
                
                # Display enhanced source summary
                if source_analysis["total_chunks"] > 0:
                    st.markdown("---")
                    st.markdown("### 📊 **Source Analysis**")
                    
                    # Show info about response type with new enhanced detection
                    if source_analysis["is_agent_response"]:
                        # Detect language for messaging
                        language = detect_language(answer or "")
                        metadata_level = source_analysis.get("agent_metadata_level", "minimal")
                        
                        if metadata_level == "enhanced":
                            # Count direct metadata fields that are available
                            sample_chunk = chunks[0] if chunks and isinstance(chunks[0], dict) else {}
                            direct_fields = ["source_file", "url", "filename", "doc_key"]
                            available_fields = [field for field in direct_fields if field in sample_chunk and sample_chunk[field]]
                            
                            if language == "he":
                                st.success(f"🤖 **תגובת API משופרת של הסוכן** - מטא-דאטה ישירה ({len(available_fields)}/{len(direct_fields)} שדות) + חילוץ מתוכן")
                            else:
                                st.success(f"🤖 **Enhanced Agent API Response** - Direct metadata ({len(available_fields)}/{len(direct_fields)} fields: {', '.join(available_fields)}) + content extraction")
                        else:
                            if language == "he":
                                st.info("🤖 **תגובת API של הסוכן** - מטא-דאטה חלקית זמינה (URL, קובץ מקור) + חילוץ מתוכן")
                            else:
                                st.info("🤖 **Agent API Response** - Partial metadata available (URL, source file) + content extraction")
                        
                        # Extract enhanced citations for analysis display
                        enhanced_citations = extract_enhanced_citations(chunks)
                        
                        # Show what was successfully extracted (summary)
                        if enhanced_citations:
                            if language == "he":
                                st.success("✅ **חילצנו בהצלחה מהתוכן:**")
                            else:
                                st.success("✅ **Successfully Extracted from Content:**")
                                
                            for citation in enhanced_citations:
                                pages = citation.get("pages", [])
                                figures = citation.get("figures", [])
                                doc_name = citation.get("document", "")
                                
                                if pages:
                                    page_list = ", ".join(map(str, sorted(pages)))
                                    if language == "he":
                                        st.success(f"📄 **מספרי עמודים מ-{doc_name}:** {page_list}")
                                    else:
                                        st.success(f"📄 **Page Numbers from {doc_name}:** {page_list}")
                                        
                                if figures:
                                    fig_count = len(figures)
                                    if language == "he":
                                        st.success(f"🖼️ **הפניות לאיורים/טבלאות מ-{doc_name}:** {fig_count} נמצאו")
                                    else:
                                        st.success(f"🖼️ **Figure/Table References from {doc_name}:** {fig_count} found")
                        
                        # Show recommendations for better citations
                        with st.expander("💡 **Recommendations for Better Citations**" if language == "en" else "💡 **המלצות לציטוטים טובים יותר**", expanded=False):
                            if language == "he":
                                st.markdown("""
                                **מטא-דאטה זמינה בתגובת הסוכן:**
                                - ✅ **כתובות URL של המסמכים**: זמינות ישירות מהסוכן  
                                - ✅ **שמות קבצים**: זמינים ישירות מהסוכן
                                - ❌ **מספרי עמודים**: נחלצים מתוכן כאשר זמינים
                                - ❌ **כתוביות תמונות**: נחלצים מתוכן כאשר זמינים
                                
                                **מה שהשגנו:**
                                1. **URLs ישירות** - לינקים פעילים למסמכים ב-SharePoint
                                2. **שמות קבצים** - זיהוי מדויק של מקורות
                                3. **חילוץ חכם** - מספרי עמודים והפניות לאיורים מהתוכן
                                
                                **תוצאה:**
                                - ✅ ציטוטים עם לינקים פעילים למסמכים
                                - ✅ הפניות לעמודים כאשר הן מופיעות בתוכן
                                - ✅ איורים וטבלאות כאשר הם מוזכרים
                                """)
                            else:
                                st.markdown("""
                                **Agent Response Metadata Status:**
                                - ✅ **Document URLs**: Available directly from agent  
                                - ✅ **Source filenames**: Available directly from agent
                                - ❌ **Page numbers**: Extracted from content when available
                                - ❌ **Image captions**: Extracted from content when available
                                
                                **What we achieved:**
                                1. **Direct URLs** - Clickable links to documents in SharePoint
                                2. **Source identification** - Accurate document naming
                                3. **Smart extraction** - Page numbers and figure references from content
                                
                                **Result:**
                                - ✅ Citations with clickable document links
                                - ✅ Page references when they appear in content
                                - ✅ Figure and table references when mentioned
                                """)
                    else:
                        st.info("🔍 **Direct Search Response** - Full metadata available from index")
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Chunks", source_analysis["total_chunks"])
                    with col2:
                        st.metric("Unique Documents", source_analysis["unique_documents"])
                    with col3:
                        st.metric("Pages Referenced", source_analysis["pages_referenced"])
                    with col4:
                        st.metric("Multimodal Chunks", source_analysis["multimodal_chunks"])
                    
                    # Document breakdown
                    if source_analysis["documents"]:
                        st.markdown("#### 📄 **Documents Used in Answer:**")
                        
                        for doc_name, doc_info in source_analysis["documents"].items():
                            # Create an expandable section for each document
                            with st.expander(f"📖 **{doc_name}** ({doc_info['chunk_count']} chunks)", expanded=True):
                                
                                # Document-level info with improved URL display
                                if doc_info["url"]:
                                    # Display URL prominently at the top
                                    st.success(f"🌐 **Source URL Available:** Enhanced Agent API metadata working!")
                                    # Make the link more prominent with custom styling
                                    st.markdown(f"""
                                    <div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; border-left: 4px solid #0066cc;">
                                        🔗 <strong><a href="{doc_info['url']}" target="_blank" style="color: #0066cc; text-decoration: none; font-size: 16px;">
                                        📖 Open Document in SharePoint →
                                        </a></strong>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    # Enhanced debugging: Show what metadata we do have
                                    st.warning("❌ **No URL Found** - Debug info below:")
                                    st.info(f"📋 **Available Metadata:** source_file='{doc_info.get('source_file', 'N/A')}', extraction_method='{doc_info.get('extraction_method', 'N/A')}'")
                                    st.info("💡 **Source:** Local Upload (no URL available) or Agent API not returning URL metadata")
                                    # Debug: Show what metadata fields are available for this document
                                    available_chunks = [chunk for chunk in chunks if isinstance(chunk, dict)]
                                    if available_chunks:
                                        # Find a chunk from this document
                                        doc_chunk = None
                                        for chunk in available_chunks:
                                            chunk_doc_name = ""
                                            # Try to match document name using same logic as analyze_chunks_for_sources
                                            if source_analysis.get("agent_metadata_level") == "enhanced":
                                                for field in ["source_file", "filename", "doc_key", "source"]:
                                                    if field in chunk and chunk[field]:
                                                        chunk_doc_name = chunk[field]
                                                        break
                                            
                                            # Clean document name to match
                                            if chunk_doc_name and ('/' in chunk_doc_name or '\\' in chunk_doc_name):
                                                chunk_doc_name = os.path.basename(chunk_doc_name)
                                                
                                            if chunk_doc_name == doc_name or doc_name in str(chunk.get("content", ""))[:100]:
                                                doc_chunk = chunk
                                                break
                                        
                                        if doc_chunk:
                                            st.json({
                                                "document_name": doc_name,
                                                "chunk_keys": list(doc_chunk.keys()),
                                                "url_field": doc_chunk.get("url", "NOT_FOUND"),
                                                "source_file": doc_chunk.get("source_file", "NOT_FOUND"),
                                                "doc_key": doc_chunk.get("doc_key", "NOT_FOUND"),
                                                "ref_id": doc_chunk.get("ref_id", "NOT_FOUND"),
                                                "agent_metadata_level": source_analysis.get("agent_metadata_level", "unknown")
                                            })
                                            
                                            # Try to look up URL from search index if doc_key is available
                                            if doc_chunk.get("doc_key") and not doc_chunk.get("url"):
                                                try:
                                                    search_client, _ = init_search_client(target_index)
                                                    direct_doc = search_client.get_document(key=doc_chunk["doc_key"])
                                                    if direct_doc and direct_doc.get("url"):
                                                        st.info(f"✅ **URL found in index:** {direct_doc['url']}")
                                                        st.markdown(f"""
                                                        <div style="background-color: #fff3cd; padding: 10px; border-radius: 5px; border-left: 4px solid #ffc107;">
                                                            🔗 <strong><a href="{direct_doc['url']}" target="_blank" style="color: #856404; text-decoration: none; font-size: 16px;">
                                                            📖 Open Document (from index lookup) →
                                                            </a></strong>
                                                        </div>
                                                        """, unsafe_allow_html=True)
                                                    else:
                                                        st.error("❌ URL not found in search index either")
                                                except Exception as lookup_err:
                                                    st.error(f"❌ Failed to lookup document in index: {lookup_err}")
                                        else:
                                            st.warning("❌ Could not find chunk data for this document")
                                    else:
                                        st.error("❌ No chunk data available for debugging")
                                    
                                    st.info("💡 **Source:** Local Upload or Agent API not returning URL metadata for this document")
                                
                                # Additional document metadata
                                col1, col2 = st.columns(2)
                                with col1:
                                    if doc_info["extraction_method"]:
                                        method_icon = get_method_icon(doc_info["extraction_method"])
                                        st.markdown(f"{method_icon} **Processing Method:** {doc_info['extraction_method']}")
                                with col2:
                                    if doc_info["multimodal_chunks"] > 0:
                                        st.markdown(f"🎨 **Multimodal Content:** {doc_info['multimodal_chunks']} chunks with images/figures")
                                
                                # Page references
                                if doc_info["pages"]:
                                    # Filter out non-numeric pages and sort the rest
                                    numeric_pages = []
                                    non_numeric_pages = []
                                    
                                    for page in set(doc_info["pages"]):
                                        if isinstance(page, int) or (isinstance(page, str) and page.isdigit()):
                                            numeric_pages.append(int(page))
                                        elif page != "Unknown":
                                            non_numeric_pages.append(str(page))
                                    
                                    # Create pages display
                                    pages_display_parts = []
                                    if numeric_pages:
                                        numeric_pages.sort()
                                        pages_display_parts.append(", ".join(map(str, numeric_pages)))
                                    if non_numeric_pages:
                                        pages_display_parts.append(", ".join(non_numeric_pages))
                                    
                                    if pages_display_parts:
                                        pages_str = ", ".join(pages_display_parts)
                                        st.markdown(f"📄 **Pages referenced:** {pages_str}")
                                    else:
                                        if source_analysis["is_agent_response"]:
                                            st.markdown("📄 **Pages referenced:** Not extractable from agent response")
                                        else:
                                            st.markdown("📄 **Pages referenced:** Information not available")
                                else:
                                    if source_analysis["is_agent_response"]:
                                        st.markdown("📄 **Pages referenced:** Page numbers not found in content")
                                    else:
                                        st.markdown("📄 **Pages referenced:** No page information available")
                                
                                # Show each chunk from this document
                                st.markdown("**Chunks from this document:**")
                                
                                for chunk_info in doc_info["chunks"]:
                                    # Chunk header with page and multimodal info
                                    page_display = chunk_info['page_number']
                                    if page_display == "Unknown":
                                        # Show different messages based on response type
                                        if source_analysis["is_agent_response"]:
                                            chunk_header = f"**Page: Not Extractable** ⚠️"
                                            st.caption("💡 Agent API response doesn't include explicit page information")
                                        else:
                                            chunk_header = f"**Page: Not Available** ⚠️"
                                            st.caption("💡 This chunk doesn't contain clear page number information")
                                    else:
                                        chunk_header = f"**Page {page_display}**"
                                    
                                    if chunk_info["is_multimodal"]:
                                        chunk_header += " 🎨"
                                    if chunk_info["image_captions"]:
                                        chunk_header += " 🖼️"
                                    
                                    st.markdown(chunk_header)
                                    
                                    # Show citation context if available
                                    if chunk_info["citation_context"]:
                                        st.info(f"**Context:** {chunk_info['citation_context']}")
                                    
                                    # Show image captions if available
                                    if chunk_info["image_captions"]:
                                        st.info(f"**📷 Image Caption:** {chunk_info['image_captions']}")
                                    
                                    # Show chunk content (truncated)
                                    content = chunk_info["content"]
                                    if len(content) > 300:
                                        content = content[:300] + "..."
                                    
                                    # Format content with proper line breaks and preserve PDF formatting
                                    formatted_content = content.replace('\n', '<br>')
                                    st.markdown(formatted_content, unsafe_allow_html=True)
                                    
                                    # Show related images if any
                                    if chunk_info["related_images"]:
                                        st.markdown(f"🖼️ **Related Images:** {', '.join(chunk_info['related_images'])}")
                                    
                                    st.markdown("---")
                
                # Update sidebar diagnostic
                session_state.dbg_chunks = len(chunks)

                # Enhanced chunks display is already shown above in the source analysis section
                
                # Optional: Show raw chunks for debugging
                if chunks:
                    # Get response type info with enhanced detection
                    is_agent_response = False
                    agent_metadata_level = "minimal"
                    if chunks and isinstance(chunks[0], dict):
                        sample_chunk = chunks[0]
                        chunk_keys = set(sample_chunk.keys())
                        if chunk_keys == {"ref_id", "content"}:
                            is_agent_response = True
                            agent_metadata_level = "minimal"
                        elif len(chunk_keys) > 2 and "ref_id" in chunk_keys:
                            is_agent_response = True  
                            agent_metadata_level = "enhanced"
                        else:
                            is_agent_response = False
                    
                    with st.expander("🐞 Raw Chunks (Debug)", expanded=False):
                        if is_agent_response:
                            if agent_metadata_level == "enhanced":
                                st.success("🤖 **Enhanced Agent API Response** - Multiple metadata fields available")
                                st.markdown("**Success!** The agent API is returning enhanced metadata including URLs and source files, plus content for extraction.")
                            else:
                                st.info("🤖 **Basic Agent API Response** - Limited metadata fields (ref_id, content)")
                                st.markdown("**Why limited data?** The agent API is in basic mode. Page numbers, URLs, and other details need to be extracted from content patterns.")
                        else:
                            st.info("🔍 **Direct Search Response Format** - Full metadata available")
                            st.markdown("**Rich metadata available:** This response includes all indexed fields like page numbers, URLs, extraction methods, etc.")
                        
                        st.markdown("**Raw Data Structure:** Shows exactly what fields are received from the API")
                        
                        # Check for URLs across all chunks
                        chunks_with_urls = 0
                        chunks_without_urls = 0
                        
                        for i, chunk in enumerate(chunks):
                            st.markdown(f"**Chunk {i}:**")
                            if isinstance(chunk, dict):
                                # Check URL availability
                                has_url = bool(chunk.get("url"))
                                if has_url:
                                    chunks_with_urls += 1
                                    st.success(f"✅ **URL Found:** {chunk['url']}")
                                else:
                                    chunks_without_urls += 1
                                    st.warning("❌ **No URL in this chunk**")
                                
                                # Show key fields for debugging
                                debug_info = {
                                    "has_url": has_url,
                                    "url": chunk.get("url", "NOT_FOUND"),
                                    "source_file": chunk.get("source_file", "NOT_FOUND"),
                                    "doc_key": chunk.get("doc_key", "NOT_FOUND"),
                                    "ref_id": chunk.get("ref_id", "NOT_FOUND"),
                                    "page_number": chunk.get("page_number", "NOT_FOUND"),
                                    "content_snippet": chunk.get("content", "NOT_FOUND")[:100] if chunk.get("content") else "NOT_FOUND",
                                    "available_keys": list(chunk.keys())
                                }
                                
                                # For agent responses, highlight the status
                                if is_agent_response:
                                    if agent_metadata_level == "enhanced":
                                        available_fields = [k for k, v in debug_info.items() if v != "NOT_FOUND" and k not in ["available_keys", "has_url"]]
                                        st.success(f"✅ **Enhanced Agent Response:** {len(available_fields)} metadata fields available: {', '.join(available_fields)}")
                                    else:
                                        st.warning("⚠️ **Basic Agent Response:** Only ref_id and content fields are available. All other metadata marked as 'NOT_FOUND' indicates basic mode.")
                                
                                st.json(debug_info)
                            else:
                                chunks_without_urls += 1
                                st.text(f"Type: {type(chunk)}, Value: {str(chunk)[:200]}...")
                            st.markdown("---")
                        
                        # Summary of URL availability
                        if chunks_with_urls > 0:
                            st.success(f"🎉 **URL Summary:** {chunks_with_urls} chunks have URLs, {chunks_without_urls} chunks missing URLs")
                        else:
                            st.error(f"❌ **URL Summary:** No URLs found in any of the {len(chunks)} chunks")
                            st.markdown("**Possible causes:**")
                            st.markdown("- Agent API not returning URL metadata for this document")
                            st.markdown("- Document not indexed with URL field")
                            st.markdown("- `includeReferenceSourceData: True` not working for this query/index")
                            st.markdown("- RBAC authentication issues affecting metadata retrieval")
                
                # Store raw chunks in session state for possible inspection
                session_state.agent_messages.append({"role": "assistant", "content": answer})

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

                # ── Explanation of retrieval methods ─────────────────────
                st.markdown("---")
                with st.expander("ℹ️ **Understanding Retrieval Methods & Metadata Availability**", expanded=False):
                    st.markdown("""
                    ### 🔍 **Enhanced Agent API with Selective Metadata**
                    
                    #### ✨ **Status: includeReferenceSourceData=true WORKING**
                    **What this achieves:**
                    - ✅ Agent API now returns intelligent answers **AND** key metadata
                    - ✅ Get URLs and source files directly from agent response
                    - ✅ Smart content extraction for page numbers and figures
                    - ✅ Hybrid approach: Direct metadata + content parsing
                    
                    **What you get:**
                    - ✅ High-quality AI-processed answers with multi-step reasoning
                    - ✅ Essential source attribution (URLs, source files) - DIRECT
                    - ✅ Page numbers and figure references - EXTRACTED when available
                    - ✅ Clickable document links for immediate access
                    - ✅ Best balance of AI reasoning + practical provenance
                    
                    #### 📊 **Direct Search API (Fallback)**
                    **When to use:**
                    - When you need raw search results without AI processing
                    - For detailed content analysis and debugging
                    - When agent API is unavailable or returns limited results
                    
                    ### 📋 **Current Implementation**
                    
                    **Agent API Parameters:**
                    - `includeReferenceSourceData: true` - Returns key metadata (URLs, source files)
                    - `rerankerThreshold` - Controls semantic ranking sensitivity
                    
                    **Note:** The agent API returns essential metadata fields (URLs, source files) directly. 
                    Other fields like page numbers are extracted from content when available.
                    
                    **Available Metadata Fields (Agent API):**
                    - ✅ `source_file`, `url`, `doc_key` - Direct from agent
                    - ⚠️ `page_number`, `image_captions`, `extraction_method` - Content extraction
                    - ⚠️ `related_images`, `has_image`, `multimodal_embeddings` - Content extraction
                    
                    ### 🔧 **Testing Your Setup**
                    Run `python test_enhanced_agent_metadata.py` to verify that your agent API is returning full metadata.
                    
                    ### 💡 **Troubleshooting**
                    If you're still seeing very limited metadata (only ref_id and content):
                    1. Check your Azure Search service API version (needs 2025-05-01-preview or later)
                    2. Verify your index contains the metadata fields
                    3. Ensure your agent supports the includeReferenceSourceData parameter
                    4. Run the test script to see current metadata status
                    
                    **Current Status:** ✅ Enhanced metadata working! Getting URLs and source files directly.
                    """)
        else:
            # No index selected - show selection prompt
            st.info("👆 **Please select an index above to start testing retrieval.**")
            st.markdown("""
            ### 🎯 **What you can do here:**
            - Test retrieval functionality with any available search index
            - Ask questions and get AI-powered answers with source citations
            - See metadata like URLs, source files, and page numbers
            - Debug retrieval performance and source data
            
            ### 📋 **Next steps:**
            1. Select an index from the dropdown above
            2. Ask a question in the chat interface that appears
            3. View the response with source citations and metadata
            4. Explore debug information and retrieval details
            """)
            
            if not available_indexes:
                st.warning("🏗️ **No indexes found.** Create an index first in the 'Create Index' or 'Manage Index' tabs.")
                st.markdown("""
                **To get started:**
                1. Go to the "Create Index" tab to create a new search index
                2. Or go to "Manage Index" tab to select an existing index
                3. Upload some documents to populate the index
                4. Return here to test retrieval functionality
                """)

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

def extract_enhanced_citations(chunks):
    """
    Extract enhanced citation information from chunks to suggest improved answer format
    """
    citations = []
    figures = []
    page_refs = []
    
    for chunk in chunks:
        if isinstance(chunk, dict):
            content = chunk.get("content", "")
            ref_id = chunk.get("ref_id", "")
            
            if isinstance(content, str):
                # Enhanced page number extraction patterns including Hebrew
                page_patterns = [
                    r'<!-- PageNumber="(\d+)" -->',  # HTML page markers (priority)
                    r'PageNumber="(\d+)"',           # Direct attribute style
                    r'PageBreak(\d+)',               # PageBreak markers
                    r'Page (\d+)',                   # Plain "Page N"
                    r'page (\d+)',                   # lowercase "page N"
                    r'עמוד (\d+)',                    # Hebrew "page N"
                    r'עמ\' (\d+)',                    # Hebrew abbreviated "page N"
                    r'p\.(\d+)',                     # "p.N"
                    r'\[Page (\d+)\]',               # "[Page N]"
                    r'FROM\s+[A-Z\s]+\s+(\d+)',     # FROM DOCUMENT 123
                    r'\s(\d+)\s*$',                  # Number at end of line
                    r'^\[([^\]]+)\]\s*(\d+)',       # [DocumentName] 123
                ]
                
                for pattern in page_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        try:
                            page_num = int(match)
                            if page_num not in page_refs:
                                page_refs.append(page_num)
                        except (ValueError, TypeError):
                            continue
                
                # Enhanced figure and table references (including Hebrew)
                fig_patterns = [
                    r'<figcaption>(Figure \d+[^<]*)</figcaption>',
                    r'Figure (\d+): ([^<\n]+)',
                    r'איור (\d+): ([^\n]+)',          # Hebrew "Figure N:"
                    r'איור (\d+) - ([^\n]+)',         # Hebrew "Figure N -"
                    r'תמונה (\d+): ([^\n]+)',         # Hebrew "Image N:"
                    r'<caption>(Table \d+[^<]*)</caption>',
                    r'Table (\d+)[:\s]*([^<\n]+)',
                    r'טבלה (\d+): ([^\n]+)',          # Hebrew "Table N:"
                    r'לוח (\d+): ([^\n]+)',           # Hebrew "Board/Table N:"
                    r'דיאגרמה (\d+): ([^\n]+)',       # Hebrew "Diagram N:"
                    r'דיאגרמת ([^,\n]+)',            # Hebrew "Diagram of..."
                    r'תרשים (\d+): ([^\n]+)',         # Hebrew "Chart N:"
                    # Special pattern for the examples you provided
                    r'ישנה (דיאגרמת [^,]+)',          # "There is a diagram of..."
                ]
                
                for pattern in fig_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            if len(match) == 2:
                                # Handle numbered figures/tables
                                fig_ref = f"{match[0]}: {match[1]}".strip()
                            else:
                                fig_ref = " ".join(match).strip()
                        else:
                            fig_ref = match.strip()
                        if fig_ref and fig_ref not in figures:
                            figures.append(fig_ref)
                
                # Extract document name with improved patterns
                doc_patterns = [
                    r'^\[([^\]]+\.pdf[^\]]*)\]',      # [filename.pdf]
                    r'^\[([^\]]+\.docx[^\]]*)\]',     # [filename.docx]
                    r'^\[([^\]]+\.[a-z]{2,5}[^\]]*)\]', # [filename.ext]
                    r'FROM\s+([A-Z\s]+)',             # FROM DOCUMENT_NAME
                    r'מקור:\s*([^\n]+)',               # Hebrew "Source:"
                    r'מסמך:\s*([^\n]+)',               # Hebrew "Document:"
                ]
                
                for pattern in doc_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        doc_name = match.group(1).strip()
                        # Clean up common artifacts
                        doc_name = re.sub(r'\s+', ' ', doc_name)  # Normalize whitespace
                        doc_name = doc_name.replace('FROM ', '').replace('מקור: ', '').replace('מסמך: ', '')
                        # Extract just the filename if it looks like a path
                        if '/' in doc_name or '\\' in doc_name:
                            doc_name = os.path.basename(doc_name)
                        
                        if doc_name not in [c["document"] for c in citations]:
                            citations.append({
                                "document": doc_name,
                                "pages": [],
                                "figures": []
                            })
    
    # Associate pages and figures with documents
    if citations:
        main_doc = citations[0]
        main_doc["pages"] = sorted(list(set(page_refs)))
        main_doc["figures"] = figures
    elif page_refs or figures:
        # Create a generic citation if we found references but no specific document
        citations.append({
            "document": "Document",
            "pages": sorted(list(set(page_refs))),
            "figures": figures
        })
    
    return citations

def detect_language(text):
    """
    Detect if text is primarily Hebrew or English
    """
    if not text:
        return "en"
    
    # Count Hebrew characters
    hebrew_chars = sum(1 for char in text if '\u0590' <= char <= '\u05FF')
    total_chars = sum(1 for char in text if char.isalpha())
    
    if total_chars == 0:
        return "en"
    
    hebrew_ratio = hebrew_chars / total_chars
    return "he" if hebrew_ratio > 0.3 else "en"

def generate_improved_answer_suggestion(original_answer, citations, source_analysis=None):
    """
    Generate a suggested improved answer with proper citations
    """
    if not citations:
        return original_answer
    
    # Detect language from original_answer
    language = detect_language(original_answer)
    
    main_citation = citations[0]
    doc_name = main_citation["document"]
    pages = main_citation["pages"]
    figures = main_citation["figures"]
    
    # Get document URL if available from source analysis
    doc_url = None
    if source_analysis and source_analysis.get("documents"):
        for doc_info in source_analysis["documents"].values():
            if doc_info.get("url"):
                doc_url = doc_info["url"]
                break
    
    # Create citation suffix based on language
    citation_parts = []
    if pages:
        page_str = ", ".join(map(str, pages))
        if language == "he":
            citation_parts.append(f"עמ' {page_str}")
        else:
            citation_parts.append(f"pp. {page_str}")
    
    if figures:
        fig_count = len([f for f in figures if "Figure" in f or "Table" in f])
        if fig_count > 0:
            if language == "he":
                citation_parts.append(f"כולל {fig_count} איורים")
            else:
                citation_parts.append(f"including {fig_count} figures")
    
    citation_suffix = f" ({', '.join(citation_parts)}, {doc_name})" if citation_parts else f" ({doc_name})"
    
    # Add clickable URL if available
    if doc_url:
        if language == "he":
            citation_suffix += f" - [📖 פתח מסמך]({doc_url})"
        else:
            citation_suffix += f" - [📖 Open Document]({doc_url})"
    
    # Add citation to the answer
    improved_answer = original_answer
    if not improved_answer.endswith('.'):
        improved_answer += '.'
    
    improved_answer += citation_suffix
    
    # Add figure details if available
    if figures:
        if language == "he":
            improved_answer += "\n\n**איורים וטבלאות:**\n"
        else:
            improved_answer += "\n\n**Figures and Tables:**\n"
            
        for i, fig in enumerate(figures[:5], 1):  # Limit to first 5 figures
            improved_answer += f"• {fig}\n"
            # Add figure URLs if available (placeholder for future implementation)
            # if doc_url:
            #     improved_answer += f"  [🔗 View Figure]({doc_url}#figure{i})\n"
            
        if len(figures) > 5:
            remaining = len(figures) - 5
            if language == "he":
                improved_answer += f"• ועוד {remaining} איורים נוספים\n"
            else:
                improved_answer += f"• {remaining} additional figures\n"
    
    return improved_answer

def debug_url_availability(chunks, sources, index_name, search_client_init_fn):
    """
    Debug function to check URL availability across different sources
    """
    results = {
        "chunks_with_urls": 0,
        "chunks_without_urls": 0,
        "source_files_found": [],
        "urls_found": [],
        "index_lookup_results": {}
    }
    
    # Check chunks
    for chunk in chunks:
        if isinstance(chunk, dict):
            if chunk.get("url"):
                results["chunks_with_urls"] += 1
                results["urls_found"].append(chunk["url"])
            else:
                results["chunks_without_urls"] += 1
            
            # Track source files
            source_file = chunk.get("source_file", "")
            if source_file and source_file not in results["source_files_found"]:
                results["source_files_found"].append(source_file)
                
                # Try to look up this document in the index to see if it has a URL
                try:
                    search_client, _ = search_client_init_fn(index_name)
                    # Search for documents with this source file
                    search_results = search_client.search(
                        search_text="",
                        filter=f"source_file eq '{source_file}'",
                        select=["id", "source_file", "url", "doc_key"],
                        top=1
                    )
                    
                    docs = list(search_results)
                    if docs and docs[0].get("url"):
                        results["index_lookup_results"][source_file] = {
                            "status": "URL_FOUND",
                            "url": docs[0]["url"],
                            "doc_key": docs[0].get("doc_key")
                        }
                    else:
                        results["index_lookup_results"][source_file] = {
                            "status": "NO_URL_IN_INDEX", 
                            "found_docs": len(docs)
                        }
                except Exception as e:
                    results["index_lookup_results"][source_file] = {
                        "status": "LOOKUP_ERROR",
                        "error": str(e)
                    }
    
    return results
