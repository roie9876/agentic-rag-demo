def agentic_retrieval(agent_name: str, index_name: str, messages: list[dict]) -> str:
    """
    Direct API retrieval from knowledge agent using managed identity authentication.
    מבצע שליפה סוכנתית (Agentic Retrieval) באמצעות API ישיר עם managed identity.
    """
    import requests
    from azure.identity import DefaultAzureCredential
    
    print(f"[agentic_retrieval] DEBUG: Starting direct API retrieval with agent_name='{agent_name}', index_name='{index_name}'")
    print(f"[agentic_retrieval] DEBUG: Messages received: {messages}")
    
    # Extract query from messages (use the last user message)
    query = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            query = msg.get("content", "")
            break
        elif isinstance(msg, str):
            query = msg
            break
    
    if not query:
        print("[agentic_retrieval] DEBUG: No query found in messages")
        return "[]"
    
    print(f"[agentic_retrieval] DEBUG: Extracted query: {query}")
    
    try:
        # Get managed identity token for Azure Search
        credential = DefaultAzureCredential()
        token = credential.get_token("https://search.azure.com/.default")
        
        # Build the knowledge agent API URL
        search_endpoint = env("AZURE_SEARCH_ENDPOINT")
        api_version = env("API_VERSION", "2025-05-01-preview")
        url = f"{search_endpoint}/indexes('{index_name}')/knowledgeAgents('{agent_name}')/search?api-version={api_version}"
        
        # Prepare headers with managed identity token
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        # Prepare request payload
        payload = {
            "query": query,
            "top": int(env("TOP_K", "5"))
        }
        
        print(f"[agentic_retrieval] DEBUG: Making API call to: {url}")
        print(f"[agentic_retrieval] DEBUG: Payload: {payload}")
        
        # Make the API call
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"[agentic_retrieval] DEBUG: Response status: {response.status_code}")
        
        if response.status_code == 200:
            result_data = response.json()
            print(f"[agentic_retrieval] DEBUG: Response received: {type(result_data)}")
            
            # Extract chunks from the response
            chunks = []
            if isinstance(result_data, dict) and "chunks" in result_data:
                raw_chunks = result_data["chunks"]
                print(f"[agentic_retrieval] DEBUG: Found {len(raw_chunks)} chunks")
                
                for i, chunk in enumerate(raw_chunks):
                    if isinstance(chunk, dict):
                        processed_chunk = {
                            "ref_id": chunk.get("ref_id", i),
                            "content": chunk.get("content", ""),
                            "url": chunk.get("url"),
                            "source_file": chunk.get("source_file"),
                            "page_number": chunk.get("page_number"),
                            "score": chunk.get("score"),
                            "doc_key": chunk.get("doc_key"),
                        }
                        # Remove None values
                        processed_chunk = {k: v for k, v in processed_chunk.items() if v is not None}
                        chunks.append(processed_chunk)
            else:
                print(f"[agentic_retrieval] DEBUG: Unexpected response format: {result_data}")
            
            print(f"[agentic_retrieval] DEBUG: Total processed chunks: {len(chunks)}")
            if chunks:
                print(f"[agentic_retrieval] DEBUG: First chunk preview: {str(chunks[0])[:200]}...")
            
            result_json = json.dumps(chunks, ensure_ascii=False)
            print(f"[agentic_retrieval] DEBUG: Returning JSON: {result_json[:300]}...")
            return result_json
            
        else:
            error_msg = f"Knowledge agent API call failed with status {response.status_code}: {response.text}"
            print(f"[agentic_retrieval] ERROR: {error_msg}")
            return "[]"
            
    except Exception as e:
        error_msg = f"Error in agentic retrieval: {str(e)}"
        print(f"[agentic_retrieval] ERROR: {error_msg}")
        return "[]"
