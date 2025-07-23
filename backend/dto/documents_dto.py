import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import settings
from db.models import Conversation, Document
from fastapi import UploadFile
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select


class DocumentContent(BaseModel):
    """Document content model for updates."""

    author: Optional[str] = None
    subject: Optional[str] = None


class DocumentsDto:
    def __init__(self, db_engine):
        self.__db_engine = db_engine

    def save_document_to_db(
        self,
        filename: str,
        file_size: int,
        file_path: str,
        document_id: Optional[str] = None,
    ) -> Dict[str, any]:
        """Save uploaded document to database."""
        with Session(self.__db_engine) as session:
            if document_id:
                # Update existing document
                found_document = session.get(Document, document_id)
                if found_document is not None:
                    found_document.filename = filename
                    found_document.file_size = file_size
                    found_document.file_path = file_path
                    found_document.status = "pending"
                    found_document.upload_time = datetime.now()

                    session.add(found_document)
                    session.commit()
                    session.refresh(found_document)

                    return {
                        "message": "Document updated successfully",
                        "document": found_document,
                    }

            # Create new document
            new_document_id = document_id or str(uuid.uuid4())
            new_document = Document(
                document_id=new_document_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                status="pending",
            )

            session.add(new_document)
            session.commit()
            session.refresh(new_document)

            return {
                "message": "Document uploaded successfully",
                "document": new_document,
            }

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        with Session(self.__db_engine) as session:
            document = session.get(Document, document_id)
            return document

    def list_documents(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """List all documents with pagination."""
        with Session(self.__db_engine) as session:
            result = session.exec(
                select(Document)
                .order_by(Document.upload_time.desc())
                .offset(skip)
                .limit(limit)
            ).all()
            return result

    def update_document_processing_status(
        self,
        document_id: str,
        status: str,  # "pending", "processing", "completed", "failed"
        processing_time: Optional[float] = None,
        tables_count: Optional[int] = None,
        figures_count: Optional[int] = None,
        openai_tokens_used: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Document:
        """Update document processing status."""
        with Session(self.__db_engine) as session:
            document = session.get(Document, document_id)

            if document is None:
                raise HTTPException(status_code=404, detail="Document not found")

            document.status = status

            if status == "processing":
                document.processing_started_at = datetime.now()
            elif status in ["completed", "failed"]:
                document.processing_completed_at = datetime.now()
                if processing_time:
                    document.processing_time = processing_time
                if tables_count:
                    document.tables_count = tables_count
                if figures_count:
                    document.figures_count = figures_count
                if openai_tokens_used:
                    document.openai_tokens_used = openai_tokens_used
                if error_message:
                    document.error_message = error_message

            session.add(document)
            session.commit()
            session.refresh(document)

            return document

    def update_document_metadata(
        self,
        document_id: str,
        page_count: Optional[int] = None,
        language: Optional[str] = None,
        markdown_content: Optional[str] = None,
    ) -> Document:
        """Update document metadata."""
        with Session(self.__db_engine) as session:
            document = session.get(Document, document_id)

            if document is None:
                raise HTTPException(status_code=404, detail="Document not found")

            if page_count is not None:
                document.page_count = page_count
            if language is not None:
                document.language = language
            if markdown_content is not None:
                document.markdown_content = markdown_content

            session.add(document)
            session.commit()
            session.refresh(document)

            return document

    def delete_document(self, document_id: str) -> Dict[str, str]:
        """Delete document and associated files."""
        with Session(self.__db_engine) as session:
            document = session.get(Document, document_id)

            if document is None:
                raise HTTPException(status_code=404, detail="Document not found")

            # Delete associated file
            try:
                if os.path.exists(document.file_path):
                    os.remove(document.file_path)
            except Exception as e:
                # Log error but continue with database deletion
                print(f"Error deleting file {document.file_path}: {e}")

            # Delete from database (cascades to chunks and conversations)
            session.delete(document)
            session.commit()

            return {
                "message": "Document deleted successfully",
                "document_id": document_id,
            }

    def save_uploaded_file(self, file: UploadFile) -> Dict[str, str]:
        """Save uploaded file to disk."""
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.upload_dir, unique_filename)

        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            return {
                "file_path": file_path,
                "filename": file.filename,
                "saved_filename": unique_filename,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    def get_processing_progress(self, document_id: str) -> Dict[str, any]:
        """Get document processing progress."""
        with Session(self.__db_engine) as session:
            document = session.get(Document, document_id)

            if document is None:
                raise HTTPException(status_code=404, detail="Document not found")

            progress_percentage = 0.0
            current_step = "Pending"

            if document.status == "processing":
                current_step = "Processing PDF..."
                progress_percentage = 50.0
            elif document.status == "completed":
                current_step = "Completed"
                progress_percentage = 100.0
            elif document.status == "failed":
                current_step = "Failed"
                progress_percentage = 0.0

            return {
                "document_id": document_id,
                "status": document.status,
                "progress_percentage": progress_percentage,
                "current_step": current_step,
                "tables_count": (
                    document.tables_count if document.tables_count > 0 else None
                ),
                "figures_count": (
                    document.figures_count if document.figures_count > 0 else None
                ),
                "error_message": document.error_message,
            }
