"""
Index Management Service
========================
Handles Azure Search index creation, management, and agentic retrieval operations.
"""
from typing import List, Tuple, Dict, Any
import os
import logging
from pathlib import Path

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchableField, SimpleField,
    HnswAlgorithmConfiguration, VectorSearch, VectorSearchAlgorithmConfiguration,
    VectorSearchProfile, AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters, SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearch, LexicalAnalyzer, StopwordsList,
    KnowledgeAgent, KnowledgeAgentAzureOpenAIModel,
    KnowledgeAgentTargetIndex, KnowledgeAgentRequestLimits
)
from azure.search.documents import SearchClient
from openai import AzureOpenAI

from utils.azure_helpers import env


class IndexService:
    """Service for managing Azure Search indexes and agentic retrieval."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_agentic_rag_index(self, index_client: SearchIndexClient, name: str) -> bool:
        """
        Create (or recreate) an index + knowledge-agent with API key for Azure OpenAI.
        """
        try:
            # ----------- Basic settings -----------------
            azure_openai_endpoint = env("AZURE_OPENAI_ENDPOINT_41")
            embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
            embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
            VECTOR_DIM = 3072
            # Resolve OpenAI key – prefer suffix _41, fall back to generic
            openai_api_key = os.getenv("AZURE_OPENAI_KEY_41") or os.getenv("AZURE_OPENAI_KEY") or ""

            # ----------- Vectorizer with api_key -----------
            vec_params = AzureOpenAIVectorizerParameters(
                resource_url=azure_openai_endpoint,
                deployment_name=embedding_deployment,
                model_name=embedding_model,
                api_key=openai_api_key,
            )

            index_schema = SearchIndex(
                name=name,
                fields=[
                    SearchField(name="id", type="Edm.String", key=True, filterable=True, sortable=True, facetable=True),
                    SearchableField(name="page_chunk", type="Edm.String", analyzer_name="standard.lucene"),
                    SearchField(
                        name="page_embedding_text_3_large",
                        type="Collection(Edm.Single)",
                        stored=False,
                        vector_search_dimensions=VECTOR_DIM,
                        vector_search_profile_name="hnsw_text_3_large",
                    ),
                    SimpleField(name="page_number", type="Edm.Int32", filterable=True, sortable=True, facetable=True),
                    SimpleField(name="source_file", type="Edm.String", filterable=True, facetable=True),
                    SimpleField(name="source", type="Edm.String", filterable=True, facetable=True),
                    SimpleField(name="url", type="Edm.String", filterable=True, searchable=True),
                    SimpleField(name="doc_key", type="Edm.String", filterable=True), # Added for proper document referencing
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
                vector_search=VectorSearch(
                    profiles=[
                        VectorSearchProfile(
                            name="hnsw_text_3_large", 
                            algorithm_configuration_name="alg",
                            vectorizer_name="azure_open_ai_text_3_large"
                        )
                    ],
                    algorithms=[
                        HnswAlgorithmConfiguration(name="alg")
                    ],
                    vectorizers=[
                        AzureOpenAIVectorizer(
                            vectorizer_name="azure_open_ai_text_3_large",
                            parameters=vec_params
                        )
                    ]
                ),
                semantic_search=SemanticSearch(
                    default_configuration_name="semantic_config",
                    configurations=[
                        SemanticConfiguration(
                            name="semantic_config",
                            prioritized_fields=SemanticPrioritizedFields(
                                content_fields=[SemanticField(field_name="page_chunk")]
                            )
                        )
                    ]
                )
            )

            # Delete if exists, then create
            try:
                index_client.delete_index(name)
                self.logger.info(f"Deleted existing index '{name}'")
            except Exception:
                pass  # ignore if doesn't exist

            result = index_client.create_index(index_schema)
            self.logger.info(f"Created index '{name}' successfully")

            # ----------- Knowledge-Agent with API Key -------
            openai_api_key = os.getenv("AZURE_OPENAI_KEY_41") or os.getenv("AZURE_OPENAI_KEY") or ""
            
            agent = KnowledgeAgent(
                name=f"{name}-agent",
                models=[
                    KnowledgeAgentAzureOpenAIModel(
                        azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                            resource_url=azure_openai_endpoint,
                            deployment_name=env("AZURE_OPENAI_DEPLOYMENT_41"),
                            model_name="gpt-4.1",
                            api_key=openai_api_key,
                        )
                    )
                ],
                target_indexes=[
                    KnowledgeAgentTargetIndex(index_name=name, default_reranker_threshold=2.5)
                ],
                request_limits=KnowledgeAgentRequestLimits(
                    max_output_size=16000  # Match Azure Function's MAX_OUTPUT_SIZE default
                ),
            )
            index_client.create_or_update_agent(agent)
            self.logger.info(f"Created knowledge agent '{name}-agent' successfully")
            
            return True

        except Exception as e:
            self.logger.error(f"Failed to create index '{name}': {e}")
            return False

    def create_private_agentic_rag_index(self, index_client: SearchIndexClient, name: str) -> bool:
        """
        Create (or recreate) a private endpoint index + knowledge-agent using Managed Identity for Azure OpenAI.
        Private indexes require different configuration with executionEnvironment set to 'private'.
        """
        try:
            # ----------- Basic settings -----------------
            azure_openai_endpoint = env("AZURE_OPENAI_ENDPOINT_41")
            embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
            embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
            VECTOR_DIM = 3072

            # ----------- Vectorizer with Managed Identity (NO API KEY) -----------
            # For private indexes, we use managed identity authentication
            vec_params = AzureOpenAIVectorizerParameters(
                resource_url=azure_openai_endpoint,
                deployment_name=embedding_deployment,
                model_name=embedding_model,
                # NO api_key parameter - managed identity will be used
            )

            # Same index schema as public indexes
            index_schema = SearchIndex(
                name=name,
                fields=[
                    SearchField(name="id", type="Edm.String", key=True, filterable=True, sortable=True, facetable=True),
                    SearchableField(name="page_chunk", type="Edm.String", analyzer_name="standard.lucene"),
                    SearchField(
                        name="page_embedding_text_3_large",
                        type="Collection(Edm.Single)",
                        stored=False,
                        vector_search_dimensions=VECTOR_DIM,
                        vector_search_profile_name="hnsw_text_3_large",
                    ),
                    SimpleField(name="page_number", type="Edm.Int32", filterable=True, sortable=True, facetable=True),
                    SimpleField(name="source_file", type="Edm.String", filterable=True, facetable=True),
                    SimpleField(name="source", type="Edm.String", filterable=True, facetable=True),
                    SimpleField(name="url", type="Edm.String", filterable=True, searchable=True),
                    SimpleField(name="doc_key", type="Edm.String", filterable=True),
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
                vector_search=VectorSearch(
                    profiles=[
                        VectorSearchProfile(
                            name="hnsw_text_3_large", 
                            algorithm_configuration_name="alg",
                            vectorizer_name="azure_open_ai_text_3_large"
                        )
                    ],
                    algorithms=[
                        HnswAlgorithmConfiguration(name="alg")
                    ],
                    vectorizers=[
                        AzureOpenAIVectorizer(
                            vectorizer_name="azure_open_ai_text_3_large",
                            parameters=vec_params  # Uses managed identity (no API key)
                        )
                    ]
                ),
                semantic_search=SemanticSearch(
                    default_configuration_name="semantic_config",
                    configurations=[
                        SemanticConfiguration(
                            name="semantic_config",
                            prioritized_fields=SemanticPrioritizedFields(
                                content_fields=[SemanticField(field_name="page_chunk")]
                            )
                        )
                    ]
                )
            )

            # Delete if exists, then create with private execution environment
            try:
                index_client.delete_index(name)
                self.logger.info(f"Deleted existing private index '{name}'")
            except Exception:
                pass  # ignore if doesn't exist

            # Create the index (same as public, the private environment is set on indexers, not the index itself)
            result = index_client.create_index(index_schema)
            self.logger.info(f"Created private index '{name}' successfully")

            # ----------- Knowledge-Agent with Managed Identity -------
            # For private indexes, the knowledge agent also needs to use managed identity

            agent = KnowledgeAgent(
                name=f"{name}-agent",
                models=[
                    KnowledgeAgentAzureOpenAIModel(
                        azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                            resource_url=azure_openai_endpoint,
                            deployment_name=env("AZURE_OPENAI_DEPLOYMENT_41"),
                            model_name="gpt-4.1",
                            # NO api_key parameter - managed identity will be used
                        )
                    )
                ],
                target_indexes=[
                    KnowledgeAgentTargetIndex(index_name=name, default_reranker_threshold=2.5)
                ],
                request_limits=KnowledgeAgentRequestLimits(
                    max_output_size=16000  # Match Azure Function's MAX_OUTPUT_SIZE default
                ),
            )
            index_client.create_or_update_agent(agent)
            self.logger.info(f"Created private knowledge agent '{name}-agent' successfully")
            
            return True

        except Exception as e:
            self.logger.error(f"Failed to create private index '{name}': {e}")
            return False

    def plan_queries(self, question: str, client: AzureOpenAI, params: dict) -> List[str]:
        """Generate multiple search queries for comprehensive retrieval."""
        prompt = f"""
        You are a query planning assistant. Given a user question, generate 2-3 diverse search queries 
        that will help retrieve relevant information to answer the question comprehensively.
        
        Question: {question}
        
        Return only the queries, one per line, without numbering or explanation.
        """
        
        response = client.chat.completions.create(
            model=params.get("model", "gpt-4"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        queries = [q.strip() for q in response.choices[0].message.content.strip().split('\n') if q.strip()]
        return queries[:3]  # Limit to 3 queries max

    def retrieve(self, queries: List[str], client: SearchClient) -> List[dict]:
        """Retrieve documents using multiple queries."""
        all_docs = []
        seen_ids = set()
        
        for query in queries:
            try:
                results = client.search(
                    search_text=query,
                    top=5,
                    include_total_count=True
                )
                
                for doc in results:
                    if doc.get("id") not in seen_ids:
                        all_docs.append(doc)
                        seen_ids.add(doc.get("id"))
                        
            except Exception as e:
                self.logger.error(f"Search failed for query '{query}': {e}")
                continue
        
        return all_docs

    def build_context(self, docs: List[dict]) -> str:
        """Build context string from retrieved documents."""
        if not docs:
            return "No relevant documents found."
        
        context_parts = []
        for i, doc in enumerate(docs[:10], 1):  # Limit to top 10
            content = doc.get("page_chunk", "")
            source = doc.get("source_file", "Unknown")
            page = doc.get("page_number", "")
            
            part = f"[{i}] Source: {source}"
            if page:
                part += f" (Page {page})"
            part += f"\nContent: {content}\n"
            context_parts.append(part)
        
        return "\n".join(context_parts)

    def answer(self, question: str, ctx: str, client: AzureOpenAI, params: dict) -> Tuple[str, int]:
        """Generate answer based on question and context."""
        system_prompt = """
        You are a helpful assistant that answers questions based on the provided context.
        Use only the information from the context to answer questions.
        If the context doesn't contain enough information, say so clearly.
        Provide citations using [1], [2], etc. format referring to the source numbers in the context.
        """
        
        user_prompt = f"""
        Context:
        {ctx}
        
        Question: {question}
        
        Please provide a comprehensive answer based on the context above.
        """
        
        response = client.chat.completions.create(
            model=params.get("model", "gpt-4"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=params.get("max_tokens", 1000),
            temperature=params.get("temperature", 0.1)
        )
        
        answer_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0
        
        return answer_text, tokens_used

    def agentic_retrieval(self, agent_name: str, index_name: str, messages: list[dict]) -> str:
        """
        Perform agentic retrieval using Azure AI Foundry agent.
        This is a placeholder for the actual agent integration.
        """
        # This would integrate with the actual agent client
        # For now, return a placeholder response
        last_message = messages[-1]["content"] if messages else ""
        return f"Agent {agent_name} processed query from index {index_name}: {last_message}"


# Global service instance
index_service = IndexService()
