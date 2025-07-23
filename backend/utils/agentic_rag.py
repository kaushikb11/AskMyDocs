import json
import logging
from typing import Any, Dict, List, Literal, Optional

from config import settings
from dto.documents_dto import DocumentsDto
from langchain.tools.retriever import create_retriever_tool
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field
from utils.qdrant_client import QdrantOfficialHybridStore

logger = logging.getLogger(__name__)


class GradeDocuments(BaseModel):
    """Grade documents using a binary score for relevance check."""

    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )


class HybridSearchRetriever:
    """Custom retriever that integrates with QdrantOfficialHybridStore."""

    def __init__(self, vector_store: QdrantOfficialHybridStore):
        self.vector_store = vector_store
        self.last_retrieved_docs = []  # Store documents for source attribution

    def get_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        """Perform hybrid search and return LangChain Document objects."""
        try:
            # Use the official hybrid search
            search_results = self.vector_store.hybrid_search(
                query=query,
                limit=8,
                score_threshold=0.2,  # Lower threshold for better recall
            )

            # Convert to LangChain Document format
            documents = []
            for result in search_results:
                # Create rich metadata for source attribution
                metadata = {
                    "chunk_id": result["chunk_id"],
                    "document_id": result["document_id"],
                    "content_type": result["content_type"],
                    "page_number": result["page_number"],
                    "chunk_index": result["chunk_index"],
                    "relevance_score": result["score"],
                    "search_type": result["search_type"],
                    "source": f"Document: {result.get('metadata', {}).get('filename', 'Unknown')} (Page {result['page_number'] + 1})",
                    # Include additional metadata
                    **result.get("metadata", {}),
                }

                doc = Document(page_content=result["content"], metadata=metadata)
                documents.append(doc)

            # Store documents for source attribution
            self.last_retrieved_docs = documents

            logger.info(
                f"Hybrid search returned {len(documents)} documents for query: {query[:50]}..."
            )
            return documents

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            self.last_retrieved_docs = []
            return []

    def invoke(self, input_data, **kwargs):
        """LangChain Runnable interface - required for create_retriever_tool."""
        if isinstance(input_data, dict):
            query = input_data.get("query", "")
        else:
            query = str(input_data)

        return self.get_relevant_documents(query, **kwargs)


class AgenticRAG:
    """Enhanced Agentic RAG system following LangGraph tutorial patterns with session support."""

    def __init__(self, documents_dto: DocumentsDto):
        self.documents_dto = documents_dto
        self.vector_store = QdrantOfficialHybridStore()

        # Create custom retriever and tool following LangGraph pattern
        self.retriever = HybridSearchRetriever(self.vector_store)
        self.retriever_tool = create_retriever_tool(
            self.retriever,
            "retrieve_documents",
            "Search and return information from uploaded PDF documents using advanced hybrid search (semantic + keyword matching).",
        )

        # Initialize models following tutorial
        self.response_model = ChatOpenAI(
            model="gpt-4", temperature=0, api_key=settings.openai_api_key
        )
        self.grader_model = ChatOpenAI(
            model="gpt-4", temperature=0, api_key=settings.openai_api_key
        )

        # Add memory saver for session support
        self.checkpointer = MemorySaver()
        self.graph = None
        self.has_documents = False

    def _check_processed_documents(self) -> bool:
        """Check if there are processed documents available for search."""
        try:
            stats = self.vector_store.get_collection_stats()
            total_points = stats.get("total_points", 0)
            self.has_documents = total_points > 0

            if self.has_documents:
                logger.info(f"Found {total_points} indexed chunks for hybrid search")
            else:
                logger.warning("No indexed documents found for hybrid search")

            return self.has_documents

        except Exception as e:
            logger.error(f"Error checking processed documents: {e}")
            self.has_documents = False
            return False

    def _generate_query_or_respond(self, state: MessagesState):
        """Generate a response or decide to retrieve documents - following LangGraph tutorial."""
        if not self.has_documents:
            # No documents available, respond directly
            response = self.response_model.invoke(state["messages"])
            return {"messages": [response]}

        # Following tutorial: bind tools and let model decide
        response = self.response_model.bind_tools([self.retriever_tool]).invoke(
            state["messages"]
        )
        return {"messages": [response]}

    def _grade_documents(
        self, state: MessagesState
    ) -> Literal["generate_answer", "rewrite_question"]:
        """Determine whether retrieved documents are relevant - following LangGraph tutorial."""
        GRADE_PROMPT = (
            "You are a grader assessing relevance of a retrieved document to a user question. \n "
            "Here is the retrieved document: \n\n {context} \n\n"
            "Here is the user question: {question} \n"
            "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
            "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."
        )

        question = state["messages"][0].content

        # Get the last tool message (retrieved content)
        context = ""
        for msg in reversed(state["messages"]):
            if hasattr(msg, "content") and hasattr(msg, "type") and msg.type == "tool":
                context = msg.content
                break

        if not context:
            logger.warning("No tool message found for grading")
            return "rewrite_question"

        prompt = GRADE_PROMPT.format(question=question, context=context)

        response = self.grader_model.with_structured_output(GradeDocuments).invoke(
            [{"role": "user", "content": prompt}]
        )

        if response.binary_score == "yes":
            logger.info("Retrieved documents are relevant - generating answer")
            return "generate_answer"
        else:
            logger.info("Retrieved documents not relevant - rewriting question")
            return "rewrite_question"

    def _rewrite_question(self, state: MessagesState):
        """Rewrite the original user question - following LangGraph tutorial."""
        REWRITE_PROMPT = (
            "Look at the input and try to reason about the underlying semantic intent / meaning. \n "
            "Here is the initial question:\n"
            "------- \n"
            "{question} \n"
            "------- \n"
            "Formulate an improved question:"
        )

        messages = state["messages"]
        question = messages[0].content
        prompt = REWRITE_PROMPT.format(question=question)

        response = self.response_model.invoke([{"role": "user", "content": prompt}])
        return {"messages": [{"role": "user", "content": response.content}]}

    def _generate_answer(self, state: MessagesState):
        """Generate answer based on retrieved context - following LangGraph tutorial."""
        GENERATE_PROMPT = (
            "You are an assistant for question-answering tasks. "
            "Use the following pieces of retrieved context to answer the question. "
            "If you don't know the answer, just say that you don't know. "
            "Use three sentences maximum and keep the answer concise.\n"
            "Question: {question} \n"
            "Context: {context}"
        )

        question = state["messages"][0].content

        # Get the last tool message (retrieved context)
        context = ""
        for msg in reversed(state["messages"]):
            if hasattr(msg, "content") and hasattr(msg, "type") and msg.type == "tool":
                context = msg.content
                break

        prompt = GENERATE_PROMPT.format(question=question, context=context)

        response = self.response_model.invoke([{"role": "user", "content": prompt}])
        return {"messages": [response]}

    def _build_graph(self):
        """Build the agentic RAG workflow graph with checkpointer for session support."""
        workflow = StateGraph(MessagesState)

        # Define nodes following tutorial
        workflow.add_node("generate_query_or_respond", self._generate_query_or_respond)
        workflow.add_node("retrieve", ToolNode([self.retriever_tool]))
        workflow.add_node("rewrite_question", self._rewrite_question)
        workflow.add_node("generate_answer", self._generate_answer)

        # Define edges following tutorial
        workflow.add_edge(START, "generate_query_or_respond")

        # Conditional edge to decide whether to retrieve - following tutorial
        workflow.add_conditional_edges(
            "generate_query_or_respond",
            # Use prebuilt tools_condition from tutorial
            tools_condition,
            {
                # Translate condition outputs to nodes
                "tools": "retrieve",
                END: END,
            },
        )

        # Conditional edge after retrieval for document grading - following tutorial
        workflow.add_conditional_edges(
            "retrieve",
            self._grade_documents,
        )

        workflow.add_edge("generate_answer", END)
        workflow.add_edge("rewrite_question", "generate_query_or_respond")

        # Compile with checkpointer for session support
        return workflow.compile(checkpointer=self.checkpointer)

    def setup_for_all_documents(self) -> bool:
        """Setup the RAG system for all uploaded documents."""
        try:
            self.has_documents = self._check_processed_documents()
            self.graph = self._build_graph()

            if self.has_documents:
                logger.info(
                    "Agentic RAG setup complete with hybrid search and session support"
                )
                return True
            else:
                logger.info(
                    "Agentic RAG setup complete without documents (general chat mode with session support)"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to setup RAG: {e}")
            return False

    def ask_question(
        self,
        question: str,
        session_id: str = "default",
        conversation_history: List[BaseMessage] = None,
    ) -> Dict[str, Any]:
        """Ask a question using the enhanced agentic RAG system with session support."""
        if not self.graph:
            raise ValueError(
                "RAG system not initialized. Call setup_for_all_documents() first."
            )

        # Create config with thread_id for session support
        config = {"configurable": {"thread_id": session_id}}

        try:
            # Run the graph with session config - LangGraph handles conversation history automatically
            result = self.graph.invoke(
                {"messages": [{"role": "user", "content": question}]}, config=config
            )

            # Extract final response
            final_message = result["messages"][-1]

            return {
                "answer": final_message.content,
                "sources": self._extract_sources_from_tool_messages(result["messages"]),
                "conversation": result["messages"],
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(f"Error in agentic RAG: {e}")
            return {
                "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
                "sources": [],
                "conversation": [{"role": "user", "content": question}],
                "session_id": session_id,
            }

    def _extract_sources_from_tool_messages(
        self, messages: List
    ) -> List[Dict[str, Any]]:
        """Extract source references using stored documents from retriever."""
        sources = []

        # Use stored documents from retriever instead of parsing tool messages
        # This preserves all the rich metadata that gets lost in tool message conversion
        if (
            hasattr(self.retriever, "last_retrieved_docs")
            and self.retriever.last_retrieved_docs
        ):
            try:
                for doc in self.retriever.last_retrieved_docs[:5]:  # Limit to 5 sources
                    metadata = doc.metadata
                    content_preview = (
                        doc.page_content[:300] + "..."
                        if len(doc.page_content) > 300
                        else doc.page_content
                    )

                    sources.append(
                        {
                            "content_preview": content_preview,
                            "source_document": metadata.get(
                                "source",
                                f"Document: {metadata.get('filename', 'Unknown')} (Page {metadata.get('page_number', 0) + 1})",
                            ),
                            "content_type": metadata.get("content_type", "text"),
                            "page_number": metadata.get("page_number", 0),
                            "chunk_index": metadata.get("chunk_index", 0),
                            "relevance_score": float(
                                metadata.get("relevance_score", 0.0)
                            ),
                            "document_id": metadata.get("document_id", ""),
                            "chunk_id": metadata.get("chunk_id", ""),
                            "search_type": metadata.get("search_type", "hybrid"),
                        }
                    )

                logger.info(f"Extracted {len(sources)} sources from stored documents")

            except Exception as e:
                logger.error(f"Error extracting sources from stored documents: {e}")

        # Fallback: if no stored documents, check tool messages (legacy behavior)
        if not sources:
            logger.warning(
                "No stored documents found, falling back to tool message parsing"
            )
            for msg in messages:
                if (
                    hasattr(msg, "type")
                    and msg.type == "tool"
                    and hasattr(msg, "content")
                ):
                    content = msg.content
                    if content:
                        sources.append(
                            {
                                "content_preview": (
                                    content[:300] + "..."
                                    if len(content) > 300
                                    else content
                                ),
                                "source_document": "Retrieved from document search",
                                "content_type": "text",
                                "page_number": 0,
                                "chunk_index": 0,
                                "relevance_score": 0.85,
                                "document_id": "",
                                "chunk_id": "",
                                "search_type": "unknown",
                            }
                        )
                        break

        return sources

    def stream_response(
        self,
        question: str,
        session_id: str = "default",
        conversation_history: List[BaseMessage] = None,
    ):
        """Stream the agentic RAG response for real-time updates with session support."""
        if not self.graph:
            raise ValueError(
                "RAG system not initialized. Call setup_for_all_documents() first."
            )

        # Create config with thread_id for session support
        config = {"configurable": {"thread_id": session_id}}

        try:
            # Stream the graph execution with session config
            for chunk in self.graph.stream(
                {"messages": [{"role": "user", "content": question}]}, config=config
            ):
                for node, update in chunk.items():
                    yield {
                        "node": node,
                        "update": update,
                        "message": (
                            update.get("messages", [])[-1]
                            if update.get("messages")
                            else None
                        ),
                        "session_id": session_id,
                    }

        except Exception as e:
            logger.error(f"Error in streaming agentic RAG: {e}")
            yield {
                "node": "error",
                "update": {"error": str(e)},
                "message": {
                    "role": "assistant",
                    "content": "I apologize, but I encountered an error while processing your question.",
                },
                "session_id": session_id,
            }
