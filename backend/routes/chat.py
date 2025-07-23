import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from constants import ConversationType, LogMessages, MessageRole
from db import get_engine
from dto.chat_dto import ChatDto
from dto.chat_models import ChatRequest, ChatResponse, SourceReference
from dto.documents_dto import DocumentsDto
from exceptions import MessageSaveError
from fastapi import APIRouter, HTTPException
from utils.agentic_rag import AgenticRAG

logger = logging.getLogger(__name__)


class ChatAPI:
    """Chat API with agentic RAG functionality and session support."""

    def __init__(self) -> None:
        self.router = APIRouter()
        self.chat_dto = ChatDto(get_engine())
        self.documents_dto = DocumentsDto(get_engine())

        # Initialize and setup agentic RAG system once
        self.agentic_rag = AgenticRAG(self.documents_dto)
        self.rag_ready = self._initialize_rag_system()

        # Essential routes only
        self.router.add_api_route(
            "/ask",
            self.ask_question,
            methods=["POST"],
            response_model=ChatResponse,
            summary="Ask a question using Enhanced Agentic RAG with session support",
        )

        self.router.add_api_route(
            "/refresh-rag",
            self.refresh_rag_system,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary="Refresh the RAG system to include newly processed documents",
        )

        self.router.add_api_route(
            "/status",
            self.get_system_status,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary="Check agentic RAG system status",
        )

    def _initialize_rag_system(self) -> bool:
        """Initialize the agentic RAG system once during startup."""
        try:
            logger.info(
                "🚀 Initializing Enhanced Agentic RAG System with Session Support"
            )
            rag_ready = self.agentic_rag.setup_for_all_documents()

            if rag_ready:
                logger.info(
                    "✅ Agentic RAG system initialized successfully with session support"
                )
            else:
                logger.info(
                    "⚠️ Agentic RAG initialized in general chat mode with session support (no documents found)"
                )

            return rag_ready

        except Exception as e:
            logger.error(f"❌ Failed to initialize agentic RAG system: {e}")
            return False

    async def refresh_rag_system(self) -> Dict[str, Any]:
        """Refresh the RAG system to include newly processed documents."""
        try:
            logger.info("🔄 Refreshing Agentic RAG system")
            self.rag_ready = self._initialize_rag_system()

            return {
                "message": "RAG system refreshed successfully",
                "rag_ready": self.rag_ready,
                "has_documents": self.agentic_rag.has_documents,
            }

        except Exception as e:
            logger.error(f"Failed to refresh RAG system: {e}")
            return {
                "message": f"Failed to refresh RAG system: {str(e)}",
                "rag_ready": False,
                "has_documents": False,
            }

    async def get_system_status(self) -> Dict[str, Any]:
        """Check agentic RAG system status."""
        try:
            # Get basic stats
            stats = (
                self.agentic_rag.vector_store.get_collection_stats()
                if self.agentic_rag.vector_store
                else {}
            )
            total_chunks = stats.get("total_points", 0)

            return {
                "status": "ready" if self.rag_ready else "no_documents",
                "message": (
                    "Agentic RAG system is ready with session support"
                    if self.rag_ready
                    else "No documents found for RAG"
                ),
                "rag_ready": self.rag_ready,
                "has_documents": self.agentic_rag.has_documents,
                "total_chunks": total_chunks,
                "documents_count": len(
                    self.documents_dto.list_documents(skip=0, limit=1000)
                ),
                "session_support": True,
            }
        except Exception as e:
            logger.error(f"System status check failed: {e}")
            return {
                "status": "error",
                "message": f"System check failed: {str(e)}",
                "rag_ready": False,
                "has_documents": False,
                "total_chunks": 0,
                "documents_count": 0,
                "session_support": False,
            }

    async def ask_question(self, request: ChatRequest) -> ChatResponse:
        """Ask a question using Enhanced Agentic RAG with session support."""
        start_time = time.time()

        try:
            # Generate session ID if not provided
            session_id = request.session_id or str(uuid.uuid4())

            logger.info(
                "Processing question with Enhanced Agentic RAG",
                extra={
                    "question_preview": request.question[:100],
                    "session_id": session_id,
                    "has_documents": self.agentic_rag.has_documents,
                    "rag_ready": self.rag_ready,
                },
            )

            # Check if RAG system needs refresh
            if not self.rag_ready:
                logger.info("RAG system not ready, attempting to refresh")
                self.rag_ready = self._initialize_rag_system()

            # Ask question using Enhanced Agentic RAG with session support
            rag_result = self.agentic_rag.ask_question(
                question=request.question, session_id=session_id
            )

            # Format sources
            sources = self._format_sources(rag_result.get("sources", []), request)

            response_time = time.time() - start_time

            logger.info(
                "Enhanced Agentic RAG query completed",
                extra={
                    "session_id": session_id,
                    "sources_count": len(sources),
                    "response_time": response_time,
                },
            )

            return ChatResponse(
                conversation_id=session_id,  # Use session_id as conversation_id for consistency
                answer=rag_result["answer"],
                sources=sources,
                response_time=response_time,
                timestamp=time.time(),
                conversation_type=ConversationType.MULTI_DOCUMENT,
                documents_searched=len(
                    self.documents_dto.list_documents(skip=0, limit=1000)
                ),
            )

        except Exception as e:
            logger.error(f"Enhanced Agentic RAG processing failed: {str(e)}")

            # Return graceful error response
            return ChatResponse(
                conversation_id=request.session_id or str(uuid.uuid4()),
                answer="I apologize, but I encountered an error while processing your question. Please try again.",
                sources=[],
                response_time=time.time() - start_time,
                timestamp=time.time(),
                conversation_type="error",
                documents_searched=0,
            )

    def _format_sources(
        self, rag_sources: List[Dict], request: ChatRequest
    ) -> List[SourceReference]:
        """Format RAG sources into SourceReference objects."""
        sources = []

        if not request.include_sources or not rag_sources:
            return sources

        # Limit sources to max_sources
        limited_sources = rag_sources[: request.max_sources]

        for i, source in enumerate(limited_sources):
            try:
                sources.append(
                    SourceReference(
                        chunk_id=f"agentic-rag-source-{i}",
                        document_id=ConversationType.MULTI_DOC_ID,
                        page_number=max(0, source.get("page_number", 0)),
                        chunk_index=source.get("chunk_index", i),
                        content_preview=source.get("content_preview", ""),
                        relevance_score=source.get("relevance_score", 0.85),
                        source_document=source.get(
                            "source_document", "Unknown Document"
                        ),
                        content_type=source.get("content_type", "text"),
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to format agentic RAG source {i}: {e}")
                continue

        return sources
