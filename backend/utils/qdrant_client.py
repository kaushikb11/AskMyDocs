import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from config import settings
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    Document,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    Match,
    NamedVector,
    PayloadSchemaType,
    PointStruct,
    Prefetch,
    SearchParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
    VectorParamsDiff,
)
from utils.smart_chunker import MarkdownDocumentChunker

logger = logging.getLogger(__name__)


class QdrantOfficialHybridStore:
    """
    Official Qdrant hybrid search implementation using FastEmbed and native fusion.
    Based on: https://qdrant.tech/documentation/beginner-tutorials/hybrid-search-fastembed/
    """

    # Official models from Qdrant documentation
    DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    SPARSE_MODEL = "prithivida/Splade_PP_en_v1"

    def __init__(self):
        if settings.qdrant_url and settings.qdrant_api_key:
            self.client = QdrantClient(
                url=settings.qdrant_url, api_key=settings.qdrant_api_key
            )
        else:
            self.client = QdrantClient(host="localhost", port=6333)

        self.dense_vector_name = "dense"
        self.sparse_vector_name = "sparse"

        self.chunker = MarkdownDocumentChunker(
            base_chunk_size=1200,
            chunk_overlap=150,
            min_chunk_size=100,
            max_chunk_size=2000,
            table_max_size=3000,
        )

        self.collection_name = "hybrid_documents_official"

        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create hybrid collection using official Qdrant approach."""
        try:
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        self.dense_vector_name: models.VectorParams(
                            size=self.client.get_embedding_size(self.DENSE_MODEL),
                            distance=models.Distance.COSINE,
                        )
                    },
                    sparse_vectors_config={
                        self.sparse_vector_name: models.SparseVectorParams()
                    },
                )
                logger.info(
                    f"Created official hybrid collection: {self.collection_name}"
                )

            self._ensure_indexes_exist()

        except Exception as e:
            logger.error(f"Error creating official hybrid collection: {e}")
            raise

    def _ensure_indexes_exist(self):
        """Create necessary indexes for efficient filtering."""
        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Created index for document_id field")

            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="content_type",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Created index for content_type field")

        except Exception as e:
            logger.warning(f"Could not create indexes (might already exist): {e}")

    def index_document(
        self, document_id: str, filename: str, markdown_doc_data: Dict[str, Any]
    ) -> int:
        """Index a MarkdownDocument using official Qdrant hybrid approach."""
        try:
            if not markdown_doc_data or "pages" not in markdown_doc_data:
                logger.warning(f"Invalid document data for {document_id}")
                return 0

            pages = markdown_doc_data.get("pages", [])
            if not pages:
                logger.warning(f"No pages found for document {document_id}")
                return 0

            chunks = self.chunker.chunk_markdown_document(
                document_id=document_id,
                filename=filename,
                markdown_doc_data=markdown_doc_data,
            )

            if not chunks:
                logger.warning(f"No chunks generated from document {document_id}")
                return 0

            documents = []
            payloads = []

            for chunk_idx, chunk in enumerate(chunks):
                try:
                    if not hasattr(chunk, "page_content"):
                        logger.warning(
                            f"Chunk {chunk_idx} missing page_content attribute for document {document_id}"
                        )
                        continue

                    content = chunk.page_content.strip() if chunk.page_content else ""
                    if not content:
                        logger.debug(
                            f"Skipping empty chunk {chunk_idx} for document {document_id}"
                        )
                        continue

                    documents.append(
                        {
                            self.dense_vector_name: models.Document(
                                text=content, model=self.DENSE_MODEL
                            ),
                            self.sparse_vector_name: models.Document(
                                text=content, model=self.SPARSE_MODEL
                            ),
                        }
                    )

                    chunk_metadata = chunk.metadata or {}

                    payloads.append(
                        {
                            "chunk_id": chunk_metadata.get(
                                "chunk_id", str(uuid.uuid4())
                            ),
                            "document_id": chunk_metadata.get(
                                "document_id", document_id
                            ),
                            "filename": chunk_metadata.get("filename", filename),
                            "content": content,
                            "content_type": chunk_metadata.get("content_type", "text"),
                            "page_number": chunk_metadata.get("page_number", 0),
                            "chunk_index": chunk_metadata.get("chunk_index", 0),
                            "chunk_size": len(content),
                            "language": chunk_metadata.get("language", "en"),
                            "heading_context": chunk_metadata.get("heading_context"),
                            "indexed_at": datetime.now().isoformat(),
                            **{
                                k: v
                                for k, v in chunk_metadata.items()
                                if k
                                not in [
                                    "chunk_id",
                                    "document_id",
                                    "filename",
                                    "content_type",
                                    "page_number",
                                    "chunk_index",
                                    "language",
                                    "heading_context",
                                ]
                            },
                        }
                    )

                except Exception as chunk_error:
                    logger.error(
                        f"Error processing chunk {chunk_idx} for document {document_id}: {chunk_error}"
                    )
                    continue

            if not documents:
                logger.warning(
                    f"No valid chunks with content found for document {document_id}"
                )
                return 0

            self.client.upload_collection(
                collection_name=self.collection_name,
                vectors=documents,
                payload=payloads,
                parallel=2,
            )

            logger.info(
                f"Successfully indexed {len(documents)} chunks for document {document_id} (official hybrid)"
            )
            return len(documents)

        except Exception as e:
            logger.error(f"Failed to index document {document_id}: {str(e)}")
            raise Exception(f"Failed to index document: {str(e)}")

    def hybrid_search(
        self,
        query: str,
        document_id: Optional[str] = None,
        chunk_types: Optional[List[str]] = None,
        limit: int = 10,
        score_threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search using official Qdrant native fusion.
        """
        try:
            query_filter = None
            if document_id:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )

            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=models.FusionQuery(
                    fusion=models.Fusion.RRF  # Reciprocal Rank Fusion
                ),
                prefetch=[
                    models.Prefetch(
                        query=models.Document(text=query, model=self.DENSE_MODEL),
                        using=self.dense_vector_name,
                        limit=limit * 2,
                    ),
                    models.Prefetch(
                        query=models.Document(text=query, model=self.SPARSE_MODEL),
                        using=self.sparse_vector_name,
                        limit=limit * 2,
                    ),
                ],
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            ).points

            results = []
            for point in search_result:
                results.append(
                    {
                        "chunk_id": point.id,
                        "score": point.score,
                        "search_type": "official_hybrid_rrf",
                        "content": point.payload["content"],
                        "document_id": point.payload["document_id"],
                        "content_type": point.payload.get("content_type", "text"),
                        "page_number": point.payload["page_number"],
                        "chunk_index": point.payload["chunk_index"],
                        "metadata": {
                            k: v
                            for k, v in point.payload.items()
                            if k
                            not in [
                                "content",
                                "document_id",
                                "content_type",
                                "page_number",
                                "chunk_index",
                            ]
                        },
                    }
                )

            logger.info(f"Official hybrid search completed: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Official hybrid search failed: {e}")
            raise Exception(f"Failed to perform hybrid search: {str(e)}")

    def search_documents(
        self,
        query: str,
        document_id: Optional[str] = None,
        chunk_types: Optional[List[str]] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Dense-only search for backward compatibility."""
        try:
            query_filter = None
            if document_id:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )

            search_results = self.client.query_points(
                collection_name=self.collection_name,
                query=models.Document(text=query, model=self.DENSE_MODEL),
                using=self.dense_vector_name,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            ).points

            results = []
            for point in search_results:
                results.append(
                    {
                        "chunk_id": point.id,
                        "score": point.score,
                        "search_type": "dense_only_official",
                        "content": point.payload["content"],
                        "document_id": point.payload["document_id"],
                        "content_type": point.payload.get("content_type", "text"),
                        "page_number": point.payload["page_number"],
                        "chunk_index": point.payload["chunk_index"],
                        "metadata": {
                            k: v
                            for k, v in point.payload.items()
                            if k
                            not in [
                                "content",
                                "document_id",
                                "content_type",
                                "page_number",
                                "chunk_index",
                            ]
                        },
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            raise Exception(f"Failed to search documents: {str(e)}")

    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document."""
        try:
            delete_result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                ),
            )

            # Check if the operation was successful
            if hasattr(delete_result, "operation_id") or delete_result:
                logger.info(f"Successfully deleted document {document_id} from Qdrant")
                return True
            else:
                logger.warning(
                    f"Delete operation for document {document_id} returned unexpected result"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {str(e)}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "total_points": info.points_count,
                "dense_vector_size": info.config.params.vectors[
                    self.dense_vector_name
                ].size,
                "distance_metric": info.config.params.vectors[
                    self.dense_vector_name
                ].distance,
                "has_sparse_vectors": bool(info.config.params.sparse_vectors),
                "collection_name": self.collection_name,
                "approach": "official_qdrant_hybrid_fastembed",
            }

        except Exception as e:
            return {"error": str(e)}


# Keep backward compatibility - this will use the older custom approach as fallback
QdrantHybridVectorStore = QdrantOfficialHybridStore
