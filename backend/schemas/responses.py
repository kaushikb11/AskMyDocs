from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from constants import ErrorCodes
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = Field(..., description="Whether the operation was successful")
    data: Optional[T] = Field(None, description="Response data")
    message: str = Field(default="", description="Human-readable message")
    error_code: Optional[str] = Field(
        None, description="Error code if operation failed"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )

    class Config:
        arbitrary_types_allowed = True


class PaginationInfo(BaseModel):
    page: int = Field(..., description="Current page number (0-based)")
    limit: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class PaginatedResponse(APIResponse[List[T]]):
    pagination: PaginationInfo = Field(..., description="Pagination information")


class ErrorDetail(BaseModel):
    field: Optional[str] = Field(None, description="Field that caused the error")
    code: str = Field(..., description="Specific error code")
    message: str = Field(..., description="Error message")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional error context"
    )


class ValidationErrorResponse(APIResponse[None]):
    errors: List[ErrorDetail] = Field(..., description="List of validation errors")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, bool] = Field(..., description="Status of individual services")
    version: str = Field(..., description="Application version")
    uptime: Optional[float] = Field(None, description="Uptime in seconds")


class ProcessingStatusResponse(BaseModel):
    """Document processing status response."""

    document_id: str = Field(..., description="Document identifier")
    status: str = Field(..., description="Processing status")
    progress_percentage: float = Field(..., description="Processing progress (0-100)")
    current_step: str = Field(..., description="Current processing step")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(
        None, description="Processing completion time"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    statistics: Optional[Dict[str, Any]] = Field(
        None, description="Processing statistics"
    )


class MetricsResponse(BaseModel):
    """Application metrics response."""

    documents_total: int = Field(..., description="Total number of documents")
    documents_processed: int = Field(..., description="Number of processed documents")
    conversations_total: int = Field(..., description="Total number of conversations")
    messages_total: int = Field(..., description="Total number of messages")
    vector_store_size: Optional[int] = Field(None, description="Vector store size")
    processing_queue_size: int = Field(
        default=0, description="Documents in processing queue"
    )
    last_updated: datetime = Field(default_factory=datetime.now)


class ResponseHelper:
    @staticmethod
    def success(
        data: T = None, message: str = "Operation completed successfully"
    ) -> APIResponse[T]:
        return APIResponse(success=True, data=data, message=message)

    @staticmethod
    def error(
        message: str, error_code: str = ErrorCodes.INTERNAL_SERVER_ERROR, data: T = None
    ) -> APIResponse[T]:
        return APIResponse(
            success=False, data=data, message=message, error_code=error_code
        )

    @staticmethod
    def validation_error(
        errors: List[ErrorDetail], message: str = "Validation failed"
    ) -> ValidationErrorResponse:
        return ValidationErrorResponse(
            success=False,
            message=message,
            error_code=ErrorCodes.VALIDATION_ERROR,
            errors=errors,
        )

    @staticmethod
    def paginated(
        data: List[T],
        page: int,
        limit: int,
        total: int,
        message: str = "Data retrieved successfully",
    ) -> PaginatedResponse[T]:
        return PaginatedResponse(
            success=True,
            data=data,
            message=message,
            pagination=PaginationInfo(
                page=page,
                limit=limit,
                total=total,
                has_next=(page + 1) * limit < total,
                has_previous=page > 0,
            ),
        )

    @staticmethod
    def not_found(entity: str, entity_id: str = None) -> APIResponse[None]:
        message = f"{entity} not found"
        if entity_id:
            message += f" (ID: {entity_id})"

        return APIResponse(
            success=False,
            message=message,
            error_code=(
                ErrorCodes.DOCUMENT_NOT_FOUND
                if "document" in entity.lower()
                else (
                    ErrorCodes.CONVERSATION_NOT_FOUND
                    if "conversation" in entity.lower()
                    else "NOT_FOUND"
                )
            ),
        )

    @staticmethod
    def processing_status(
        document_id: str, status: str, progress: float, current_step: str, **kwargs
    ) -> APIResponse[ProcessingStatusResponse]:
        status_data = ProcessingStatusResponse(
            document_id=document_id,
            status=status,
            progress_percentage=progress,
            current_step=current_step,
            **kwargs,
        )

        return ResponseHelper.success(
            data=status_data, message=f"Document processing status: {status}"
        )

    @staticmethod
    def health_check(
        services: Dict[str, bool],
        version: str = "1.0.0",
        uptime: Optional[float] = None,
    ) -> HealthCheckResponse:
        overall_status = "healthy" if all(services.values()) else "unhealthy"

        return HealthCheckResponse(
            status=overall_status, services=services, version=version, uptime=uptime
        )


class DocumentUploadResponse(BaseModel):
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    upload_time: datetime = Field(..., description="Upload timestamp")
    status: str = Field(..., description="Initial processing status")


class DocumentListItem(BaseModel):
    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    upload_time: datetime = Field(..., description="Upload timestamp")
    status: str = Field(..., description="Processing status")
    page_count: Optional[int] = Field(None, description="Number of pages")
    tables_count: Optional[int] = Field(None, description="Number of tables")
    figures_count: Optional[int] = Field(None, description="Number of figures")


class ConversationListItem(BaseModel):
    conversation_id: str = Field(..., description="Conversation identifier")
    document_id: str = Field(..., description="Associated document")
    document_filename: str = Field(..., description="Document filename")
    last_message: str = Field(..., description="Last message preview")
    message_count: int = Field(..., description="Number of messages")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    conversation_type: str = Field(..., description="Type of conversation")
