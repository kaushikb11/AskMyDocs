from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Chat message role enum."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SourceReference(BaseModel):
    """Reference to a source document chunk."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Source document identifier")
    page_number: Optional[int] = Field(None, description="Page number in document")
    chunk_index: int = Field(..., description="Chunk index within document")
    content_preview: str = Field(..., description="Preview of the source content")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    source_document: Optional[str] = Field(
        None, description="Name of the source document file"
    )
    content_type: Optional[str] = Field(
        default="text", description="Type of content: text, table, or figure"
    )


class ChatRequest(BaseModel):
    """Request model for chat/ask endpoint."""

    document_id: Optional[str] = Field(
        None,
        description="Specific document to ask about (optional - searches all documents if not provided)",
    )
    question: str = Field(
        ..., min_length=1, max_length=1000, description="User question"
    )
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    session_id: Optional[str] = Field(
        None, description="Session ID for conversation continuity"
    )
    include_sources: bool = Field(
        default=True, description="Whether to include source references"
    )
    max_sources: int = Field(
        default=3, description="Maximum number of source references"
    )
    search_mode: Optional[str] = Field(
        default="hybrid", description="Search mode: 'hybrid', 'dense', or 'sparse'"
    )


class ChatResponse(BaseModel):
    """Response model for chat/ask endpoint."""

    conversation_id: str = Field(..., description="Conversation identifier")
    answer: str = Field(..., description="Generated answer")
    sources: List[SourceReference] = Field(..., description="Source references")
    response_time: float = Field(..., description="Response time in seconds")
    timestamp: datetime = Field(..., description="Response timestamp")
    conversation_type: str = Field(
        default="multi-document",
        description="Type of conversation: 'single-document' or 'multi-document'",
    )
    documents_searched: int = Field(
        default=0, description="Number of documents searched"
    )


class ChatMessageDto(BaseModel):
    """Individual chat message."""

    message_id: str = Field(..., description="Unique message identifier")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    sources: Optional[List[SourceReference]] = Field(
        None, description="Source references for assistant messages"
    )


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""

    conversation_id: str = Field(..., description="Conversation identifier")
    document_id: str = Field(..., description="Associated document")
    messages: List[ChatMessageDto] = Field(..., description="Conversation messages")
    created_at: datetime = Field(..., description="Conversation creation time")
    updated_at: datetime = Field(..., description="Last update time")


class ConversationListItem(BaseModel):
    """Conversation list item."""

    conversation_id: str = Field(..., description="Conversation identifier")
    document_id: str = Field(..., description="Associated document")
    document_filename: str = Field(..., description="Document filename")
    last_message: str = Field(..., description="Last message preview")
    message_count: int = Field(..., description="Number of messages")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    conversation_type: Optional[str] = Field(
        default=None, description="Type: 'single-document' or 'multi-document'"
    )


class ConversationListResponse(BaseModel):
    """Response model for listing conversations."""

    conversations: List[ConversationListItem] = Field(
        ..., description="List of conversations"
    )
    total: int = Field(..., description="Total number of conversations")


class ClearConversationResponse(BaseModel):
    """Response model for clearing conversation."""

    conversation_id: str = Field(..., description="Cleared conversation ID")
    message: str = Field(..., description="Success message")
