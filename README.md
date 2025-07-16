# Agentic RAG Demo

A comprehensive demonstration of Agentic Retrieval-Augmented Generation on Azure using Azure OpenAI, Azure AI Search, and SharePoint integration with advanced document processing capabilities.

## ✨ Key Features

- **🤖 Agentic RAG**: Advanced retrieval-augmented generation with Azure AI Search knowledge agents
- **🏗️ AI Foundry Account Deployment**: Automated deployment of Azure AI Foundry Accounts with network security and private endpoints
- **📄 Multi-format Document Processing**: Support for PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, JSON with unified processing pipeline
- **🖼️ Multimodal Processing**: Advanced image and figure extraction from documents using Azure Document Intelligence
- **📊 SharePoint Integration**: Automated indexing and synchronization with SharePoint Online
- **🔒 Secure Authentication**: Multiple authentication methods including client secrets, certificates, and Azure Key Vault
- **🌐 Private Network Support**: Complete private network deployment with VNet integration and private endpoints
- **⚡ Real-time Processing**: Streamlit web interface with live document upload and processing
- **📈 Advanced Analytics**: Comprehensive reporting and monitoring of document processing

## � What's New

### AI Foundry Account Deployment
- **One-Click Deployment**: Deploy complete AI Foundry Accounts with bicep templates
- **Network Security**: Private VNet with subnets and private endpoints
- **Resource Flexibility**: Skip or use existing Azure resources (AI Search, Storage, Cosmos DB)
- **DNS Integration**: Automatic private DNS zone creation and configuration
- **Real-time Monitoring**: Live deployment status tracking and error reporting

### Enhanced Architecture  
- **Modular Design**: Clean separation of concerns with organized module structure
- **Documentation Hub**: All implementation docs moved to `/docs/` folder for better organization
- **Performance Optimizations**: Ultra-fast UI with optimized caching and state management

## 📖 Documentation

Comprehensive documentation is now organized in the `/docs/` folder:

- **[📚 Complete Documentation Hub](docs/)** - All project documentation and guides
- **[🏗️ Project Structure Guide](docs/PROJECT_STRUCTURE.md)** - Detailed codebase overview
- **[⚡ Performance Optimizations](docs/ULTRA_FAST_UI_PERFORMANCE_FINAL.md)** - Ultra-fast UI implementation
- **[🌐 AI Foundry Implementation](docs/AI_FOUNDRY_FINAL_IMPLEMENTATION_SUMMARY.md)** - AI Foundry Account deployment guide
- **[🔧 Modular Development](docs/MODULAR_DEVELOPMENT_WORKFLOW.md)** - Development guidelines and architecture

## 🌐 Agentic RAG Deployment Guide - A to Z

This section provides a comprehensive step-by-step visual guide for deploying the complete Agentic RAG Demo from start to finish, including private endpoints, network security, and AI Foundry integration.

### 🏗️ High-Level Deployment Architecture

![Agentic RAG Architecture Overview](media/HLD.png)

*Complete architecture overview showing the Agentic RAG ingest pipeline with Azure AI Foundry, Copilot Studio, private networks, and M365 integration*

### 📋 Complete Deployment Process

#### Step 1: Deploy AI Foundry Account
![Step 1 - Deploy AI Account](media/step%20(1)%20Deploy%20AI%20Account%20.png)

*Deploy Azure AI Foundry Account with all required services including Azure OpenAI, AI Search, Document Intelligence, and network security*

#### Step 2: Run Private Health Check
![Step 2 - Private Health Check](media/step(2)%20run%20Private%20Health%20Check%20.png)

*Verify all Azure services are properly deployed and accessible within the private network configuration*

#### Step 3: Create Search Index
![Step 3 - Create Index](media/step%20%20(3)%20Create%20Index.png)

*Set up Azure AI Search index with proper schema, vector fields, and document processing configuration*

#### Step 4: Manage Index and Documents
![Step 4 - Manage Index](media/step%20(4)%20Manage%20Index.png)

*Upload and process documents, manage index content, and configure document chunking strategies*

#### Step 5: Run Test Retrieval
![Step 5 - Test Retrieval](media/steo%20(5)%20Run%20Test%20Retrieval.png)

*Test the retrieval system with sample queries and validate search results and knowledge agent responses*

#### Step 6: Configure Function 1 (Document Processing)
![Step 6 - Function 1 Config](media/step%20(6)%20Function%201%20Config.png)

*Deploy and configure Azure Functions for automated document processing and SharePoint integration*

#### Step 7: Create AI Foundry Agent
![Step 7 - Create AI Foundry Agent](media/step%20(7)%20Create%20AI%20Foundry%20Agent.png)

*Set up knowledge agents in Azure AI Foundry with proper grounding data and conversation flows*

#### Step 8: Configure Function 2 (Studio2Foundry)
![Step 8 - Function 2 Config](media/Step%20(8)%20Function%202%20config%20(Studio2Foundry).png)

*Configure the Studio2Foundry integration for seamless agent deployment and management*

#### Step 9: Set up Virtual Network Support for Power Platform
![Step 9 - Power Platform VNet](media/Step9%20Set%20up%20Virtual%20Network%20support%20for%20Power%20Platform.png)

*Enable Power Platform integration with virtual network support for enterprise-grade security and compliance*

### 🚀 Quick Deployment Commands

```bash
# Clone and setup the project
git clone https://github.com/your-org/agentic-rag-demo.git
cd agentic-rag-demo
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure service credentials

# Deploy with private endpoints (one-click)
cd 15-private-network-standard-agent-setup
az deployment group create \
  --resource-group your-rg \
  --template-file main.json \
  --parameters @main.json.parameters

# Start the application
cd ..
streamlit run agentic-rag-demo.py
```

### ✨ Deployment Features

- ✅ **Complete AI Foundry Setup**: Automated deployment of Azure AI Foundry Account with all required services
- ✅ **Private Network Security**: Full VNet integration with private endpoints for all Azure services
- ✅ **Document Processing Pipeline**: Automated ingestion from SharePoint, OneDrive, and file uploads
- ✅ **Knowledge Agent Integration**: Seamless connection between search index and AI Foundry agents
- ✅ **Power Platform Support**: Enterprise-grade integration with virtual network security
- ✅ **Health Monitoring**: Comprehensive health checks and real-time status monitoring
- ✅ **Function Automation**: Automated document processing and agent management workflows
- ✅ **Multi-modal Support**: Advanced document intelligence with image and text processing

---

## 🛠️ Quick Start

### Prerequisites
- Python 3.9+
- Azure CLI (`az login` required)
- Azure subscription with appropriate permissions

### Installation

```bash
git clone https://github.com/your-org/agentic-rag-demo.git
cd agentic-rag-demo
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Edit with your Azure service credentials
streamlit run agentic-rag-demo.py
```

### Authentication

The application uses **Managed Identity (RBAC) Authentication** for Azure AI Search:
- Ensure your application has the "Search Index Data Reader" and "Search Service Contributor" roles assigned on the Azure AI Search service
- This approach eliminates the need to manage API keys and is the recommended method for production deployments

### SharePoint Integration

The application can connect to SharePoint to retrieve documents. You can use one of the following authentication methods:

#### Option 1: Client Secret Authentication (Recommended)

1. Register an application in Azure AD for your Agentic app.
2. Grant the application permissions to access SharePoint sites and lists.
3. Add a client secret to your Azure AD app registration.
4. Configure the following environment variables:
   - `SHAREPOINT_TENANT_ID` - Your SharePoint tenant ID
   - `SHAREPOINT_CLIENT_ID` - Application (client) ID of your Azure AD app
   - `SHAREPOINT_CLIENT_SECRET` - Client secret of your Azure AD app
   - `SHAREPOINT_SITE_DOMAIN` - SharePoint site domain (e.g., "yourtenant.sharepoint.com")
   - `SHAREPOINT_SITE_NAME` - SharePoint site name (leave blank for root site)
   - `SHAREPOINT_SITE_FOLDER` - SharePoint folder path (e.g., "/Documents")

#### Option 2: Certificate Authentication

1. Register an application in Azure AD for your Agentic app.
2. Grant the application permissions to access SharePoint sites and lists.
3. Create a self-signed certificate and upload it to your Azure AD app registration.
4. Configure the following environment variables:
   - `SHAREPOINT_TENANT_ID` - Your SharePoint tenant ID
   - `SHAREPOINT_CLIENT_ID` - Application (client) ID of your Azure AD app
   - `AGENTIC_APP_SPN_CERT_PATH` - Path to the certificate file (PEM or PFX)
   - `AGENTIC_APP_SPN_CERT_PASSWORD` - Password for the certificate (if applicable)
   - `SHAREPOINT_SITE_DOMAIN` - SharePoint site domain

#### Option 3: Azure Key Vault for Secrets (Recommended for Production)

For enhanced security, store your SharePoint client secret in Azure Key Vault:
1. Create an Azure Key Vault and store your SharePoint client secret
2. Configure the following environment variables:
   - `AZURE_KEY_VAULT_NAME` - Name of your Azure Key Vault
   - `AZURE_KEY_VAULT_ENDPOINT` - Endpoint URL of your Azure Key Vault
   - `SHAREPOINT_CLIENT_SECRET_NAME` - Name of the secret in Key Vault (default: "sharepointClientSecret")

### Multimodal Processing

The application supports advanced multimodal processing for extracting and analyzing images within documents:

- **Enable Multimodal**: Set `MULTIMODAL=true` in your `.env` file
- **Azure Storage**: Configure `AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER` for image storage
- **Supported Formats**: PDF, DOCX, PPTX with embedded images and figures
- **AI-Powered Analysis**: Automatic image captioning and content understanding

---

## Quick‑start

```bash
git clone https://github.com/your‑org/agentic-rag-demo.git
cd agentic-rag-demo
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # fill with your own values
streamlit run agentic-rag-demo.py
```

---

## Application Features

### 📄 Document Processing Pipeline
- **Unified Processing**: All document formats use the same DocumentChunker for consistency
- **Format Support**: PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, JSON with specialized chunkers for each format
- **Azure Document Intelligence**: Advanced OCR and layout analysis for complex documents
- **Metadata Extraction**: Comprehensive metadata including extraction methods, document types, and processing timestamps

### 🔍 Search and Retrieval
- **Hybrid Search**: Combines BM25 keyword search with vector similarity search
- **Agentic RAG**: Knowledge agents provide context-aware responses with proper citations
- **Test Retrieval**: Interactive testing interface for query optimization

### 📊 SharePoint Integration
- **Automated Indexing**: Scheduled processing of SharePoint documents
- **Real-time Sync**: Detection and processing of modified files
- **Comprehensive Reporting**: Detailed processing statistics and success/failure tracking
- **Batch Processing**: Configurable batch sizes and processing schedules

#### 🔄 SharePoint Index Pipeline for Office & PDF Files

The SharePoint index pipeline is a sophisticated multi-stage process that transforms raw documents from SharePoint into intelligently processed, searchable content in Azure AI Search:

**Complete Pipeline Overview:**
```
SharePoint Document → Authentication → Discovery → Download → 
Format Detection → Document Intelligence → Multimodal Processing → 
Chunking → Embedding Generation → Index Storage → Search Ready
```

**🏗️ Stage-by-Stage Process:**

**Stage 1: SharePoint Connection & File Discovery**
- **Authentication**: Certificate-based or client secret authentication via Microsoft Graph API
- **File Discovery**: Recursively scans SharePoint folders for supported file types (`.pdf`, `.docx`, `.pptx`, `.xlsx`)
- **Change Detection**: Compares timestamps to process only modified files
- **Security Preservation**: Maintains original document permissions and access controls

**Stage 2: Document Processing Pipeline**
- **File Download**: Binary content retrieved from SharePoint via Graph API
- **Format Detection**: File extension determines processing strategy
- **Chunker Selection**: ChunkerFactory routes to appropriate processor based on file type

**Stage 3: Azure Document Intelligence Integration**

For **PDF, DOCX, PPTX** files, the system leverages Azure Document Intelligence:
- **OCR Processing**: Extracts text from scanned documents and images
- **Layout Analysis**: Identifies document structure (headers, paragraphs, tables)
- **Table Extraction**: Preserves tabular data structure with relationships
- **Figure Detection**: Identifies and extracts embedded images and figures
- **Coordinate Mapping**: Maintains positional information for accurate content extraction

**Stage 4: Multimodal Processing Enhancement**

When `MULTIMODAL=true` is enabled:
- **Image Extraction**: Extracts embedded images from PDFs and Office documents
- **Azure Blob Storage**: Stores images with unique identifiers and secure access
- **OpenAI GPT-4 Vision**: Generates descriptive captions for images using advanced AI
- **Caption Embedding**: Creates separate embeddings for image descriptions
- **Content Association**: Links images to their corresponding text chunks for contextual search

**Stage 5: Intelligent Chunking Strategies**
- **PDF Processing**: Layout-aware chunking that preserves table structures and reading order
- **Office Documents**: Extracts text while preserving document structure (slides, paragraphs)
- **Excel Files**: Uses Pandas parser to convert tabular data into natural language summaries
- **Adaptive Chunking**: Optimizes chunk sizes based on content type and complexity

**Stage 6: Azure OpenAI Embedding Generation**
- **Model**: `text-embedding-3-large` (3072-dimensional vectors)
- **Content Preparation**: Filename prefix added to chunks for enhanced context
- **Dual Vectors**: Separate embeddings for text content and image captions
- **Batch Processing**: Efficient parallel processing of multiple chunks

**Stage 7: Azure AI Search Index Storage**

Creates a hybrid search index with rich metadata:
```json
{
  "id": "unique_chunk_identifier",
  "page_chunk": "processed_text_content",
  "page_embedding_text_3_large": [3072_dimensional_vector],
  "page_number": 1,
  "source_file": "document.pdf",
  "parent_id": "sharepoint_document_id",
  "url": "sharepoint_document_url",
  
  // SharePoint-specific metadata
  "metadata_storage_path": "sharepoint_web_url",
  "metadata_storage_name": "filename.pdf", 
  "metadata_storage_last_modified": "2024-01-15T10:30:00Z",
  "metadata_security_id": "user_permissions",
  
  // Processing metadata
  "extraction_method": "document_intelligence",
  "document_type": "PDF Document",
  "has_figures": true,
  "processing_timestamp": "2024-01-15T10:30:00Z",
  
  // Multimodal fields (when enabled)
  "imageCaptions": "AI-generated descriptions",
  "captionVector": [caption_embedding_array],
  "relatedImages": ["blob_storage_urls"],
  "isMultimodal": true
}
```

**🎯 Advanced Processing Features:**
- **Smart Retry Logic**: Multiple content-type detection strategies for robust processing
- **Change Detection**: Only processes modified files for efficiency
- **Error Handling**: Comprehensive error tracking and graceful fallback mechanisms
- **Security Preservation**: Maintains SharePoint permissions and access controls
- **Real-time Monitoring**: Live processing status with detailed success/failure reporting

**📊 Processing Outcomes:**
```
✅ Successfully Processed (5 files):
   • Report_Q1.pdf - 12 chunks (document_intelligence) 🎨
   • Data_Analysis.xlsx - 3 chunks (pandas_parser)
   • Meeting_Notes.docx - 8 chunks (document_intelligence)
   • Presentation.pptx - 15 chunks (document_intelligence) 🎨

⚠️ Skipped Files (2 files):
   • Empty_File.pdf (0 bytes) - No content
   • Duplicate_Report.pdf - Already indexed (unchanged)
```

This comprehensive pipeline ensures that Office files and PDFs from SharePoint are transformed into intelligent, searchable knowledge with full multimodal capabilities for enhanced retrieval and contextual understanding.

### ⚙️ Configuration Management
- **Function Deployment**: Automated Azure Function deployment and configuration
- **Environment Sync**: Push configuration changes to Azure Functions
- **Health Monitoring**: Built-in health checks and diagnostics

---

## Environment variables (`.env`)

Below are the main environment variables used by this project. **Do not use real secrets in documentation or commits.**

### Core Azure Services
| Key | Example value (fake) | Description |
|-----|----------------------|-------------|
| `AZURE_OPENAI_ENDPOINT` | `https://my-openai.openai.azure.com/` | Azure OpenAI endpoint |
| `AZURE_OPENAI_KEY` | `YOUR-OPENAI-KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | `2025-01-01-preview` | OpenAI API version |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4.1` | Chat model deployment name |
| `AZURE_OPENAI_CHATGPT_DEPLOYMENT` | `gpt-4.1` | **Must match actual deployment** |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-3-large` | Embedding model deployment |
| `AZURE_SEARCH_ENDPOINT` | `https://my-search.search.windows.net` | Azure AI Search endpoint |
| `DOCUMENT_INTEL_ENDPOINT` | `https://my-formrec.cognitiveservices.azure.com` | Document Intelligence endpoint |
| `DOCUMENT_INTEL_KEY` | `YOUR-DOC-INTEL-KEY` | Document Intelligence API key |

### SharePoint Configuration
| Key | Example value | Description |
|-----|---------------|-------------|
| `SHAREPOINT_TENANT_ID` | `00000000-0000-0000-0000-000000000000` | SharePoint tenant ID |
| `SHAREPOINT_CLIENT_ID` | `00000000-0000-0000-0000-000000000000` | App registration client ID |
| `SHAREPOINT_CLIENT_SECRET` | `YOUR-SECRET` | App registration client secret |
| `SHAREPOINT_SITE_DOMAIN` | `mytenant.sharepoint.com` | SharePoint site domain |
| `SHAREPOINT_SITE_NAME` | `mysite` | SharePoint site name (blank for root) |
| `SHAREPOINT_SITE_FOLDER` | `/Documents` | SharePoint folder path |
| `SHAREPOINT_CONNECTOR_ENABLED` | `true` | Enable SharePoint connector |

### Azure Key Vault (Optional)
| Key | Example value | Description |
|-----|---------------|-------------|
| `AZURE_KEY_VAULT_NAME` | `my-keyvault` | Azure Key Vault name |
| `AZURE_KEY_VAULT_ENDPOINT` | `https://my-keyvault.vault.azure.net/` | Key Vault endpoint |
| `SHAREPOINT_CLIENT_SECRET_NAME` | `sharepointClientSecret` | Secret name in Key Vault |

### Multimodal Processing
| Key | Example value | Description |
|-----|---------------|-------------|
| `MULTIMODAL` | `true` | Enable multimodal processing |
| `AZURE_STORAGE_CONNECTION_STRING` | `DefaultEndpointsProtocol=https;...` | Storage for images |
| `AZURE_STORAGE_CONTAINER` | `images` | Storage container name |

### Function Configuration
| Key | Example value | Description |
|-----|---------------|-------------|
| `AGENT_FUNC_KEY` | `YOUR-FUNCTION-KEY` | Azure Function host key |
| `PROJECT_ENDPOINT` | `https://my-project.services.ai.azure.com/...` | AI Studio project endpoint |
| `API_VERSION` | `2025-05-01-preview` | API version for search runtime |
| `MAX_OUTPUT_SIZE` | `16000` | Max output token size |
| `TOP_K` | `5` | Default number of top results |

### SharePoint Functions
| Key | Example value | Description |
|-----|---------------|-------------|
| `SHAREPOINT_INDEXER_FUNCTION_APP` | `sharepoint-indexer` | Indexer function app name |
| `SHAREPOINT_PURGER_FUNCTION_APP` | `sharepoint-purger` | Purger function app name |
| `SP_INDEXER_SCHEDULE` | `0 */15 * * * *` | Indexer schedule (every 15 min) |
| `SP_PURGER_SCHEDULE` | `0 0 2 * * *` | Purger schedule (daily at 2 AM) |
| `SHAREPOINT_FILES_FORMAT` | `pdf,docx,pptx,xlsx,txt,md,json` | Supported file formats |

> Fill these once in `.env`. The **Function Config** tab can push them to Azure Functions automatically.

---

## Required local tooling

| Tool | Purpose | Install |
|------|---------|---------|
| **Python 3.9+** | runs Streamlit UI | `pyenv`, Homebrew, Windows installer |
| **Azure CLI (`az`)** | deploy code / update app settings | <https://aka.ms/azure-cli> |
| **Git** | version control | <https://git-scm.com> |
| *(optional)* VS Code + Python ext. | editing & debugging | <https://code.visualstudio.com> |

Sign in: `az login` targeting the subscription that owns your Search, OpenAI and Function resources.

---

## Application Architecture

### Core Components
1. **📄 Document Ingestion** – Upload files via web UI or SharePoint sync with unified processing pipeline
2. **🔍 Hybrid Search** – BM25 + vector search with Azure AI Search for optimal retrieval
3. **🤖 Agentic RAG** – Knowledge agents provide contextual answers with proper citations
4. **📊 SharePoint Sync** – Automated document processing and real-time synchronization
5. **⚙️ Function Management** – Deploy and configure Azure Functions for batch processing

### Processing Pipeline
```
Document Upload → DocumentChunker → Format-Specific Processor → 
Azure Document Intelligence → Embedding Generation → Index Storage → 
Knowledge Agent Retrieval → Contextual Response
```

### Supported Document Formats
- **PDF**: Advanced OCR and layout analysis
- **DOCX/PPTX**: Native Office document processing
- **XLSX/CSV**: Intelligent spreadsheet summarization
- **TXT/MD/JSON**: Text-based format processing
- **Images**: Multimodal analysis with AI-powered captioning

---

## 🏗️ Development Guidelines

### Modular Architecture

This project enforces a **strict modular architecture** to prevent code bloat and maintain maintainability:

- **Main File Limit**: `agentic-rag-demo.py` should remain under 500 lines
- **Current Status**: 🔴 2613 lines (needs refactoring)
- **Rule**: NO new business logic should be added to the main file

### Development Workflow

Before contributing, please follow our modular development workflow:

```bash
# Check architecture compliance
python scripts/validate_modular_architecture.py

# For new features, use existing modular structure:
# - UI components → app/ui/components/ (or create app/tabs/ as needed)
# - Business logic → core/ (azure_clients.py, document_processor.py)
# - Utilities → utils/ (azure_helpers.py, file_utils.py)
# - Health checks → health_check/
# - Integrations → connectors/sharepoint/
```

**Key Resources:**
- **[Development Workflow](MODULAR_DEVELOPMENT_WORKFLOW.md)** - Complete development guidelines
- **[Architecture Guidelines](.github/copilot-instructions.md)** - Copilot instructions for modular development
- **VS Code Task**: "Validate Modular Architecture" - Quick compliance check

### Code Organization

```
📁 Current Project Structure:
├── agentic-rag-demo.py     # Main orchestration ONLY (target: <500 lines)
├── app/                    # UI components & processing
│   ├── ui/components/      # Reusable UI components ✅
│   ├── document_processing/ # Document processing modules ✅
│   ├── openai/             # OpenAI-related functionality ✅
│   └── search/             # Search-related functionality ✅
├── core/                   # Core business logic ✅
│   ├── azure_clients.py    # Azure service clients ✅
│   └── document_processor.py # Document processing ✅
├── utils/                  # Utility functions ✅
│   ├── azure_helpers.py    # Azure utilities ✅
│   ├── file_utils.py       # File operations ✅
│   └── file_format_detector.py # Format detection ✅
├── connectors/             # External integrations ✅
│   └── sharepoint/         # SharePoint integration ✅
├── health_check/           # Health check system ✅
│   ├── health_checker.py   # Health check logic ✅
│   └── health_check_ui.py  # Health check UI ✅
├── chunking/               # Document chunking system ✅
└── scripts/                # Development tools ✅
    └── validate_modular_architecture.py # Architecture validation ✅
```

**Pre-commit Hook**: Automatically validates architecture compliance before each commit.

---

## Troubleshooting

### Common Issues

**BCP177 Bicep Deployment Error** ✅ **RESOLVED**
- **Issue**: BCP177 error during AI Foundry Hub deployment with Bicep templates
- **Solution**: Automatically resolved - deployment service now uses ARM template (`main.json`) instead of Bicep (`main.bicep`)
- **Status**: No user action required - deployments work automatically
- **Verification**: Run `python3 tests/diagnostics/diagnose_sudden_bcp177.py` to confirm fix

**XLSX Processing Failures**
- Ensure `AZURE_OPENAI_CHATGPT_DEPLOYMENT` matches your actual deployment name
- Check that your Azure OpenAI deployment is accessible

**SharePoint Authentication**
- Verify tenant ID, client ID, and secret/certificate configuration
- Ensure proper SharePoint permissions are granted to your app registration

**Multimodal Processing**
- Configure Azure Storage connection string and container
- Verify Document Intelligence service is properly configured

### Error Handling
The application includes comprehensive error handling and fallback mechanisms:
- Graceful degradation when Azure OpenAI is unavailable
- Automatic retry logic for transient failures  
- Detailed logging and error reporting

---

## License

MIT – free for personal or commercial use. Never commit real secrets!
