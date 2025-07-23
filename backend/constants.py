from enum import Enum
from typing import Final


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationType(str, Enum):
    SINGLE_DOCUMENT = "single-document"
    MULTI_DOCUMENT = "multi-document"
    MULTI_DOC_ID = "multi-doc"


class ContentType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"


class SearchMode(str, Enum):
    HYBRID = "hybrid"
    DENSE = "dense"
    SPARSE = "sparse"


class ProcessingDefaults:
    MAX_FILE_SIZE: Final[int] = 50 * 1024 * 1024
    BASE_CHUNK_SIZE: Final[int] = 1200  # Increased for better context
    CHUNK_OVERLAP: Final[int] = 150  # Increased overlap for continuity
    MIN_CHUNK_SIZE: Final[int] = 100  # Increased minimum for meaningful content
    MAX_CHUNK_SIZE: Final[int] = 2000  # New: allow larger chunks for complex content
    TABLE_MAX_SIZE: Final[int] = 3000  # New: preserve table integrity
    MAX_CONVERSATION_HISTORY: Final[int] = 10
    DEFAULT_SEARCH_LIMIT: Final[int] = 8
    DEFAULT_PAGINATION_LIMIT: Final[int] = 10
    MAX_PAGINATION_LIMIT: Final[int] = 100
    SIMILARITY_THRESHOLD: Final[float] = 0.2
    HIGH_RELEVANCE_SCORE: Final[float] = 0.85
    # Legacy constant for backward compatibility
    CHUNK_SIZE: Final[int] = BASE_CHUNK_SIZE


class APIDefaults:
    DEFAULT_INCLUDE_SOURCES: Final[bool] = True
    DEFAULT_MAX_SOURCES: Final[int] = 3
    DEFAULT_SKIP: Final[int] = 0


class ErrorCodes:
    DOCUMENT_NOT_FOUND = "DOC_001"
    DOCUMENT_PROCESSING_FAILED = "DOC_002"
    DOCUMENT_UPLOAD_FAILED = "DOC_003"
    DOCUMENT_DELETE_FAILED = "DOC_004"

    CONVERSATION_NOT_FOUND = "CONV_001"
    MESSAGE_SAVE_FAILED = "CONV_002"

    PROCESSING_FAILED = "PROC_001"
    VECTOR_SEARCH_FAILED = "PROC_002"
    RAG_SETUP_FAILED = "PROC_003"

    VALIDATION_ERROR = "VAL_001"
    FILE_TOO_LARGE = "VAL_002"
    INVALID_FILE_TYPE = "VAL_003"

    EXTERNAL_API_ERROR = "EXT_001"
    DATABASE_ERROR = "DB_001"

    INTERNAL_SERVER_ERROR = "INT_001"


class HTTPMessages:
    DOCUMENT_NOT_FOUND = "Document not found"
    CONVERSATION_NOT_FOUND = "Conversation not found"
    FILE_TOO_LARGE = "File too large. Maximum size is {max_size}MB"
    INVALID_FILE_TYPE = "Only PDF files are allowed"
    PROCESSING_FAILED = "Document processing failed"
    UPLOAD_SUCCESS = "Document uploaded successfully"
    DELETE_SUCCESS = "Document deleted successfully"
    PROCESSING_STARTED = "Document processing started"
    CONVERSATION_CLEARED = "Conversation cleared successfully"


class LogMessages:
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PROCESSING_STARTED = "document_processing_started"
    DOCUMENT_PROCESSING_COMPLETED = "document_processing_completed"
    DOCUMENT_PROCESSING_FAILED = "document_processing_failed"
    DOCUMENT_DELETED = "document_deleted"

    CONVERSATION_CREATED = "conversation_created"
    MESSAGE_SAVED = "message_saved"

    RAG_SETUP_STARTED = "rag_setup_started"
    RAG_SETUP_COMPLETED = "rag_setup_completed"
    RAG_QUERY_PROCESSED = "rag_query_processed"

    VECTOR_SEARCH_PERFORMED = "vector_search_performed"
    OPENAI_API_CALLED = "openai_api_called"

    ERROR_OCCURRED = "error_occurred"


class FileExtensions:
    PDF = ".pdf"
    SUPPORTED_TYPES = [PDF]


class OpenAIModels:
    GPT_4_VISION = "gpt-4-vision-preview"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    TEXT_EMBEDDING_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_LARGE = "text-embedding-3-large"


class QdrantDefaults:
    COLLECTION_NAME = "hybrid_documents_official"
    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"
    DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    SPARSE_MODEL = "prithivida/Splade_PP_en_v1"
    DEFAULT_DISTANCE = "cosine"
