import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings
from dto.documents_dto import DocumentsDto
from dto.openai_models import MarkdownDocument, OpenAIExtractionRequest
from utils.openai_client import OpenAIVisionClient
from utils.qdrant_client import QdrantOfficialHybridStore


class DocumentProcessor:
    """Integrated document processing pipeline with official Qdrant hybrid search."""

    def __init__(self, db_engine):
        self.openai_client = OpenAIVisionClient()
        self.vector_store = QdrantOfficialHybridStore()
        self.documents_dto = DocumentsDto(db_engine)

    async def process_document(
        self,
        document_id: str,
        file_path: str,
        extract_tables: bool = True,
        extract_figures: bool = True,
    ) -> Dict[str, Any]:
        """
        Complete document processing pipeline:
        1. Extract content using OpenAI Vision
        2. Index content in Qdrant
        3. Update database with results
        """
        start_time = time.time()

        try:
            # Update status to processing
            self.documents_dto.update_document_processing_status(
                document_id=document_id, status="processing"
            )

            # Step 1: Extract content using OpenAI Vision
            print(f"Starting OpenAI vision extraction for document {document_id}")

            extraction_request = OpenAIExtractionRequest(
                file_path=file_path,
                document_id=document_id,
                extract_tables=extract_tables,
                extract_figures=extract_figures,
            )

            extraction_response = await self.openai_client.extract_document_content(
                extraction_request
            )
            markdown_document = extraction_response.markdown_document

            print(
                f"OpenAI extraction completed in {extraction_response.processing_time:.2f}s"
            )
            print(f"Extracted {extraction_response.total_pages} pages")

            # Check if we have valid content to index
            if not markdown_document or not markdown_document.pages:
                print(
                    f"No content extracted from document {document_id}, skipping Qdrant indexing"
                )
                total_chunks = 0
            else:
                # Check if pages have actual content (text, tables, or figures)
                pages_with_content = []
                for page in markdown_document.pages:
                    # Check for text content
                    page_content = getattr(page, "markdown_content", "") or getattr(
                        page, "content", ""
                    )
                    has_text = page_content and page_content.strip()

                    # Check for tables
                    tables = getattr(page, "tables", []) or []
                    has_tables = len(tables) > 0

                    # Check for figures
                    figures = getattr(page, "figures", []) or []
                    has_figures = len(figures) > 0

                    # Page has content if it has text, tables, or figures
                    if has_text or has_tables or has_figures:
                        pages_with_content.append(page)

                if not pages_with_content:
                    print(
                        f"No pages with content found in document {document_id}, skipping Qdrant indexing"
                    )
                    total_chunks = 0
                else:
                    # Step 2: Index content in Qdrant
                    print(
                        f"Starting Qdrant indexing for document {document_id} with {len(pages_with_content)} pages"
                    )

                    try:
                        total_chunks = self.vector_store.index_document(
                            document_id=document_id,
                            filename=file_path.split("/")[
                                -1
                            ],  # Extract filename from path
                            markdown_doc_data=markdown_document.dict(),
                        )

                        print(f"Indexed {total_chunks} chunks in Qdrant")

                    except Exception as qdrant_error:
                        print(f"Qdrant indexing failed: {qdrant_error}")
                        # Continue with processing even if Qdrant indexing fails
                        total_chunks = 0

            # Step 3: Calculate document statistics
            processing_time = time.time() - start_time

            # Step 4: Update document with processing results
            updated_doc = self.documents_dto.update_document_processing_status(
                document_id=document_id,
                status="completed",
                processing_time=processing_time,
                tables_count=len(markdown_document.get_all_tables()),
                figures_count=len(markdown_document.get_all_figures()),
                openai_tokens_used=extraction_response.total_tokens_used,
            )

            # Update document metadata if extracted
            if markdown_document.pages:
                first_page = markdown_document.pages[0]

                # Serialize MarkdownDocument to JSON for storage
                markdown_content_json = json.dumps(markdown_document.dict())

                self.documents_dto.update_document_metadata(
                    document_id=document_id,
                    page_count=len(markdown_document.pages),
                    language=(
                        first_page.metadata.language if first_page.metadata else "en"
                    ),
                    markdown_content=markdown_content_json,
                )
            else:
                # Update with minimal metadata if no content was extracted
                self.documents_dto.update_document_metadata(
                    document_id=document_id,
                    page_count=0,
                    language="unknown",
                    markdown_content=None,
                )

            return {
                "success": True,
                "document_id": document_id,
                "processing_time": processing_time,
                "total_pages": len(markdown_document.pages),
                "total_chunks": total_chunks,
                "openai_tokens": extraction_response.total_tokens_used,
                "tables_extracted": len(markdown_document.get_all_tables()),
                "figures_extracted": len(markdown_document.get_all_figures()),
                "status": "completed",
            }

        except Exception as e:
            # Update status to failed
            error_message = str(e)
            processing_time = time.time() - start_time

            self.documents_dto.update_document_processing_status(
                document_id=document_id,
                status="failed",
                processing_time=processing_time,
                error_message=error_message,
            )

            return {
                "success": False,
                "document_id": document_id,
                "error": error_message,
                "processing_time": processing_time,
            }

    def search_document_content(
        self,
        query: str,
        document_id: Optional[str] = None,
        limit: int = 10,
        include_tables: bool = True,
        include_figures: bool = True,
        use_hybrid_search: bool = True,
        score_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Search document content using official Qdrant hybrid search or dense-only search.

        Args:
            query: Search query
            document_id: Limit search to specific document
            limit: Maximum results to return
            include_tables: Include table content in search
            include_figures: Include figure content in search
            use_hybrid_search: Whether to use hybrid search (official Qdrant approach)
            score_threshold: Minimum score threshold (uses defaults if None)
        """

        # Determine chunk types to search
        chunk_types = ["text"]
        if include_tables:
            chunk_types.append("table")
        if include_figures:
            chunk_types.append("figure")

        # Use appropriate score threshold
        if score_threshold is None:
            score_threshold = 0.3 if use_hybrid_search else 0.7

        try:
            if use_hybrid_search:
                # Use official Qdrant hybrid search with SPLADE + dense embeddings
                return self.vector_store.hybrid_search(
                    query=query,
                    document_id=document_id,
                    chunk_types=chunk_types,
                    limit=limit,
                    score_threshold=score_threshold,
                )
            else:
                # Fallback to dense-only search
                return self.vector_store.search_documents(
                    query=query,
                    document_id=document_id,
                    chunk_types=chunk_types,
                    limit=limit,
                    score_threshold=score_threshold,
                )

        except Exception as e:
            logger.warning(f"Search failed, trying fallback: {e}")
            # Ultimate fallback to dense-only search
            return self.vector_store.search_documents(
                query=query,
                document_id=document_id,
                chunk_types=chunk_types,
                limit=limit,
                score_threshold=0.7,
            )

    def delete_document_content(self, document_id: str) -> bool:
        """Delete document content from Qdrant and database."""
        qdrant_success = False
        database_success = False

        try:
            # Delete from Qdrant first
            print(f"Deleting document {document_id} from Qdrant vector store...")
            qdrant_success = self.vector_store.delete_document(document_id)

            if qdrant_success:
                print(f"✅ Successfully deleted document {document_id} from Qdrant")
            else:
                print(f"⚠️ Failed to delete document {document_id} from Qdrant")

        except Exception as qdrant_error:
            print(
                f"❌ Qdrant deletion error for document {document_id}: {qdrant_error}"
            )
            qdrant_success = False

        try:
            # Delete from database (always attempt this even if Qdrant fails)
            print(f"Deleting document {document_id} from database...")
            self.documents_dto.delete_document(document_id)
            database_success = True
            print(f"✅ Successfully deleted document {document_id} from database")

        except Exception as db_error:
            print(f"❌ Database deletion error for document {document_id}: {db_error}")
            database_success = False

        # Return True only if both operations succeeded
        overall_success = qdrant_success and database_success

        if not overall_success:
            error_details = []
            if not qdrant_success:
                error_details.append("Qdrant deletion failed")
            if not database_success:
                error_details.append("Database deletion failed")
            print(
                f"❌ Document deletion incomplete for {document_id}: {', '.join(error_details)}"
            )

        return overall_success

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing and indexing statistics for official hybrid search."""
        try:
            qdrant_stats = self.vector_store.get_collection_stats()

            return {
                "qdrant_collection_stats": qdrant_stats,
                "hybrid_search": {
                    "approach": "official_qdrant_fastembed",
                    "dense_model": self.vector_store.DENSE_MODEL,
                    "sparse_model": self.vector_store.SPARSE_MODEL,
                    "fusion_method": "reciprocal_rank_fusion",
                    "native_qdrant_fusion": True,
                },
                "openai_vision_model": self.openai_client.model,
                "smart_chunking": {
                    "chunk_size": 600,
                    "chunk_overlap": 100,
                    "min_chunk_size": 50,
                },
            }

        except Exception as e:
            return {"error": str(e)}

    async def process_document_batch(
        self, document_ids: list[str], file_paths: list[str]
    ) -> Dict[str, Any]:
        """Process multiple documents concurrently."""
        if len(document_ids) != len(file_paths):
            raise ValueError("Document IDs and file paths lists must be same length")

        tasks = []
        for doc_id, file_path in zip(document_ids, file_paths):
            task = self.process_document(doc_id, file_path)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in results if isinstance(r, dict) and r.get("success")
        )
        failed_count = len(results) - success_count

        return {
            "total_documents": len(document_ids),
            "successful": success_count,
            "failed": failed_count,
            "results": results,
        }
