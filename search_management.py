from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchField,
    ComplexField,
    SearchFieldDataType,   # <-- add this
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    HnswParameters,
)

# Add multimodal fields to the index schema

# ... existing code ...

def create_search_index(
        index_name,
        search_client,
        embedding_dimension: int = 1536,       # <−− add a parameter for vector size
        enable_multimodal: bool = True):  # default is now True
    """
    Create a search index with the specified name.
    
    Args:
        index_name: Name for the index
        search_client: Azure Cognitive Search client
        embedding_dimension: Dimension of the embedding vector
        enable_multimodal: Whether to enable multimodal fields in the index (default: True)
    """
    # -------------------- FIX START --------------------
    hnsw_conf_name = "myHnswConf"
    vector_search = VectorSearch(
        algorithm_configurations=[
            HnswAlgorithmConfiguration(
                name=hnsw_conf_name,
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500,
                    metric="cosine",
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name=hnsw_conf_name,
            )
        ],
    )
    # --------------------  FIX END  --------------------

    # Define semantic configuration
    semantic_config = {
        "configurations": [
            {
                "name": "my-semantic-config",
                "prioritizedFields": {
                    "titleField": None,
                    "prioritizedContentFields": [
                        {
                            "fieldName": "content"
                        }
                    ],
                    "prioritizedKeywordsFields": []
                }
            }
        ]
    }
    
    # Define fields based on the actual index structure
    fields = [
        # keys / identifiers
        SimpleField(name="id", type=SearchFieldDataType.String, key=True,
                    searchable=False, retrievable=True, filterable=True,
                    sortable=True, facetable=True),

        # legacy chunk + vector  ↓↓↓  (add these back)
        SimpleField(name="page_chunk", type=SearchFieldDataType.String,
                    searchable=True, retrievable=True),
        SearchField(name="page_embedding_text",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=embedding_dimension,
                    vector_search_profile="myHnswProfile"),   # ← property name

        # new unified content + vector (keep them if you still need them)
        SimpleField(name="content", type=SearchFieldDataType.String,
                    searchable=True, retrievable=True),
        SearchField(name="contentVector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=embedding_dimension,
                    vector_search_profile="myHnswProfile"),

        # other metadata
        SimpleField(name="page_number",  type=SearchFieldDataType.Int32,
                    retrievable=True, filterable=True, sortable=True, facetable=True),
        SimpleField(name="filename",     type=SearchFieldDataType.String,
                    retrievable=True, filterable=True, facetable=True),
        SimpleField(name="source_file",  type=SearchFieldDataType.String,
                    retrievable=True, filterable=True, facetable=True),
        SimpleField(name="source",       type=SearchFieldDataType.String,
                    retrievable=True, filterable=True, facetable=True),
        SimpleField(name="url",          type=SearchFieldDataType.String,
                    retrievable=True),
        SimpleField(name="doc_key",      type=SearchFieldDataType.String,
                    retrievable=True, filterable=True),
        SimpleField(name="extraction_method", type=SearchFieldDataType.String,
                    retrievable=True, filterable=True, facetable=True),
        SimpleField(name="document_type",    type=SearchFieldDataType.String,
                    retrievable=True, filterable=True, facetable=True),
        SimpleField(name="has_figures",  type=SearchFieldDataType.Boolean,
                    retrievable=True, filterable=True, facetable=True),
        SimpleField(name="processing_timestamp", type=SearchFieldDataType.DateTimeOffset,
                    retrievable=True, filterable=True, sortable=True),
        SimpleField(name="isMultimodal", type=SearchFieldDataType.Boolean,
                    retrievable=True, filterable=True, facetable=True),
    ]

    # optional multimodal additions
    if enable_multimodal:
        multimodal_fields = [
            SimpleField(name="imageCaptions", type=SearchFieldDataType.String,
                        searchable=True, retrievable=True),
            SearchField(name="captionVector",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True,
                        vector_search_dimensions=embedding_dimension,
                        vector_search_profile="myHnswProfile"),
            SimpleField(name="relatedImages",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                        filterable=True, retrievable=True),
            ComplexField(name="imageDetails",
                         collection=True,
                         fields=[],
                         retrievable=True)   # populate sub-fields if necessary
        ]
        fields.extend(multimodal_fields)
    
    # Create the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_config
    )
    
    try:
        search_client.create_index(index)
        return True, f"Index '{index_name}' created successfully."
    except Exception as e:
        return False, f"Error creating index: {str(e)}"
