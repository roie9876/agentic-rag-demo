import logging
import os
import asyncio
import time
from connectors import SharePointDataReader
from tools import KeyVaultClient
from tools import AISearchClient
from typing import Any, Dict, List, Optional
import base64

class SharepointFilesIndexer:
    def __init__(self, index_name: Optional[str] = None):
        # Initialize configuration from environment variables
        self.connector_enabled = os.getenv("SHAREPOINT_CONNECTOR_ENABLED", "false").lower() == "true"
        self.tenant_id = os.getenv("SHAREPOINT_TENANT_ID")
        self.client_id = os.getenv("SHAREPOINT_CLIENT_ID")
        self.site_domain = os.getenv("SHAREPOINT_SITE_DOMAIN")
        # Empty, "/", or whitespace → treat as root site
        self.site_name = os.getenv("SHAREPOINT_SITE_NAME", "").strip() or "root"
        self.folder_path = os.getenv("SHAREPOINT_SITE_FOLDER", "/")
        self.sharepoint_client_secret_name = os.getenv("SHAREPOINT_CLIENT_SECRET_NAME", "sharepointClientSecret")
        env_index = os.getenv("AZURE_SEARCH_SHAREPOINT_INDEX_NAME")
        # If caller supplies an index name (e.g. chosen in the UI) – use it; else fall back to env/default
        self.index_name = (
            index_name.strip()
            if index_name and index_name.strip()
            else (env_index.strip() if env_index and env_index.strip() else "ragindex")
        )
        self.file_formats = os.getenv("SHAREPOINT_FILES_FORMAT")
        if self.file_formats:
            # Convert comma-separated string into a list, trimming whitespace
            self.file_formats = [fmt.strip() for fmt in self.file_formats.split(",")]
        else:
            # By default, handle common document formats including PPTX
            self.file_formats = ["pdf", "docx", "pptx", "xlsx", "txt", "md", "json"]
        # When true we skip Document Intelligence and store the whole file as one record
        self.direct_index = os.getenv("SHAREPOINT_INDEX_DIRECT", "false").lower() == "true"
        self.keyvault_client: Optional[KeyVaultClient] = None
        self.client_secret: Optional[str] = None
        self.sharepoint_data_reader: Optional[SharePointDataReader] = None
        self.search_client: Optional[AISearchClient] = None
        
        # Processing statistics tracking
        self.processing_stats = {
            "processed_files": [],    # List of successfully processed files with details
            "skipped_files": [],      # List of skipped files with reasons
            "failed_files": [],       # List of files that failed processing
            "total_chunks": 0,        # Total number of chunks created
            "start_time": None,       # Processing start time
            "end_time": None,         # Processing end time
            "methods_used": {}        # Track which extraction methods were used
        }

    async def initialize_clients(self) -> bool:
        """Initialize KeyVaultClient, retrieve secrets, and initialize SharePointDataReader and AISearchClient."""
        # Initialize Key Vault Client and retrieve SharePoint client secret
        keyvault_client = None
        try:
            keyvault_client = KeyVaultClient()
            self.client_secret = await keyvault_client.get_secret(self.sharepoint_client_secret_name)
            logging.debug("[sharepoint_files_indexer] Retrieved sharepointClientSecret secret from Key Vault.")
        except Exception as e:
            logging.error(f"[sharepoint_files_indexer] Failed to retrieve secret from Key Vault: {e}")
            return False
        finally:
            if keyvault_client:
                await keyvault_client.close()
        # Check for missing environment variables
        required_vars = {
            "SHAREPOINT_TENANT_ID": self.tenant_id,
            "SHAREPOINT_CLIENT_ID": self.client_id,
            "SHAREPOINT_SITE_DOMAIN": self.site_domain,
        }
        missing_env_vars = [var for var, value in required_vars.items() if not value]
        if missing_env_vars:
            logging.error(
                f"[sharepoint_files_indexer] Missing environment variables: {', '.join(missing_env_vars)}. "
                "Please set all required environment variables."
            )
            return False
        if not self.client_secret:
            logging.error(
                "[sharepoint_files_indexer] SharePoint connector secret is not properly configured. "
                "Missing secret: sharepointClientSecret. Please set the required secret in Key Vault."
            )
            return False
        # Initialize SharePointDataReader
        try:
            self.sharepoint_data_reader = SharePointDataReader(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            self.sharepoint_data_reader._msgraph_auth()
            logging.debug("[sharepoint_files_indexer] Authenticated with Microsoft Graph successfully.")
        except Exception as e:
            logging.error(f"[sharepoint_files_indexer] Authentication failed: {e}")
            return False
        # Initialize AISearchClient
        try:
            self.search_client = AISearchClient()
            logging.debug("[sharepoint_files_indexer] Initialized AISearchClient successfully.")
        except ValueError as ve:
            logging.error(f"[sharepoint_files_indexer] AISearchClient initialization failed: {ve}")
            return False
        except Exception as e:
            logging.error(f"[sharepoint_files_indexer] Unexpected error during AISearchClient initialization: {e}")
            return False
        return True

    async def delete_existing_chunks(self, existing_chunks: Dict[str, Any], file_name: str) -> None:
        """Delete existing document chunks from the search index."""
        chunk_ids = [doc['id'] for doc in existing_chunks.get('documents', []) if 'id' in doc]
        if not chunk_ids:
            logging.warning(f"[sharepoint_files_indexer] No valid 'id's found for existing chunks of '{file_name}'. Skipping deletion.")
            return
        try:
            await self.search_client.delete_documents(index_name=self.index_name, key_field="id", key_values=chunk_ids)
            logging.debug(f"[sharepoint_files_indexer] Deleted {len(chunk_ids)} existing chunks for '{file_name}'.")
        except Exception as e:
            logging.error(f"[sharepoint_files_indexer] Failed to delete existing chunks for '{file_name}': {e}")

    async def index_file(self, data: Dict[str, Any]) -> None:
        """Index a single file's metadata into the search index."""
        try:
            await self.search_client.index_document(index_name=self.index_name, document=data)
            logging.debug(f"[sharepoint_files_indexer] Indexed file '{data['fileName']}' successfully.")
        except Exception as e:
            logging.error(f"[sharepoint_files_indexer] Failed to index file '{data['fileName']}': {e}")

    async def process_file(self, file: Dict[str, Any], semaphore: asyncio.Semaphore) -> None:
        """Process and index a single SharePoint file."""
        async with semaphore:
            file_name = file.get("name")
            if not file_name:
                logging.warning("[sharepoint_files_indexer] File name is missing. Skipping file.")
                self._track_file_skipped("Unknown", "File name is missing")
                return

            sharepoint_id = file.get("id")
            document_bytes = file.get("content")
            document_url = file.get("source")
            last_modified_datetime = file.get("last_modified_datetime")
            read_access_entity = file.get("read_access_entity")
            file_size = len(document_bytes) if isinstance(document_bytes, (bytes, bytearray)) else 0

            logging.info(f"[sharepoint_files_indexer] Processing File: {file_name}. Last Modified: {last_modified_datetime}")

            # Check if file has content
            if not document_bytes:
                self._track_file_skipped(file_name, "No content", file_size)
                logging.warning(f"[sharepoint_files_indexer] No content for file '{file_name}'. Skipping.")
                return

            data = {
                "sharepointId": sharepoint_id,
                "fileName": file_name,
                "documentBytes": document_bytes,
                "documentUrl": document_url
            }

            # Decide which search filter to use (whole‑doc vs. chunks)
            filter_str = (
                f"id eq '{sharepoint_id}' and source eq 'sharepoint'"
                if self.direct_index
                else f"parent_id eq '{sharepoint_id}' and source eq 'sharepoint'"
            )

            # Fetch existing chunks related to the file
            try:
                existing_chunks = await self.search_client.search_documents(
                    index_name=self.index_name,
                    search_text="*",
                    filter_str=filter_str,
                    select_fields=['id', 'metadata_storage_last_modified', 'metadata_storage_name'],
                    top=1
                )
            except Exception as e:
                logging.error(f"[sharepoint_files_indexer] Failed to search existing chunks for '{file_name}': {e}")
                self._track_file_failed(file_name, f"Search failed: {str(e)}", file_size)
                return

            if existing_chunks.get('count', 0) == 0:
                logging.debug(f"[sharepoint_files_indexer] No existing chunks found for '{file_name}'. Proceeding to index.")
            else:
                indexed_last_modified_str = existing_chunks['documents'][0].get('metadata_storage_last_modified')

                if not indexed_last_modified_str:
                    logging.warning(
                        f"[sharepoint_files_indexer] 'metadata_storage_last_modified' not found for existing chunks of '{file_name}'. "
                        "Deleting existing chunks and proceeding to re-index."
                    )
                    if self.direct_index:
                        await self.search_client.delete_documents(
                            index_name=self.index_name,
                            key_field="id",
                            key_values=[sharepoint_id],
                        )
                    else:
                        await self.delete_existing_chunks(existing_chunks, file_name)
                else:
                    # Compare modification times
                    if last_modified_datetime <= indexed_last_modified_str:
                        logging.info(f"[sharepoint_files_indexer] '{file_name}' has not been modified since last indexing. Skipping.")
                        self._track_file_skipped(file_name, "No modifications since last indexing", file_size)
                        return  # Skip indexing as no changes detected
                    else:
                        # If the file has been modified, delete existing chunks and re-index
                        logging.debug(f"[sharepoint_files_indexer] '{file_name}' has been modified. Deleting existing chunks and re-indexing.")
                        if self.direct_index:
                            await self.search_client.delete_documents(
                                index_name=self.index_name,
                                key_field="id",
                                key_values=[sharepoint_id],
                            )
                        else:
                            await self.delete_existing_chunks(existing_chunks, file_name)

            # ---------- direct index path ----------
            if self.direct_index:
                document_record = {
                    "id": sharepoint_id,
                    "fileName": file_name,
                    "metadata_storage_name": file_name,
                    "metadata_storage_path": document_url,
                    "url": document_url,
                    "metadata_storage_last_modified": last_modified_datetime,
                    "metadata_security_id": read_access_entity,
                    "source": "sharepoint",
                    # keep bytes JSON‑safe
                    "documentBytes": (
                        base64.b64encode(document_bytes).decode("utf-8")
                        if isinstance(document_bytes, (bytes, bytearray))
                        else document_bytes
                    ),
                }
                # --- guarantee mandatory schema fields ---
                mandatory = [
                    "id",
                    "fileName",
                    "metadata_storage_name",
                    "metadata_storage_path",
                    "metadata_storage_last_modified",
                    "metadata_security_id",
                    "source",
                    "url",
                ]
                for fld in mandatory:
                    document_record.setdefault(fld, "")
                # -----------------------------------------
                try:
                    await self.search_client.index_document(self.index_name, document_record)
                    logging.info(
                        f"[sharepoint_files_indexer] Indexed '{file_name}' directly (no Document Intelligence)."
                    )
                    # Track successful processing (direct mode = 1 chunk)
                    self._track_file_processed(file_name, 1, "direct_index", file_size, False)
                except Exception as e:
                    logging.error(
                        f"[sharepoint_files_indexer] Failed to index '{file_name}': {e}"
                    )
                    self._track_file_failed(file_name, str(e), file_size)
                return  # skip the chunking path
            # ---------- end direct index path ----------

            # ---------- chunk & embed path (non‑direct_index) ----------
            # Use DocumentChunker for consistent processing across all file types
            try:
                ext = os.path.splitext(file_name)[-1].lower()
                
                # Enable multimodal processing for supported file types
                multimodal_env = os.getenv("MULTIMODAL", "false").lower() in ["true", "1", "yes"]
                multimodal_enabled = multimodal_env and ext in ('.pdf', '.png', '.jpeg', '.jpg', '.bmp', '.tiff', '.docx', '.pptx')
                
                # Create DocumentChunker instance
                from chunking import DocumentChunker
                dc = DocumentChunker(multimodal=multimodal_enabled, openai_client=None)
                
                # Prepare data in the format expected by DocumentChunker
                data = {
                    "fileName": file_name,
                    "documentBytes": base64.b64encode(document_bytes).decode("utf-8") if isinstance(document_bytes, bytes) else document_bytes,
                    "documentUrl": document_url or "",
                }
                
                # Process the document
                chunks, errors, warnings = dc.chunk_documents(data)
                
                if errors:
                    logging.error(f"[sharepoint_files_indexer] Chunking errors for '{file_name}': {errors}")
                if warnings:
                    logging.warning(f"[sharepoint_files_indexer] Chunking warnings for '{file_name}': {warnings}")
                    
            except Exception as e:
                logging.error(
                    f"[sharepoint_files_indexer] Failed to create DocumentChunker for '{file_name}' (ext={ext}). "
                    f"Error: {e}"
                )
                self._track_file_failed(file_name, f"DocumentChunker failed: {str(e)}", file_size)
                return

            if not chunks:
                logging.warning(
                    f"[sharepoint_files_indexer] No chunks produced for '{file_name}'."
                )
                self._track_file_skipped(file_name, "No chunks produced", file_size)
                return

            # Convert DocumentChunker output to SharePoint index schema format
            processed_chunks = []
            for i, ch in enumerate(chunks):
                # Extract text content (DocumentChunker uses different field names)
                content = ch.get("page_chunk") or ch.get("chunk") or ch.get("content") or ""
                if not content:
                    continue
                    
                # Create a properly formatted chunk for the SharePoint index
                processed_chunk = {
                    "id": ch.get("id") or f"{sharepoint_id}_{i}",
                    "page_chunk": content,
                    "page_number": ch.get("page_number") or i + 1,
                    "source_file": file_name,
                    "source": file_name,
                    "url": document_url,
                    "doc_key": file_name,
                    # SharePoint-specific metadata
                    "parent_id": sharepoint_id,
                    "metadata_storage_path": document_url,
                    "metadata_storage_name": file_name,
                    "metadata_storage_last_modified": last_modified_datetime,
                    "metadata_security_id": read_access_entity,
                    # Enhanced metadata from DocumentChunker
                    "extraction_method": ch.get("extraction_method", "document_chunker"),
                    "document_type": ch.get("document_type", "Unknown"),
                    "has_figures": ch.get("has_figures", False),
                    "processing_timestamp": ch.get("processing_timestamp", ""),
                    # Multimodal fields (if present)
                    "content": ch.get("content", content),
                    "imageCaptions": ch.get("imageCaptions", ""),
                    "relatedImages": ch.get("relatedImages", []),
                    "isMultimodal": ch.get("isMultimodal", False),
                    "filename": ch.get("filename", file_name),
                    # Ensure we have the required embedding field (will be generated during indexing)
                    "page_embedding_text_3_large": ch.get("page_embedding_text_3_large", []),
                }
                
                # Add vectors if available
                if ch.get("contentVector"):
                    processed_chunk["contentVector"] = ch["contentVector"]
                if ch.get("captionVector"):
                    processed_chunk["captionVector"] = ch["captionVector"]
                    
                processed_chunks.append(processed_chunk)

            # enrich each chunk with uniform metadata expected by the index schema
            for i, ch in enumerate(processed_chunks):
                ch.update(
                    {
                        "parent_id": sharepoint_id,
                        "metadata_storage_path": document_url,
                        "metadata_storage_name": file_name,
                        "metadata_storage_last_modified": last_modified_datetime,
                        "metadata_security_id": read_access_entity,
                        "source": "sharepoint",
                        "url": document_url,
                    }
                )
                # guarantee minimal required fields
                ch.setdefault("id", f"{sharepoint_id}_{i}")
                ch.setdefault("page_number", i + 1)
                ch.setdefault("source_file", file_name)
                ch.setdefault("page_embedding_text_3_large", [])

            # upload in bulk
            try:
                await self.search_client.upload_documents(
                    index_name=self.index_name, documents=processed_chunks
                )
                logging.info(
                    f"[sharepoint_files_indexer] Indexed {len(processed_chunks)} chunks for '{file_name}' using DocumentChunker."
                )
                
                # Track successful processing with statistics
                extraction_method = processed_chunks[0].get("extraction_method", "document_chunker") if processed_chunks else "document_chunker"
                has_multimodal = any(chunk.get("isMultimodal", False) for chunk in processed_chunks)
                self._track_file_processed(file_name, len(processed_chunks), extraction_method, file_size, has_multimodal)
                
            except Exception as e:
                logging.error(
                    f"[sharepoint_files_indexer] Failed to upload chunks for '{file_name}': {e}"
                )
                self._track_file_failed(file_name, f"Upload failed: {str(e)}", file_size)

    def _track_file_processed(self, file_name: str, chunks_count: int, extraction_method: str, 
                             file_size: int = 0, multimodal: bool = False) -> None:
        """Track a successfully processed file."""
        file_ext = os.path.splitext(file_name)[-1].lower()
        self.processing_stats["processed_files"].append({
            "name": file_name,
            "extension": file_ext,
            "chunks": chunks_count,
            "extraction_method": extraction_method,
            "file_size": file_size,
            "multimodal": multimodal
        })
        self.processing_stats["total_chunks"] += chunks_count
        
        # Track method usage
        if extraction_method not in self.processing_stats["methods_used"]:
            self.processing_stats["methods_used"][extraction_method] = 0
        self.processing_stats["methods_used"][extraction_method] += 1

    def _track_file_skipped(self, file_name: str, reason: str, file_size: int = 0) -> None:
        """Track a skipped file."""
        file_ext = os.path.splitext(file_name)[-1].lower()
        self.processing_stats["skipped_files"].append({
            "name": file_name,
            "extension": file_ext,
            "reason": reason,
            "file_size": file_size
        })

    def _track_file_failed(self, file_name: str, error: str, file_size: int = 0) -> None:
        """Track a failed file."""
        file_ext = os.path.splitext(file_name)[-1].lower()
        self.processing_stats["failed_files"].append({
            "name": file_name,
            "extension": file_ext,
            "error": error,
            "file_size": file_size
        })

    def generate_processing_report(self) -> Dict[str, Any]:
        """Generate a comprehensive processing report."""
        if not self.processing_stats["start_time"] or not self.processing_stats["end_time"]:
            import time
            self.processing_stats["end_time"] = time.time()
            
        duration = (self.processing_stats["end_time"] - self.processing_stats["start_time"]) if self.processing_stats["start_time"] else 0
        
        # Calculate summary statistics
        total_files = len(self.processing_stats["processed_files"]) + len(self.processing_stats["skipped_files"]) + len(self.processing_stats["failed_files"])
        success_rate = (len(self.processing_stats["processed_files"]) / total_files * 100) if total_files > 0 else 0
        
        # Group by file extension
        extensions_processed = {}
        for file_info in self.processing_stats["processed_files"]:
            ext = file_info["extension"]
            if ext not in extensions_processed:
                extensions_processed[ext] = {"count": 0, "chunks": 0, "methods": set()}
            extensions_processed[ext]["count"] += 1
            extensions_processed[ext]["chunks"] += file_info["chunks"]
            extensions_processed[ext]["methods"].add(file_info["extraction_method"])
        
        # Convert sets to lists for JSON serialization
        for ext_info in extensions_processed.values():
            ext_info["methods"] = list(ext_info["methods"])
        
        return {
            "summary": {
                "total_files": total_files,
                "processed_files": len(self.processing_stats["processed_files"]),
                "skipped_files": len(self.processing_stats["skipped_files"]),
                "failed_files": len(self.processing_stats["failed_files"]),
                "total_chunks": self.processing_stats["total_chunks"],
                "success_rate": round(success_rate, 2),
                "duration_seconds": round(duration, 2),
                "index_name": self.index_name,
                "processing_mode": "direct_index" if self.direct_index else "chunked_processing"
            },
            "processing_methods": self.processing_stats["methods_used"],
            "extensions_processed": extensions_processed,
            "processed_files": self.processing_stats["processed_files"],
            "skipped_files": self.processing_stats["skipped_files"],
            "failed_files": self.processing_stats["failed_files"],
            "configuration": {
                "site_domain": self.site_domain,
                "site_name": self.site_name,
                "folder_path": self.folder_path,
                "file_formats": self.file_formats,
                "direct_index": self.direct_index
            }
        }

    def print_processing_report(self) -> None:
        """Print a formatted processing report to the console."""
        report = self.generate_processing_report()
        
        print("\n" + "="*80)
        print("📊 SHAREPOINT INDEXING PROCESSING REPORT")
        print("="*80)
        
        # Summary
        summary = report["summary"]
        print(f"📋 Summary:")
        print(f"   • Index: {summary['index_name']}")
        print(f"   • Processing Mode: {summary['processing_mode']}")
        print(f"   • Total Files: {summary['total_files']}")
        print(f"   • Successfully Processed: {summary['processed_files']} ({summary['success_rate']}%)")
        print(f"   • Skipped: {summary['skipped_files']}")
        print(f"   • Failed: {summary['failed_files']}")
        print(f"   • Total Chunks Created: {summary['total_chunks']}")
        print(f"   • Processing Time: {summary['duration_seconds']} seconds")
        
        # Processing methods used
        if report["processing_methods"]:
            print(f"\n🔧 Processing Methods Used:")
            for method, count in report["processing_methods"].items():
                print(f"   • {method}: {count} files")
        
        # Extensions processed
        if report["extensions_processed"]:
            print(f"\n📁 File Extensions Processed:")
            for ext, info in report["extensions_processed"].items():
                methods_str = ", ".join(info["methods"])
                print(f"   • {ext}: {info['count']} files, {info['chunks']} chunks ({methods_str})")
        
        # Detailed file listings
        if report["processed_files"]:
            print(f"\n✅ Successfully Processed Files ({len(report['processed_files'])}):")
            for file_info in report["processed_files"]:
                multimodal_indicator = " 🎨" if file_info.get("multimodal", False) else ""
                print(f"   • {file_info['name']} - {file_info['chunks']} chunks ({file_info['extraction_method']}){multimodal_indicator}")
        
        if report["skipped_files"]:
            print(f"\n⚠️ Skipped Files ({len(report['skipped_files'])}):")
            for file_info in report["skipped_files"]:
                print(f"   • {file_info['name']} - {file_info['reason']}")
        
        if report["failed_files"]:
            print(f"\n❌ Failed Files ({len(report['failed_files'])}):")
            for file_info in report["failed_files"]:
                print(f"   • {file_info['name']} - {file_info['error']}")
        
        print("="*80)

    async def run(self) -> None:
        """Main method to run the SharePoint files indexing process."""
        import time
        self.processing_stats["start_time"] = time.time()
        
        logging.info("[sharepoint_files_indexer] Started sharepoint files index run.")

        if not self.connector_enabled:
            logging.info("[sharepoint_files_indexer] SharePoint connector is disabled. Set SHAREPOINT_CONNECTOR_ENABLED to 'true' to enable the connector.")
            return

        # Initialize clients and configurations
        if not await self.initialize_clients():
            return

        # Retrieve SharePoint files content
        try:
            files = self.sharepoint_data_reader.retrieve_sharepoint_files_content(
                site_domain=self.site_domain,
                site_name=self.site_name,
                folder_path=self.folder_path,
                file_formats=self.file_formats,
            )
            number_files = len(files) if files else 0
            logging.info(f"[sharepoint_files_indexer] Retrieved {number_files} files from SharePoint.")
        except Exception as e:
            logging.error(f"[sharepoint_files_indexer] Failed to retrieve files. Check your sharepoint configuration environment variables. Error: {e}")
            return

        if not files:
            logging.info("[sharepoint_files_indexer] No files retrieved from SharePoint.")
            await self.search_client.close()
            return

        semaphore = asyncio.Semaphore(10)  # Limit concurrent file processing

        # Create tasks to process all files in parallel
        tasks = [self.process_file(file, semaphore) for file in files]
        await asyncio.gather(*tasks)

        # Close the AISearchClient
        try:
            await self.search_client.close()
            logging.debug("[sharepoint_files_indexer] Closed AISearchClient successfully.")
        except Exception as e:
            logging.error(f"[sharepoint_files_indexer] Failed to close AISearchClient: {e}")

        # Mark end time and generate report
        self.processing_stats["end_time"] = time.time()
        
        logging.info("[sharepoint_files_indexer] SharePoint connector finished.")
        
        # Generate and print the processing report
        self.print_processing_report()
        
        # Also return the report data for programmatic access
        return self.generate_processing_report()

# Example usage
# To run the indexer, you would typically do the following in an async context:

# import asyncio
# 
# if __name__ == "__main__":
#     indexer = SharepointFilesIndexer()
#     asyncio.run(indexer.run())
