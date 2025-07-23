import os
from typing import Any, Dict, List, Optional

from config import settings
from constants import (
    APIDefaults,
    DocumentStatus,
    ErrorCodes,
    HTTPMessages,
    ProcessingDefaults,
)
from db import get_engine
from db.models import Document
from dto.documents_dto import DocumentsDto
from dto.upload_dto import (
    DocumentListItem,
    DocumentListResponse,
    DocumentUploadResponse,
    ProcessingStatusResponse,
    SummaryRequest,
    SummaryResponse,
)
from exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentUploadError,
    validate_document_id,
    validate_file_upload,
)
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from utils.document_processor import DocumentProcessor
from utils.openai_client import OpenAISummaryClient


class DocumentsAPI:
    def __init__(self) -> None:
        self.router = APIRouter()
        self.documents_dto = DocumentsDto(get_engine())
        self.document_processor = DocumentProcessor(get_engine())
        self.summary_client = OpenAISummaryClient()

        # Document management routes
        self.router.add_api_route(
            "/upload",
            self.upload_document,
            methods=["POST"],
            response_model=DocumentUploadResponse,
            summary="Upload a PDF document",
        )

        self.router.add_api_route(
            "",
            self.list_documents,
            methods=["GET"],
            response_model=DocumentListResponse,
            summary="List all documents",
        )

        self.router.add_api_route(
            "/{document_id}",
            self.get_document,
            methods=["GET"],
            response_model=Document,
            summary="Get document by ID",
        )

        self.router.add_api_route(
            "/{document_id}/status",
            self.get_document_status,
            methods=["GET"],
            response_model=ProcessingStatusResponse,
            summary="Get document processing status",
        )

        self.router.add_api_route(
            "/{document_id}",
            self.delete_document,
            methods=["DELETE"],
            response_model=Dict[str, str],
            summary="Delete document",
        )

        self.router.add_api_route(
            "/{document_id}/summary",
            self.generate_summary,
            methods=["POST"],
            response_model=SummaryResponse,
            summary="Generate document summary",
        )

        self.router.add_api_route(
            "/{document_id}/process",
            self.process_document,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary="Process document with OpenAI Vision and Qdrant indexing",
        )

        self.router.add_api_route(
            "/processing-stats",
            self.get_processing_stats,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary="Get processing and hybrid search statistics",
        )

        self.router.add_api_route(
            "/{document_id}/reprocess",
            self.reprocess_document_endpoint,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary="Reprocess document with improved extraction",
        )

    async def upload_document(
        self, background_tasks: BackgroundTasks, file: UploadFile = File(...)
    ) -> DocumentUploadResponse:
        """Upload a PDF document for processing."""
        # Validate file upload using centralized validation
        validate_file_upload(file, settings.max_file_size)

        # Get file size (already calculated in validation)
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Seek back to start

        try:
            # Save file to disk
            file_info = self.documents_dto.save_uploaded_file(file)

            # Save document to database
            result = self.documents_dto.save_document_to_db(
                filename=file_info["filename"],
                file_size=file_size,
                file_path=file_info["file_path"],
            )

            document = result["document"]

            # Update status to processing immediately
            self.documents_dto.update_document_processing_status(
                document_id=document.document_id, status=DocumentStatus.PROCESSING
            )

            # Add background task for automatic processing
            background_tasks.add_task(
                self._process_document_background,
                document.document_id,
                document.file_path,
            )

            return DocumentUploadResponse(
                document_id=document.document_id,
                filename=document.filename,
                file_size=document.file_size,
                upload_time=document.upload_time,
                status=DocumentStatus.PROCESSING,
                message=f"{HTTPMessages.UPLOAD_SUCCESS} - {HTTPMessages.PROCESSING_STARTED}",
            )

        except Exception as e:
            raise DocumentUploadError(
                f"Failed to upload document: {str(e)}", filename=file.filename
            )

    async def list_documents(
        self,
        skip: int = Query(
            APIDefaults.DEFAULT_SKIP, ge=0, description="Number of documents to skip"
        ),
        limit: int = Query(
            ProcessingDefaults.DEFAULT_PAGINATION_LIMIT,
            ge=1,
            le=ProcessingDefaults.MAX_PAGINATION_LIMIT,
            description="Maximum number of documents to return",
        ),
    ) -> DocumentListResponse:
        """List all uploaded documents with pagination."""
        try:
            documents = self.documents_dto.list_documents(skip=skip, limit=limit)

            document_items = [
                DocumentListItem(
                    document_id=doc.document_id,
                    filename=doc.filename,
                    file_size=doc.file_size,
                    upload_time=doc.upload_time,
                    status=doc.status,
                    page_count=doc.page_count if doc.page_count > 0 else None,
                    tables_count=doc.tables_count if doc.tables_count > 0 else None,
                    figures_count=doc.figures_count if doc.figures_count > 0 else None,
                )
                for doc in documents
            ]

            return DocumentListResponse(
                documents=document_items, total=len(document_items)
            )

        except Exception as e:
            raise DocumentProcessingError(f"Failed to list documents: {str(e)}")

    async def get_document(self, document_id: str) -> Document:
        """Get document by ID."""
        # Validate document ID
        validated_id = validate_document_id(document_id)

        document = self.documents_dto.get_document(validated_id)

        if not document:
            raise DocumentNotFoundError(validated_id)

        return document

    async def get_document_status(self, document_id: str) -> ProcessingStatusResponse:
        """Get document processing status."""
        # Validate document ID
        validated_id = validate_document_id(document_id)

        try:
            progress_info = self.documents_dto.get_processing_progress(validated_id)

            return ProcessingStatusResponse(
                document_id=progress_info["document_id"],
                status=progress_info["status"],
                progress_percentage=progress_info["progress_percentage"],
                current_step=progress_info["current_step"],
                tables_count=progress_info.get("tables_count"),
                figures_count=progress_info.get("figures_count"),
                error_message=progress_info.get("error_message"),
            )

        except DocumentNotFoundError:
            raise  # Re-raise DocumentNotFoundError as-is
        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to get document status: {str(e)}", document_id=validated_id
            )

    async def delete_document(self, document_id: str) -> Dict[str, str]:
        """Delete document and all associated data."""
        # Validate document ID
        validated_id = validate_document_id(document_id)

        try:
            # Delete from vector store and database using document processor
            success = self.document_processor.delete_document_content(validated_id)

            if success:
                return {
                    "message": HTTPMessages.DELETE_SUCCESS,
                    "document_id": validated_id,
                }
            else:
                raise DocumentProcessingError(
                    "Failed to delete document from vector store",
                    document_id=validated_id,
                )

        except DocumentNotFoundError:
            raise  # Re-raise DocumentNotFoundError as-is
        except DocumentProcessingError:
            raise  # Re-raise DocumentProcessingError as-is
        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to delete document: {str(e)}", document_id=validated_id
            )

    async def process_document(
        self, document_id: str, background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """Process document using OpenAI Vision and index in Qdrant."""
        # Validate document ID
        validated_id = validate_document_id(document_id)

        try:
            # Get document to verify it exists and get file path
            document = self.documents_dto.get_document(validated_id)

            if not document:
                raise DocumentNotFoundError(validated_id)

            # Add processing task to background
            background_tasks.add_task(
                self._process_document_background, validated_id, document.file_path
            )

            return {
                "message": HTTPMessages.PROCESSING_STARTED,
                "document_id": validated_id,
                "status": DocumentStatus.PROCESSING,
            }

        except DocumentNotFoundError:
            raise  # Re-raise DocumentNotFoundError as-is
        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to start document processing: {str(e)}",
                document_id=validated_id,
            )

    async def reprocess_document(self, document_id: str) -> Dict[str, Any]:
        """Reprocess an existing document with improved extraction."""
        try:
            # Get document from database
            document = self.documents_dto.get_document_by_id(document_id)
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")

            # Check if file still exists
            if not document.file_path or not os.path.exists(document.file_path):
                raise HTTPException(
                    status_code=400, detail="Original document file not found"
                )

            # Update status to processing
            self.documents_dto.update_document_processing_status(
                document_id=document_id, status="processing"
            )

            # Reprocess with improved extraction
            result = await self.document_processor.process_document(
                document_id=document_id,
                file_path=document.file_path,
                extract_tables=True,
                extract_figures=True,
            )

            return result

        except Exception as e:
            # Update status back to completed if reprocessing fails
            self.documents_dto.update_document_processing_status(
                document_id=document_id, status="completed"
            )
            raise HTTPException(
                status_code=500, detail=f"Reprocessing failed: {str(e)}"
            )

    async def generate_summary(
        self, document_id: str, request: SummaryRequest
    ) -> SummaryResponse:
        """Generate a summary for the specified document."""
        import json
        import time
        from datetime import datetime

        # Validate document ID
        validated_id = validate_document_id(document_id)

        try:
            # Get document from database
            document = self.documents_dto.get_document(validated_id)
            if not document:
                raise DocumentNotFoundError(validated_id)

            # Check if document processing is completed
            if document.status != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Document must be processed before generating summary. Current status: {document.status}",
                )

            # Extract document content from markdown_content field
            if not document.markdown_content:
                raise HTTPException(
                    status_code=400,
                    detail="Document content not available for summary generation",
                )

            try:
                # Parse the stored MarkdownDocument JSON
                markdown_doc_data = json.loads(document.markdown_content)

                # Extract text content from all pages
                document_text = ""
                tables_text = ""
                figures_text = ""

                for page in markdown_doc_data.get("pages", []):
                    # Add main content
                    if page.get("content"):
                        document_text += f"\n\nPage {page.get('page_number', 'N/A')}:\n{page['content']}"

                    # Extract tables if requested
                    if request.include_tables_summary and page.get("tables"):
                        for table in page["tables"]:
                            # Get table metadata
                            table_metadata = table.get("metadata", {})
                            table_title = table_metadata.get("title") or table.get(
                                "title", "Untitled"
                            )
                            table_caption = table_metadata.get("caption", "")

                            tables_text += f"\nTable: {table_title}\n"
                            if table_caption:
                                tables_text += f"Caption: {table_caption}\n"

                            # Process headers - handle both structured TableHeader objects and simple strings
                            if table.get("headers") and isinstance(
                                table["headers"], list
                            ):
                                headers_list = []
                                for header in table["headers"]:
                                    if isinstance(header, dict):
                                        # Structured TableHeader object
                                        header_name = header.get(
                                            "name", str(header.get("id", ""))
                                        )
                                        headers_list.append(header_name)
                                    else:
                                        # Simple string header
                                        headers_list.append(str(header))

                                if headers_list:
                                    tables_text += (
                                        f"Headers: {', '.join(headers_list)}\n"
                                    )

                            # Process table data - handle both structured and raw content
                            table_data = table.get("data", [])
                            if table_data and len(table_data) > 0:
                                tables_text += f"Data: {len(table_data)} rows of data\n"
                                # Show first few rows as example if available
                                if len(table_data) > 0:
                                    sample_rows = table_data[:3]  # Show first 3 rows
                                    for i, row in enumerate(sample_rows):
                                        if isinstance(row, dict):
                                            row_text = ", ".join(
                                                [
                                                    f"{k}: {v}"
                                                    for k, v in row.items()
                                                    if v
                                                ]
                                            )
                                            tables_text += f"  Row {i+1}: {row_text}\n"
                                    if len(table_data) > 3:
                                        tables_text += f"  ... and {len(table_data) - 3} more rows\n"
                            else:
                                # Fallback to raw content if available
                                table_content = table.get("content", "")
                                if table_content and table_content.strip():
                                    tables_text += f"Content:\n{table_content[:500]}{'...' if len(table_content) > 500 else ''}\n"
                                else:
                                    tables_text += "Data: No data available (extraction may have failed)\n"

                    # Extract figures if requested
                    if request.include_figures_summary and page.get("figures"):
                        for figure in page["figures"]:
                            # Get figure title from different possible locations
                            figure_title = (
                                figure.get("title")
                                or figure.get("caption")
                                or f"Figure {figure.get('id', 'Unknown')}"
                            )
                            figures_text += f"\nFigure: {figure_title}\n"

                            # Get description/caption from multiple sources
                            description = (
                                figure.get("description")
                                or figure.get("caption")
                                or figure.get("content")
                            )

                            if description and description.strip():
                                figures_text += f"Description: {description}\n"
                            else:
                                figures_text += "Description: No description available (vision extraction may have failed)\n"

                # Combine all content
                full_content = document_text
                if tables_text:
                    full_content += f"\n\nTables Summary:\n{tables_text}"
                if figures_text:
                    full_content += f"\n\nFigures Summary:\n{figures_text}"

            except (json.JSONDecodeError, KeyError) as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse document content: {str(e)}",
                )

            # Generate summary using OpenAI
            summary_result = await self.summary_client.generate_summary(
                document_content=full_content,
                summary_type=request.summary_type.value,
                document_title=document.filename,
                custom_instructions=request.custom_instructions,
                include_key_points=request.include_key_points,
                include_tables_summary=request.include_tables_summary,
                include_figures_summary=request.include_figures_summary,
            )

            if not summary_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Summary generation failed: {summary_result.get('error', 'Unknown error')}",
                )

            # Build response
            summary_data = summary_result["summary"]

            # Estimate word count (rough approximation)
            word_count_estimate = len(document_text.split()) if document_text else 0

            return SummaryResponse(
                document_id=validated_id,
                filename=document.filename,
                summary_type=request.summary_type,
                title=summary_data.get("title"),
                overview=summary_data["overview"],
                sections=[],  # Could be enhanced for detailed summaries
                key_points=summary_data.get("key_points", []),
                tables_summary=(
                    tables_text
                    if request.include_tables_summary and tables_text
                    else None
                ),
                figures_summary=(
                    figures_text
                    if request.include_figures_summary and figures_text
                    else None
                ),
                total_pages=document.page_count,
                word_count_estimate=word_count_estimate,
                generation_time=summary_result["generation_time"],
                timestamp=datetime.now(),
                confidence_score=summary_result.get("confidence_score"),
                tokens_used=summary_result.get("tokens_used"),
            )

        except DocumentNotFoundError:
            raise  # Re-raise DocumentNotFoundError as-is
        except HTTPException:
            raise  # Re-raise HTTPException as-is
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to generate summary: {str(e)}"
            )

    async def _process_document_background(self, document_id: str, file_path: str):
        """Background task for document processing with OpenAI Vision extraction."""
        import logging

        logger = logging.getLogger(__name__)

        try:
            logger.info(f"🔄 Starting background processing for document {document_id}")
            logger.info(f"📄 File path: {file_path}")

            result = await self.document_processor.process_document(
                document_id=document_id,
                file_path=file_path,
                extract_tables=True,
                extract_figures=True,
            )

            if result.get("success"):
                logger.info(f"✅ Document {document_id} processed successfully!")
                logger.info(f"📊 Stats: {result['total_pages']} pages")
                logger.info(
                    f"📋 Extracted: {result['tables_extracted']} tables, {result['figures_extracted']} figures"
                )
                logger.info(f"⏱️  Processing time: {result['processing_time']:.2f}s")
            else:
                logger.error(
                    f"❌ Document {document_id} processing failed: {result.get('error')}"
                )

        except Exception as e:
            logger.error(
                f"❌ Background processing failed for document {document_id}: {str(e)}"
            )
            logger.error(f"🔍 Exception details: {type(e).__name__}")

            # Ensure document status is updated to failed
            try:
                self.documents_dto.update_document_processing_status(
                    document_id=document_id,
                    status=DocumentStatus.FAILED,
                    error_message=str(e),
                )
            except Exception as db_error:
                logger.error(f"Failed to update document status: {db_error}")

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing and hybrid search statistics."""
        try:
            stats = self.document_processor.get_processing_stats()

            if "error" in stats:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to retrieve stats: {stats['error']}",
                )

            return stats

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get processing stats: {str(e)}"
            )

    async def reprocess_document_endpoint(self, document_id: str) -> Dict[str, Any]:
        """Endpoint for reprocessing documents with improved extraction."""
        return await self.reprocess_document(document_id)
