from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BoxCoords(BaseModel):
    """Bounding box coordinates for spatial elements."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    width: float = Field(..., description="Width of the box")
    height: float = Field(..., description="Height of the box")


class PageMetadata(BaseModel):
    """Metadata for a page in the document."""

    language: Optional[str] = Field(None, description="Language of the document")
    page_number: int = Field(..., description="Page number (0-indexed)")


class TableHeader(BaseModel):
    """Table header information."""

    id: str = Field(default="", description="Unique identifier for the header")
    column: int = Field(default=0, description="Column index of the header")
    name: str = Field(default="", description="Name of the header")
    dtype: str = Field(default="string", description="Data type of the header")


class TableMetadata(BaseModel):
    """Metadata for table elements."""

    title: Optional[str] = Field(None, description="Title of the table")
    caption: Optional[str] = Field(None, description="Caption of the table")
    notes: Optional[str] = Field(None, description="Notes about the table")


class MarkdownTable(BaseModel):
    """Table representation in markdown document."""

    metadata: TableMetadata = Field(
        default_factory=lambda: TableMetadata(title=None, caption=None, notes=None),
        description="Table metadata",
    )
    content: str = Field(default="", description="Markdown content of the table")
    headers: List[TableHeader] = Field(
        default_factory=list, description="Table headers"
    )
    data: List[Dict[str, Any]] = Field(
        default_factory=list, description="Table data rows"
    )
    bbox: Optional[BoxCoords] = Field(None, description="Bounding box of the table")


class MarkdownFigure(BaseModel):
    """Figure representation in markdown document."""

    id: int = Field(default=0, description="Unique identifier for the figure")
    title: Optional[str] = Field(None, description="Title of the figure")
    caption: Optional[str] = Field(None, description="Caption of the figure")
    content: Optional[str] = Field(None, description="Figure content/description")
    bbox: Optional[BoxCoords] = Field(None, description="Bounding box of the figure")


class MarkdownPage(BaseModel):
    """Single page in a markdown document."""

    metadata: PageMetadata = Field(
        default_factory=lambda: PageMetadata(language="en", page_number=0),
        description="Page metadata",
    )
    content: str = Field(default="", description="Markdown content of the page")
    markdown_content: Optional[str] = Field(
        None, description="Enhanced markdown content"
    )
    tables: Optional[List[MarkdownTable]] = Field(
        default_factory=list, description="Tables in the page"
    )
    figures: Optional[List[MarkdownFigure]] = Field(
        default_factory=list, description="Figures in the page"
    )


class MarkdownDocument(BaseModel):
    """Complete document representation from OpenAI vision API."""

    pages: List[MarkdownPage] = Field(
        default_factory=list, description="Pages in the document"
    )

    def get_total_pages(self) -> int:
        """Get total number of pages."""
        return len(self.pages)

    def get_all_text_content(self) -> str:
        """Extract all text content from all pages."""
        return "\n\n".join([page.content for page in self.pages])

    def get_all_tables(self) -> List[MarkdownTable]:
        """Get all tables from all pages."""
        tables = []
        for page in self.pages:
            if page.tables:
                tables.extend(page.tables)
        return tables

    def get_all_figures(self) -> List[MarkdownFigure]:
        """Get all figures from all pages."""
        figures = []
        for page in self.pages:
            if page.figures:
                figures.extend(page.figures)
        return figures


class OpenAIExtractionRequest(BaseModel):
    """Request model for OpenAI visual content extraction."""

    file_path: str = Field(..., description="Path to the PDF file")
    document_id: str = Field(..., description="Document identifier")
    extract_tables: bool = Field(default=True, description="Whether to extract tables")
    extract_figures: bool = Field(
        default=True, description="Whether to extract figures"
    )
    language: Optional[str] = Field(
        default="en", description="Expected document language"
    )


class OpenAIExtractionResponse(BaseModel):
    """Response model for OpenAI visual content extraction."""

    document_id: str = Field(..., description="Document identifier")
    markdown_document: MarkdownDocument = Field(
        ..., description="Extracted markdown document"
    )
    processing_time: float = Field(..., description="Processing time in seconds")
    total_pages: int = Field(..., description="Total pages processed")
    total_tokens_used: Optional[int] = Field(
        None, description="Tokens used for extraction"
    )
    extraction_timestamp: datetime = Field(
        default_factory=datetime.now, description="When extraction was completed"
    )
