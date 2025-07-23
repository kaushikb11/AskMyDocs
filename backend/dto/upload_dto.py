from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Document processing status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    upload_time: datetime = Field(..., description="Upload timestamp")
    status: ProcessingStatus = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")


class DocumentMetadata(BaseModel):
    """Document metadata extracted from PDF."""

    title: Optional[str] = Field(None, description="Document title")
    author: Optional[str] = Field(None, description="Document author")
    subject: Optional[str] = Field(None, description="Document subject")
    creator: Optional[str] = Field(None, description="Document creator")
    producer: Optional[str] = Field(None, description="Document producer")
    creation_date: Optional[datetime] = Field(None, description="Creation date")
    modification_date: Optional[datetime] = Field(None, description="Modification date")
    page_count: int = Field(..., description="Total number of pages")


class ProcessingResult(BaseModel):
    """Result of document processing."""

    document_id: str = Field(..., description="Document identifier")
    total_chunks: int = Field(..., description="Number of text chunks created")
    processing_time: float = Field(..., description="Processing time in seconds")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    status: ProcessingStatus = Field(..., description="Final processing status")
    error_message: Optional[str] = Field(
        None, description="Error message if processing failed"
    )


class DocumentListItem(BaseModel):
    """Document list item for listing endpoints."""

    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    upload_time: datetime = Field(..., description="Upload timestamp")
    status: ProcessingStatus = Field(..., description="Current processing status")
    page_count: Optional[int] = Field(None, description="Number of pages")
    tables_count: Optional[int] = Field(None, description="Number of tables")
    figures_count: Optional[int] = Field(None, description="Number of figures")


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""

    documents: list[DocumentListItem] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")


class ProcessingStatusResponse(BaseModel):
    """Response model for processing status check."""

    document_id: str = Field(..., description="Document identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    progress_percentage: float = Field(..., description="Processing progress (0-100)")
    current_step: str = Field(..., description="Current processing step")
    tables_count: Optional[int] = Field(
        None, description="Number of tables (if completed)"
    )
    figures_count: Optional[int] = Field(
        None, description="Number of figures (if completed)"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SummaryType(str, Enum):
    """Document summary type enum."""

    BRIEF = "brief"  # Short overview (1-2 paragraphs)
    DETAILED = "detailed"  # Comprehensive summary (3-5 paragraphs)
    BULLET_POINTS = "bullet_points"  # Key points in bullet format
    EXECUTIVE = "executive"  # Executive summary style


class SummaryRequest(BaseModel):
    """Request model for document summary generation."""

    document_id: str = Field(..., description="Document identifier to summarize")
    summary_type: SummaryType = Field(
        default=SummaryType.BRIEF, description="Type of summary to generate"
    )
    custom_instructions: Optional[str] = Field(
        None, description="Custom instructions for summary generation"
    )
    include_key_points: bool = Field(
        default=True, description="Include key points in summary"
    )
    include_tables_summary: bool = Field(
        default=True, description="Include summary of tables found"
    )
    include_figures_summary: bool = Field(
        default=True, description="Include summary of figures found"
    )


class SummarySection(BaseModel):
    """A section of the document summary."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    page_references: List[int] = Field(
        default_factory=list, description="Page numbers referenced in this section"
    )


class SummaryResponse(BaseModel):
    """Response model for document summary generation."""

    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original document filename")
    summary_type: SummaryType = Field(..., description="Type of summary generated")

    # Main summary content
    title: Optional[str] = Field(None, description="Generated title for the document")
    overview: str = Field(..., description="Main summary content")

    # Structured sections (for detailed summaries)
    sections: List[SummarySection] = Field(
        default_factory=list, description="Summary sections"
    )

    # Key insights
    key_points: List[str] = Field(
        default_factory=list, description="Key points extracted"
    )
    tables_summary: Optional[str] = Field(None, description="Summary of tables found")
    figures_summary: Optional[str] = Field(None, description="Summary of figures found")

    # Metadata
    total_pages: int = Field(..., description="Total pages in document")
    word_count_estimate: Optional[int] = Field(
        None, description="Estimated word count of original document"
    )
    generation_time: float = Field(..., description="Time taken to generate summary")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Summary generation timestamp"
    )

    # Quality indicators
    confidence_score: Optional[float] = Field(
        None, description="AI confidence in summary quality (0-1)"
    )
    tokens_used: Optional[int] = Field(
        None, description="OpenAI tokens used for summary generation"
    )
