from datetime import datetime
from typing import Any, Dict, List, Optional

from constants import DocumentStatus, MessageRole
from sqlmodel import Field, Relationship, SQLModel
from utils.serialization import (
    ModelJSONMixin,
    deserialize_metadata,
    deserialize_relevance_scores,
    deserialize_source_chunks,
    serialize_metadata,
    serialize_relevance_scores,
    serialize_source_chunks,
)


class Document(SQLModel, ModelJSONMixin, table=True):
    document_id: str = Field(primary_key=True, description="Unique document identifier")
    filename: str = Field(description="Original filename")
    file_path: str = Field(description="Path to stored file")
    file_size: int = Field(description="File size in bytes")

    status: str = Field(default=DocumentStatus.PENDING, description="Processing status")

    upload_time: datetime = Field(
        default_factory=datetime.now, description="Upload timestamp"
    )
    processing_started_at: Optional[datetime] = Field(
        default=None, description="Processing start time"
    )
    processing_completed_at: Optional[datetime] = Field(
        default=None, description="Processing completion time"
    )

    page_count: int = Field(default=0, description="Total number of pages")
    language: Optional[str] = Field(default=None, description="Document language")

    processing_time: float = Field(
        default=0.0, description="Processing time in seconds"
    )
    tables_count: int = Field(default=0, description="Number of tables extracted")
    figures_count: int = Field(default=0, description="Number of figures extracted")
    openai_tokens_used: Optional[int] = Field(
        default=None, description="OpenAI tokens consumed"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if processing failed"
    )

    markdown_content: Optional[str] = Field(
        default=None, description="Serialized MarkdownDocument JSON"
    )

    conversations: List["Conversation"] = Relationship(back_populates="document")

    @property
    def is_processed(self) -> bool:
        return self.status == DocumentStatus.COMPLETED

    @property
    def is_processing(self) -> bool:
        return self.status == DocumentStatus.PROCESSING

    @property
    def has_failed(self) -> bool:
        return self.status == DocumentStatus.FAILED

    @property
    def markdown_data(self) -> Optional[Dict[str, Any]]:
        return deserialize_metadata(self.markdown_content)

    @markdown_data.setter
    def markdown_data(self, value: Optional[Dict[str, Any]]):
        self.markdown_content = serialize_metadata(value)


class Conversation(SQLModel, table=True):
    """Conversation model for storing chat sessions."""

    conversation_id: str = Field(
        primary_key=True, description="Unique conversation identifier"
    )
    document_id: str = Field(
        foreign_key="document.document_id", description="Associated document"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )

    # Relationships
    document: Document = Relationship(back_populates="conversations")
    messages: List["ChatMessage"] = Relationship(back_populates="conversation")


class ChatMessage(SQLModel, ModelJSONMixin, table=True):
    message_id: str = Field(primary_key=True, description="Unique message identifier")
    conversation_id: str = Field(
        foreign_key="conversation.conversation_id", description="Parent conversation"
    )

    role: str = Field(description="Message role (user, assistant, system)")
    content: str = Field(description="Message content")

    source_chunks: Optional[str] = Field(
        default=None, description="JSON string of referenced chunk IDs"
    )
    relevance_scores: Optional[str] = Field(
        default=None, description="JSON string of relevance scores"
    )

    response_time: Optional[float] = Field(
        default=None, description="Response time in seconds"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Message timestamp"
    )

    conversation: Conversation = Relationship(back_populates="messages")

    @property
    def source_chunks_list(self) -> List[str]:
        return deserialize_source_chunks(self.source_chunks)

    @source_chunks_list.setter
    def source_chunks_list(self, value: Optional[List[str]]):
        self.source_chunks = serialize_source_chunks(value)

    @property
    def relevance_scores_list(self) -> List[float]:
        return deserialize_relevance_scores(self.relevance_scores)

    @relevance_scores_list.setter
    def relevance_scores_list(self, value: Optional[List[float]]):
        self.relevance_scores = serialize_relevance_scores(value)
