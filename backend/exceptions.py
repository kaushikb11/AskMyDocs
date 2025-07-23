from datetime import datetime
from typing import Any, Dict, Optional

from constants import ErrorCodes, HTTPMessages


class DocumentIntelligenceError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or ErrorCodes.INTERNAL_SERVER_ERROR
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error_code": self.error_code,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(DocumentIntelligenceError):
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else None
        super().__init__(
            message=message,
            status_code=400,
            error_code=ErrorCodes.VALIDATION_ERROR,
            details=details,
        )


class DocumentNotFoundError(DocumentIntelligenceError):
    def __init__(self, document_id: str):
        super().__init__(
            message=HTTPMessages.DOCUMENT_NOT_FOUND,
            status_code=404,
            error_code=ErrorCodes.DOCUMENT_NOT_FOUND,
            details={"document_id": document_id},
        )


class DocumentProcessingError(DocumentIntelligenceError):
    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        stage: Optional[str] = None,
    ):
        details = {}
        if document_id:
            details["document_id"] = document_id
        if stage:
            details["processing_stage"] = stage

        super().__init__(
            message=message,
            status_code=500,
            error_code=ErrorCodes.DOCUMENT_PROCESSING_FAILED,
            details=details if details else None,
        )


class DocumentUploadError(DocumentIntelligenceError):
    def __init__(self, message: str, filename: Optional[str] = None):
        details = {"filename": filename} if filename else None
        super().__init__(
            message=message,
            status_code=400,
            error_code=ErrorCodes.DOCUMENT_UPLOAD_FAILED,
            details=details,
        )


class FileTooLargeError(DocumentUploadError):
    def __init__(self, file_size: int, max_size: int, filename: Optional[str] = None):
        max_size_mb = max_size // (1024 * 1024)
        message = HTTPMessages.FILE_TOO_LARGE.format(max_size=max_size_mb)

        super().__init__(message=message, filename=filename)
        self.error_code = ErrorCodes.FILE_TOO_LARGE
        self.details.update(
            {
                "file_size_bytes": file_size,
                "max_size_bytes": max_size,
                "max_size_mb": max_size_mb,
            }
        )


class InvalidFileTypeError(DocumentUploadError):
    def __init__(self, filename: str, provided_type: Optional[str] = None):
        super().__init__(message=HTTPMessages.INVALID_FILE_TYPE, filename=filename)
        self.error_code = ErrorCodes.INVALID_FILE_TYPE
        if provided_type:
            self.details["provided_type"] = provided_type


class ConversationNotFoundError(DocumentIntelligenceError):
    def __init__(self, conversation_id: str):
        super().__init__(
            message=HTTPMessages.CONVERSATION_NOT_FOUND,
            status_code=404,
            error_code=ErrorCodes.CONVERSATION_NOT_FOUND,
            details={"conversation_id": conversation_id},
        )


class MessageSaveError(DocumentIntelligenceError):
    def __init__(self, message: str, conversation_id: Optional[str] = None):
        details = {"conversation_id": conversation_id} if conversation_id else None
        super().__init__(
            message=message,
            status_code=500,
            error_code=ErrorCodes.MESSAGE_SAVE_FAILED,
            details=details,
        )


class VectorSearchError(DocumentIntelligenceError):
    def __init__(self, message: str, query: Optional[str] = None):
        details = {"query": query} if query else None
        super().__init__(
            message=message,
            status_code=500,
            error_code=ErrorCodes.VECTOR_SEARCH_FAILED,
            details=details,
        )


class RAGSetupError(DocumentIntelligenceError):
    def __init__(self, message: str):
        super().__init__(
            message=message, status_code=500, error_code=ErrorCodes.RAG_SETUP_FAILED
        )


class ExternalAPIError(DocumentIntelligenceError):
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        details = {}
        if service:
            details["service"] = service
        if status_code:
            details["external_status_code"] = status_code

        super().__init__(
            message=message,
            status_code=503,
            error_code=ErrorCodes.EXTERNAL_API_ERROR,
            details=details if details else None,
        )


class DatabaseError(DocumentIntelligenceError):
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {"operation": operation} if operation else None
        super().__init__(
            message=message,
            status_code=500,
            error_code=ErrorCodes.DATABASE_ERROR,
            details=details,
        )


def validate_document_id(document_id: Optional[str]) -> str:
    if not document_id:
        raise ValidationError("Document ID is required", field="document_id")
    if not isinstance(document_id, str) or len(document_id.strip()) == 0:
        raise ValidationError(
            "Document ID must be a non-empty string", field="document_id"
        )
    return document_id.strip()


def validate_conversation_id(conversation_id: Optional[str]) -> str:
    if not conversation_id:
        raise ValidationError("Conversation ID is required", field="conversation_id")
    if not isinstance(conversation_id, str) or len(conversation_id.strip()) == 0:
        raise ValidationError(
            "Conversation ID must be a non-empty string", field="conversation_id"
        )
    return conversation_id.strip()


def validate_file_upload(file, max_size: int) -> None:
    if not file or not file.filename:
        raise DocumentUploadError("No file provided")

    if not file.filename.lower().endswith(".pdf"):
        raise InvalidFileTypeError(
            filename=file.filename,
            provided_type=(
                file.filename.split(".")[-1] if "." in file.filename else "unknown"
            ),
        )

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > max_size:
        raise FileTooLargeError(
            file_size=file_size, max_size=max_size, filename=file.filename
        )
