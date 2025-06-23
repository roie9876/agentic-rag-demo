# Agentic RAG Demo - Project Structure Guide

This document provides a comprehensive overview of the Agentic RAG Demo project structure, designed to serve as a reference for understanding the codebase and helping with future development tasks.

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Core Architecture](#core-architecture)
3. [Main Application Structure](#main-application-structure)
4. [Module Structure](#module-structure)
5. [Key Components](#key-components)
6. [Development Guidelines](#development-guidelines)
7. [Environment Configuration](#environment-configuration)
8. [Deployment Architecture](#deployment-architecture)

## 🎯 Project Overview

**Agentic RAG Demo** is a comprehensive demonstration of Agentic Retrieval-Augmented Generation on Azure, featuring advanced document processing, SharePoint integration, and multimodal AI capabilities.

### Key Features
- 🤖 **Agentic RAG**: Advanced retrieval-augmented generation with Azure AI Search knowledge agents
- 📄 **Multi-format Document Processing**: PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, JSON support
- 🖼️ **Multimodal Processing**: Image and figure extraction using Azure Document Intelligence
- 📊 **SharePoint Integration**: Automated indexing and synchronization
- 🔒 **Secure Authentication**: Multiple authentication methods (client secrets, certificates, Key Vault)
- ⚡ **Real-time Processing**: Streamlit web interface with live processing
- 📈 **Advanced Analytics**: Comprehensive reporting and monitoring

## 🏗️ Core Architecture

### High-Level Flow
```
Document Upload → DocumentChunker → Format-Specific Processor → 
Azure Document Intelligence → Embedding Generation → Index Storage → 
Knowledge Agent Retrieval → Contextual Response
```

### Technology Stack
- **Frontend**: Streamlit (Python-based web UI)
- **Backend**: Azure Functions (Python)
- **AI Services**: Azure OpenAI, Azure AI Search, Azure Document Intelligence
- **Storage**: Azure Blob Storage, Azure AI Search indexes
- **Integration**: SharePoint Online, Azure Key Vault
- **Authentication**: Azure AD, Managed Identity, API Keys

## 📁 Main Application Structure

### Root Directory Layout
```
agentic-rag-demo/
├── 📄 agentic-rag-demo.py          # Main Streamlit application (2400+ lines)
├── 📄 agent.py                     # Legacy agent implementation
├── 📄 agent_foundry.py             # AI Foundry agent management
├── 📄 azure_function_helper.py     # Azure Function deployment utilities
├── 📄 requirements.txt             # Python dependencies
├── 📄 README.md                    # Project documentation
├── 📄 .env.example                 # Environment variables template
├── 📁 function/                    # Azure Function code
├── 📁 chunking/                    # Document processing modules
├── 📁 connectors/                  # External service connectors
├── 📁 tools/                       # Azure service clients
├── 📁 health_check/                # Health monitoring system
├── 📁 app/                         # Modular application components
├── 📁 ui/                          # UI components (legacy)
├── 📁 utils/                       # Utility functions
├── 📁 scripts/                     # Automation scripts
├── 📁 infra/                       # Infrastructure-as-Code
└── 📁 media/                       # Documentation assets
```

## 🧩 Module Structure

### 1. Main Application (`agentic-rag-demo.py`)

**Purpose**: Primary Streamlit application with tabbed interface
**Key Features**:
- 🩺 Health Check tab - Service health monitoring
- 1️⃣ Create Index tab - New search index creation
- 2️⃣ Manage Index tab - Index management and agent configuration
- 3️⃣ Test Retrieval tab - Query testing interface
- ⚙️ Function Config tab - Azure Function deployment
- 🤖 AI Foundry Agent tab - Agent creation and management

**Key Functions**:
- `run_streamlit_ui()` - Main UI orchestrator
- `_chunk_to_docs()` - Document processing pipeline
- `pdf_to_documents()` - PDF-specific processing
- `init_openai()` - OpenAI client initialization
- `init_search_client()` - Azure AI Search client setup

### 2. Document Processing (`chunking/`)

```
chunking/
├── __init__.py                    # Module exports
├── document_chunking.py           # Main DocumentChunker class
├── chunker_factory.py            # Chunker selection logic
├── multimodal_processor.py       # Image/figure processing
├── exceptions.py                  # Custom exceptions
└── chunkers/                      # Format-specific chunkers
    ├── azure_document_intelligence_chunker.py
    ├── langchain_chunker.py
    ├── pandas_chunker.py
    └── simple_chunker.py
```

**Key Classes**:
- `DocumentChunker` - Main processing orchestrator
- `ChunkerFactory` - Selects appropriate chunker based on file type
- `MultimodalProcessor` - Handles images and figures in documents

### 3. SharePoint Integration (`connectors/sharepoint/`)

```
connectors/sharepoint/
├── sharepoint_data_reader.py      # Main SharePoint client
├── sharepoint_auth.py             # Authentication handling
├── sharepoint_indexer.py          # Document indexing logic
└── sharepoint_manager.py          # High-level management
```

**Authentication Methods**:
- Client Secret (recommended)
- Certificate-based
- Azure Key Vault integration

### 4. Azure Service Clients (`tools/`)

```
tools/
├── __init__.py                    # Module exports
├── aoai.py                        # Azure OpenAI client
├── aisearch.py                    # Azure AI Search client
├── doc_intelligence.py           # Document Intelligence client
├── blob.py                        # Azure Blob Storage client
└── keyvault.py                    # Azure Key Vault client
```

### 5. Health Monitoring (`health_check/`)

```
health_check/
├── __init__.py
├── health_checker.py             # Core health checking logic
├── health_check_ui.py            # Streamlit UI components
└── README.md                     # Module documentation
```

**Services Monitored**:
- Azure OpenAI (multiple endpoints)
- Azure AI Search
- Azure Document Intelligence
- Azure Storage
- SharePoint connectivity

### 6. Azure Functions (`function/`)

```
function/
├── host.json                     # Function runtime config
├── local.settings.json           # Local development settings
├── requirements.txt              # Function dependencies
├── agent.py                      # Shared agent logic
└── AgentFunction/               # HTTP-triggered function
    ├── __init__.py
    └── function.json
```

### 7. Modular Components (`app/`)

```
app/
├── document_processing/          # Document processing modules
├── openai/                      # OpenAI integration
├── search/                      # Search functionality
├── ui/                         # UI components
└── utils/                      # Shared utilities
```

## 🔧 Key Components

### Document Processing Pipeline

1. **File Upload** → Streamlit file uploader or SharePoint connector
2. **Format Detection** → File extension-based routing
3. **Chunker Selection** → ChunkerFactory determines appropriate processor
4. **Processing** → Format-specific extraction (PDF, DOCX, etc.)
5. **Multimodal Enhancement** → Image/figure processing if enabled
6. **Embedding Generation** → Azure OpenAI text-embedding-3-large
7. **Index Storage** → Azure AI Search with metadata

### Authentication Flow

```
Request → Environment Check → Authentication Method Selection:
├── API Key → Direct authentication
├── Managed Identity → Azure AD token
├── Client Secret → SharePoint app authentication
└── Certificate → Certificate-based authentication
```

### Knowledge Agent Architecture

```
User Query → Knowledge Agent → Index Search → 
Retrieval → Reranking → Context Building → 
OpenAI Response → Citation Generation
```

## 📝 Development Guidelines

### Code Organization Principles

1. **Modular Design**: Each module has a specific responsibility
2. **Configuration-Driven**: Environment variables control behavior
3. **Error Handling**: Comprehensive error handling with fallbacks
4. **Logging**: Structured logging for debugging and monitoring
5. **Security**: No hardcoded secrets, proper credential management

### File Naming Conventions

- **Snake_case** for Python files and functions
- **CamelCase** for class names
- **UPPER_CASE** for constants and environment variables
- **kebab-case** for configuration files

### Testing Strategy

- Health checks for service availability
- Processing validation for each document type
- Authentication testing for all methods
- UI component testing with Streamlit

### Performance Considerations

- **Batch Processing**: Configurable batch sizes for document processing
- **Caching**: Client connection reuse
- **Async Operations**: Non-blocking operations where possible
- **Memory Management**: Proper cleanup of large document processing

## ⚙️ Environment Configuration

### Critical Environment Variables

#### Azure OpenAI
```bash
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_CHATGPT_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
```

#### Azure AI Search
```bash
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-search-key  # Optional with managed identity
```

#### SharePoint Integration
```bash
SHAREPOINT_TENANT_ID=your-tenant-id
SHAREPOINT_CLIENT_ID=your-client-id
SHAREPOINT_CLIENT_SECRET=your-client-secret
SHAREPOINT_SITE_DOMAIN=yourtenant.sharepoint.com
SHAREPOINT_SITE_NAME=yoursite
SHAREPOINT_SITE_FOLDER=/Documents
```

#### Multimodal Processing
```bash
MULTIMODAL=true
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection
AZURE_STORAGE_CONTAINER=images
```

### Configuration Hierarchy

1. **Environment Variables** (highest priority)
2. **`.env` file** (development)
3. **Azure Function App Settings** (production)
4. **Default Values** (fallback)

## 🚀 Deployment Architecture

### Local Development
```
Developer Machine → Streamlit UI → Azure Services
                 → Azure Functions (local testing)
```

### Production Deployment
```
User → Streamlit App → Azure Functions → Azure AI Services
                    → SharePoint → Document Processing
                    → Azure AI Search → Knowledge Agents
```

### Infrastructure Components

1. **Azure AI Search** - Document indexing and retrieval
2. **Azure OpenAI** - Language models and embeddings
3. **Azure Document Intelligence** - Advanced document processing
4. **Azure Functions** - Serverless compute for batch processing
5. **Azure Storage** - Document and image storage
6. **Azure Key Vault** - Secure credential management
7. **SharePoint Online** - Document source integration

### Monitoring and Observability

- **Application Insights** - Performance and error tracking
- **Health Checks** - Service availability monitoring
- **Processing Logs** - Document processing statistics
- **User Analytics** - Usage patterns and optimization

## 📊 Data Flow

### Document Ingestion Flow
```
Document Source (Upload/SharePoint) → 
Validation → 
Format Detection → 
Content Extraction → 
Chunking → 
Embedding Generation → 
Index Storage → 
Metadata Tracking
```

### Query Processing Flow
```
User Query → 
Query Planning → 
Index Search → 
Result Retrieval → 
Reranking → 
Context Assembly → 
Response Generation → 
Citation Formatting
```

### SharePoint Ingestion Pipeline

The SharePoint ingestion pipeline is a sophisticated system that automatically indexes documents from SharePoint folders into Azure AI Search. Here's the detailed flow:

#### 🔗 **SharePoint Connection & Authentication Flow**
```
Environment Variables → SharePointDataReader → Authentication → Microsoft Graph API Access
```

**Key Files:**
- `connectors/sharepoint/sharepoint_data_reader.py` - Main SharePoint client
- `connectors/sharepoint/sharepoint_files_indexer.py` - Document processing orchestrator

**Authentication Methods (in priority order):**
1. **Certificate-based Authentication** (`AGENTIC_APP_SPN_CERT_PATH`)
2. **Client Secret Authentication** (`SHAREPOINT_CLIENT_SECRET`)
3. **Interactive Browser Login** (fallback)

#### 📁 **SharePoint File Discovery Flow**
```
SharePoint Site/Domain → Site ID Resolution → Drive ID Resolution → 
Folder Navigation → File Enumeration → Format Filtering → 
Time-based Filtering → Permission Check
```

**Process Details:**
1. **Site ID Resolution**: Convert `SHAREPOINT_SITE_DOMAIN` + `SHAREPOINT_SITE_NAME` to Graph API Site ID
2. **Drive ID Resolution**: Find the target drive (default or named drive like "Documents")
3. **Folder Navigation**: Navigate to specified folder path (e.g., `/Documents/Reports`)
4. **File Discovery**: Enumerate all files in the folder and subfolders
5. **Format Filtering**: Filter by file extensions (PDF, DOCX, PPTX, XLSX, etc.)
6. **Time Filtering**: Optional filtering by last modified date
7. **Permission Extraction**: Get read access entities for security

#### 🔄 **Document Processing Pipeline Flow**
```
SharePoint File → Content Download → Duplicate Check → 
DocumentChunker → Format-Specific Processing → 
Multimodal Enhancement → Embedding Generation → 
Index Upload → Metadata Tracking
```

**Detailed Processing Steps:**

**Step 1: Content Retrieval**
- **API Call**: `GET /sites/{site-id}/drives/{drive-id}/root:/{folder-path}/{filename}:/content`
- **Authentication**: Bearer token from Microsoft Graph
- **File Download**: Raw bytes downloaded from SharePoint
- **Metadata Extraction**: File properties, permissions, timestamps

**Step 2: Duplicate Detection & Change Management**
- **Index Query**: Search Azure AI Search for existing chunks by `parent_id`
- **Timestamp Comparison**: Compare SharePoint `lastModifiedDateTime` with indexed `metadata_storage_last_modified`
- **Decision Logic**: Skip if unchanged, delete old chunks if modified
- **Tracking**: Log skipped vs. processed files

**Step 3: Document Processing (DocumentChunker)**
- **File**: `chunking/document_chunking.py` - Main DocumentChunker class
- **Input**: Base64-encoded document bytes + metadata
- **Chunker Selection**: Automatic based on file extension
  - `.pdf` → Azure Document Intelligence Chunker
  - `.docx/.pptx` → Azure Document Intelligence Chunker  
  - `.xlsx/.csv` → Pandas Chunker
  - `.txt/.md/.json` → Simple Text Chunker
  - Fallback → LangChain Chunker

**Step 4: Azure Service Integration**

**Azure Document Intelligence Processing:**
- **Service**: Azure Document Intelligence (4.0 API)
- **Capabilities**: OCR, layout analysis, table extraction, figure detection
- **Input**: Binary document content
- **Output**: Structured text with page numbers, tables, and image references
- **Multimodal**: Image extraction and AI-powered captioning (if enabled)

**Azure OpenAI Embedding Generation:**
- **Model**: `text-embedding-3-large` (default)
- **Service**: Azure OpenAI
- **Process**: Convert text chunks to 3072-dimensional vectors
- **Batch Processing**: Multiple chunks embedded simultaneously

**Step 5: Index Storage (Azure AI Search)**
- **Service**: Azure AI Search
- **Index Schema**: Hybrid search with vector and keyword fields
- **Batch Upload**: Uses `SearchIndexingBufferedSender` for efficient uploads
- **Error Handling**: Failed uploads tracked and reported

#### 🏗️ **Index Schema Structure**

**Core Fields:**
```json
{
  "id": "unique_chunk_identifier",
  "page_chunk": "extracted_text_content",
  "page_number": 1,
  "source_file": "document.pdf",
  "parent_id": "sharepoint_document_id",
  "url": "https://tenant.sharepoint.com/path/to/file",
  "page_embedding_text_3_large": [vector_array]
}
```

**SharePoint-Specific Metadata:**
```json
{
  "metadata_storage_path": "sharepoint_web_url",
  "metadata_storage_name": "filename.pdf",
  "metadata_storage_last_modified": "2024-01-15T10:30:00Z",
  "metadata_security_id": "user_permissions",
  "sharepoint_id": "unique_sharepoint_id",
  "source": "sharepoint"
}
```

**Enhanced Processing Metadata:**
```json
{
  "extraction_method": "document_intelligence|pandas_parser|simple_parser",
  "document_type": "PDF|DOCX|XLSX",
  "has_figures": true,
  "processing_timestamp": "2024-01-15T10:30:00Z",
  "isMultimodal": true,
  "imageCaptions": "AI-generated image descriptions",
  "relatedImages": ["image_url1", "image_url2"]
}
```

#### 🎯 **Integration Points in Main Application**

**UI Integration** (`agentic-rag-demo.py`):
```python
# Line ~1960: SharePoint ingestion button
if st.button("🔗 Ingest from SharePoint"):
    sharepoint_reader = SharePointDataReader()
    sp_files = sharepoint_reader.retrieve_sharepoint_files_content(
        site_domain=site_domain,
        site_name=site_name,
        folder_path=folder_path,
        file_formats=file_types,
        drive_name=drive_name
    )
```

**Processing Integration**:
```python
# Line ~2000: Document processing with _chunk_to_docs
docs = _chunk_to_docs(
    fname,
    file_bytes,
    file_url,
    oai_client,
    embed_deploy,
)
```

#### 🔧 **Configuration Requirements**

**Environment Variables:**
```bash
# SharePoint Authentication
SHAREPOINT_TENANT_ID=your-tenant-id
SHAREPOINT_CLIENT_ID=your-app-id  
SHAREPOINT_CLIENT_SECRET=your-secret

# SharePoint Location
SHAREPOINT_SITE_DOMAIN=yourtenant.sharepoint.com
SHAREPOINT_SITE_NAME=yoursite  # or blank for root
SHAREPOINT_SITE_FOLDER=/Documents/YourFolder
SHAREPOINT_DRIVE_NAME=Documents  # optional

# Azure Services
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
DOCUMENT_INTEL_ENDPOINT=https://your-docint.cognitiveservices.azure.com/

# Optional: Multimodal Processing
MULTIMODAL=true
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection
```

#### 📊 **Processing Statistics & Monitoring**

**Success Tracking:**
- Files processed with chunk count
- Extraction methods used (Document Intelligence, Pandas, etc.)
- Multimodal content detection
- Processing time and throughput

**Error Handling:**
- Skipped files (duplicates, no content, invalid format)
- Failed files (processing errors, upload failures)  
- Authentication failures
- Service availability issues

**Example Output:**
```
✅ Successfully Processed (5 files):
   • Report_Q1.pdf - 12 chunks (document_intelligence) 🎨
   • Data_Analysis.xlsx - 3 chunks (pandas_parser)
   • Meeting_Notes.docx - 8 chunks (document_intelligence)

⚠️ Skipped Files (2 files):
   • Empty_File.pdf (0 bytes) - No content
   • Duplicate_Report.pdf - Already indexed (unchanged)
```

#### 🚀 **Automated Scheduling (Azure Functions)**

**Scheduled Processing:**
- **Function**: `sharepoint-functions/SharePointIndexer/`
- **Schedule**: Configurable CRON expression (e.g., every 15 minutes)
- **Change Detection**: Only processes modified files
- **Cleanup**: Removes deleted files from index
- **Reporting**: Comprehensive processing reports

This SharePoint ingestion pipeline provides enterprise-grade document processing with comprehensive error handling, security, and monitoring capabilities.

---

## 💡 Development Tips

### Adding New Document Formats

1. Create new chunker in `chunking/chunkers/`
2. Register in `ChunkerFactory`
3. Add format detection logic
4. Update UI file type filters
5. Add processing tests

### Extending Authentication

1. Add new auth method to `connectors/sharepoint/sharepoint_auth.py`
2. Update environment variable handling
3. Add configuration UI elements
4. Test authentication flow

### Adding New Azure Services

1. Create client wrapper in `tools/`
2. Add health check in `health_check/health_checker.py`
3. Update environment configuration
4. Add UI integration

### Performance Optimization

1. Profile document processing bottlenecks
2. Implement connection pooling
3. Add batch processing capabilities
4. Monitor memory usage patterns

---

This document serves as the definitive guide to understanding and working with the Agentic RAG Demo project. Keep it updated as the project evolves and use it as a reference for architectural decisions and development patterns.
