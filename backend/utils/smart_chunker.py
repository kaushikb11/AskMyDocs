import json
import re
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class MarkdownDocumentChunker:
    """Smart chunking strategy for MarkdownDocument that preserves semantic structure."""

    def __init__(
        self,
        base_chunk_size: int = 1200,
        chunk_overlap: int = 150,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2000,
        table_max_size: int = 3000,
    ):
        self.base_chunk_size = base_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.table_max_size = table_max_size

        # Create text splitter optimized for markdown with better boundaries
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=base_chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                "\n\n\n",  # Multiple line breaks (section boundaries)
                "\n\n",  # Double line breaks (paragraph separation)
                "\n# ",  # Markdown headings (major sections)
                "\n## ",  # Markdown subheadings
                "\n### ",  # Markdown sub-subheadings
                ". ",  # Sentences (better semantic boundaries)
                ";\n",  # List items or clauses
                ", ",  # Clauses
                "\n",  # Single line breaks
                " ",  # Words
                "",  # Characters
            ],
        )

        # Adaptive splitter for different content types
        self.adaptive_splitters = {
            "technical": RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n\n", "\n\n", ". ", "\n", " ", ""],
            ),
            "narrative": RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
                length_function=len,
                separators=["\n\n", ". ", "\n", " ", ""],
            ),
        }

    def chunk_markdown_document(
        self, document_id: str, filename: str, markdown_doc_data: Dict[str, Any]
    ) -> List[Document]:
        """
        Chunk a MarkdownDocument using adaptive sizing and semantic boundaries.

        Args:
            document_id: Document identifier
            filename: Document filename
            markdown_doc_data: Parsed MarkdownDocument JSON

        Returns:
            List of Document chunks optimized for user experience
        """
        all_chunks = []

        doc_analysis = self._analyze_document_complexity(markdown_doc_data)

        for page_idx, page in enumerate(markdown_doc_data.get("pages", [])):
            page_chunks = self._chunk_page(
                page=page,
                page_idx=page_idx,
                document_id=document_id,
                filename=filename,
                doc_analysis=doc_analysis,
            )
            all_chunks.extend(page_chunks)

        return all_chunks

    def _analyze_document_complexity(
        self, markdown_doc_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze document characteristics to determine optimal chunking strategy."""
        total_text = ""
        total_length = 0
        table_count = 0
        figure_count = 0
        heading_count = 0

        for page in markdown_doc_data.get("pages", []):
            content = page.get("markdown_content", "") or page.get("content", "")
            total_text += content.lower()
            total_length += len(content)
            table_count += len(page.get("tables", []) or [])
            figure_count += len(page.get("figures", []) or [])
            heading_count += content.count("#")

        avg_words_per_page = (
            total_length / max(len(markdown_doc_data.get("pages", [])), 1) / 5
        )  # rough word estimate
        structured_content_ratio = (table_count + figure_count) / max(
            len(markdown_doc_data.get("pages", [])), 1
        )

        return {
            "avg_words_per_page": avg_words_per_page,
            "table_count": table_count,
            "figure_count": figure_count,
            "heading_count": heading_count,
            "structured_content_ratio": structured_content_ratio,
            "total_pages": len(markdown_doc_data.get("pages", [])),
            "is_structured_document": structured_content_ratio > 0.5
            or heading_count > 20,
        }

    def _chunk_page(
        self,
        page: Dict[str, Any],
        page_idx: int,
        document_id: str,
        filename: str,
        doc_analysis: Dict[str, Any],
    ) -> List[Document]:
        """Chunk a single page with adaptive sizing based on document complexity."""
        chunks = []

        page_metadata = page.get("metadata", {})
        language = page_metadata.get("language", "en")

        # Chunk main text content with adaptive sizing
        markdown_content = page.get("markdown_content") or ""
        page_content = markdown_content.strip() if markdown_content else ""

        if not page_content:
            content = page.get("content") or ""
            page_content = content.strip() if content else ""

        if page_content:
            chunks.extend(
                self._chunk_text_content_adaptive(
                    content=page_content,
                    document_id=document_id,
                    filename=filename,
                    page_idx=page_idx,
                    language=language,
                    content_type="text",
                    doc_analysis=doc_analysis,
                )
            )

        # Process tables with preservation-first approach
        tables = page.get("tables", []) or []
        for table_idx, table in enumerate(tables):
            if table is None:
                continue
            table_chunks = self._chunk_table_preserving(
                table=table,
                table_idx=table_idx,
                document_id=document_id,
                filename=filename,
                page_idx=page_idx,
                language=language,
            )
            if table_chunks:
                chunks.extend(table_chunks)

        # Process figures as semantic units
        figures = page.get("figures", []) or []
        for figure_idx, figure in enumerate(figures):
            if figure is None:
                continue
            figure_chunk = self._chunk_figure(
                figure=figure,
                figure_idx=figure_idx,
                document_id=document_id,
                filename=filename,
                page_idx=page_idx,
                language=language,
            )
            if figure_chunk:
                chunks.append(figure_chunk)

        return chunks

    def _chunk_text_content_adaptive(
        self,
        content: str,
        document_id: str,
        filename: str,
        page_idx: int,
        language: str,
        content_type: str,
        doc_analysis: Dict[str, Any],
    ) -> List[Document]:
        """Chunk text content using adaptive sizing based on document complexity."""

        headings = self._extract_headings(content)

        # Choose appropriate splitter based on document characteristics
        if (
            doc_analysis.get("is_structured_document", False)
            or doc_analysis.get("avg_words_per_page", 0) > 800
        ):
            splitter = self.adaptive_splitters["technical"]
        elif doc_analysis.get("avg_words_per_page", 0) < 400:
            splitter = self.adaptive_splitters["narrative"]
        else:
            splitter = self.text_splitter

        text_chunks = splitter.split_text(content)

        chunks = []
        for chunk_idx, chunk_text in enumerate(text_chunks):
            if not chunk_text or len(chunk_text.strip()) < self.min_chunk_size:
                continue

            chunk_heading = self._find_relevant_heading(chunk_text, headings)
            quality_score = self._calculate_content_quality(chunk_text)

            chunk = Document(
                page_content=chunk_text,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": page_idx,
                    "chunk_index": chunk_idx,
                    "content_type": content_type,
                    "language": language,
                    "heading_context": chunk_heading,
                    "chunk_size": len(chunk_text),
                    "chunk_id": str(uuid.uuid4()),
                    "original_chunk_ref": f"{document_id}_p{page_idx}_c{chunk_idx}",
                    "quality_score": quality_score,
                    "is_complete_section": self._is_complete_section(chunk_text),
                    "is_structured_document": doc_analysis.get(
                        "is_structured_document", False
                    ),
                    "document_complexity": self._get_complexity_level(doc_analysis),
                },
            )
            chunks.append(chunk)

        return chunks

    def _chunk_table_preserving(
        self,
        table: Dict[str, Any],
        table_idx: int,
        document_id: str,
        filename: str,
        page_idx: int,
        language: str,
    ) -> List[Document]:
        """Process table with preservation-first approach for better UX."""
        chunks = []

        table_metadata = table.get("metadata", {})
        table_title = table_metadata.get("title", "")
        table_caption = table_metadata.get("caption", "")

        table_content_raw = table.get("content") or ""
        table_content = table_content_raw.strip() if table_content_raw else ""
        if not table_content:
            return chunks

        full_table_content = ""
        if table_title:
            full_table_content += f"Table {table_idx + 1}: {table_title}\n"
        if table_caption:
            full_table_content += f"Caption: {table_caption}\n"
        full_table_content += f"\n{table_content}"

        # Try to preserve table integrity - only chunk if absolutely necessary
        if len(full_table_content) <= self.table_max_size:
            chunk = Document(
                page_content=full_table_content,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": page_idx,
                    "chunk_index": 0,
                    "content_type": "table",
                    "table_index": table_idx,
                    "table_title": table_title,
                    "table_caption": table_caption,
                    "language": language,
                    "chunk_size": len(full_table_content),
                    "chunk_id": str(uuid.uuid4()),
                    "original_chunk_ref": f"{document_id}_p{page_idx}_t{table_idx}",
                    "is_complete_table": True,
                    "quality_score": 0.9,
                },
            )
            chunks.append(chunk)
        else:
            table_chunks = self.text_splitter.split_text(full_table_content)
            for chunk_idx, chunk_text in enumerate(table_chunks):
                chunk = Document(
                    page_content=chunk_text,
                    metadata={
                        "document_id": document_id,
                        "filename": filename,
                        "page_number": page_idx,
                        "chunk_index": chunk_idx,
                        "content_type": "table",
                        "table_index": table_idx,
                        "table_title": table_title,
                        "table_caption": table_caption,
                        "language": language,
                        "chunk_size": len(chunk_text),
                        "chunk_id": str(uuid.uuid4()),
                        "original_chunk_ref": f"{document_id}_p{page_idx}_t{table_idx}_c{chunk_idx}",
                        "is_complete_table": False,
                        "table_part": f"Part {chunk_idx + 1} of {len(table_chunks)}",
                        "quality_score": 0.6,
                    },
                )
                chunks.append(chunk)

        return chunks

    def _chunk_figure(
        self,
        figure: Dict[str, Any],
        figure_idx: int,
        document_id: str,
        filename: str,
        page_idx: int,
        language: str,
    ) -> Optional[Document]:
        """Process figure as a semantic unit."""

        figure_title = figure.get("title", "")
        figure_caption = figure.get("caption", "")
        figure_content = figure.get("content", "")

        full_figure_content = ""
        if figure_title:
            full_figure_content += f"Figure: {figure_title}\n"
        if figure_caption:
            full_figure_content += f"Caption: {figure_caption}\n"
        if figure_content:
            full_figure_content += f"Description: {figure_content}"

        if not full_figure_content or not full_figure_content.strip():
            return None

        return Document(
            page_content=full_figure_content,
            metadata={
                "document_id": document_id,
                "filename": filename,
                "page_number": page_idx,
                "chunk_index": 0,
                "content_type": "figure",
                "figure_index": figure_idx,
                "figure_title": figure_title,
                "figure_caption": figure_caption,
                "language": language,
                "chunk_size": len(full_figure_content),
                "chunk_id": str(uuid.uuid4()),
                "original_chunk_ref": f"{document_id}_p{page_idx}_f{figure_idx}",
            },
        )

    def _extract_headings(self, content: str) -> List[Dict[str, Any]]:
        """Extract markdown headings for context."""
        headings = []
        lines = content.split("\n")

        for line_idx, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                heading_text = line.lstrip("#").strip()
                if heading_text:
                    headings.append(
                        {"level": level, "text": heading_text, "line_index": line_idx}
                    )

        return headings

    def _find_relevant_heading(
        self, chunk_text: str, headings: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find the most relevant heading for a chunk."""
        if not headings:
            return None

        for heading in reversed(headings):
            if heading["text"].lower() in chunk_text.lower():
                return heading["text"]

        return headings[0]["text"] if headings else None

    def _calculate_content_quality(self, content: str) -> float:
        """Calculate content quality score for better ranking and UX."""
        score = 0.5

        if content.strip().endswith((".", "!", "?", ":")):
            score += 0.2

        if any(
            content.strip().startswith(marker)
            for marker in ["#", "-", "*", "1.", "2.", "3."]
        ):
            score += 0.1

        if len(content.strip()) > 800:
            score += 0.1

        if content.count("...") > 2 or content.count("[truncated]") > 0:
            score -= 0.3

        return min(1.0, max(0.1, score))

    def _is_complete_section(self, content: str) -> bool:
        """Determine if chunk represents a complete semantic section."""
        content = content.strip()

        starts_with_header = any(
            content.startswith(marker) for marker in ["#", "##", "###"]
        )
        ends_properly = content.endswith((".", "!", "?", ":"))
        has_good_length = len(content) > 500

        return starts_with_header and ends_properly and has_good_length

    def _get_complexity_level(self, doc_analysis: Dict[str, Any]) -> str:
        """Determine document complexity level based on analysis."""
        structured_ratio = doc_analysis.get("structured_content_ratio", 0)
        avg_words = doc_analysis.get("avg_words_per_page", 0)

        if structured_ratio > 0.5 or avg_words > 1000:
            return "high"
        elif structured_ratio > 0.2 or avg_words > 500:
            return "medium"
        else:
            return "low"
