import asyncio
import base64
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF for PDF to image conversion
import instructor
from config import settings
from dto.openai_models import (
    MarkdownDocument,
    MarkdownFigure,
    MarkdownPage,
    MarkdownTable,
    OpenAIExtractionRequest,
    OpenAIExtractionResponse,
    PageMetadata,
)
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIVisionClient:
    """Client for OpenAI Vision API to extract content from PDFs."""

    def __init__(self):
        # Initialize OpenAI client with Instructor for structured responses
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.client = instructor.from_openai(openai_client)
        self.model = "gpt-4.1"

    def _pdf_to_images(self, pdf_path: str, dpi: int = 150) -> List[bytes]:
        """Convert PDF pages to images for vision processing."""
        images = []

        # Open PDF
        pdf_document = fitz.open(pdf_path)

        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]

            # Convert page to image
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # Scale factor for DPI
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            images.append(img_data)

        pdf_document.close()
        return images

    def _encode_image_to_base64(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64 string."""
        return base64.b64encode(image_bytes).decode("utf-8")

    async def _extract_page_content(
        self,
        image_base64: str,
        page_number: int,
        extract_tables: bool = True,
        extract_figures: bool = True,
    ) -> tuple[MarkdownPage, int]:
        """Extract content from a single page using GPT-4.1 with vision capabilities and Instructor."""

        try:
            # Use Instructor to get structured response with token tracking
            completion = await self.client.chat.completions.create(
                model=self.model,
                response_model=MarkdownPage,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert document analysis AI. Extract content from this PDF page and return it as structured data.

Instructions:
1. Convert all text content to clean markdown format preserving structure and hierarchy
2. For TABLES (if extract_tables=True):
   - Extract complete table structure with headers and ALL data rows
   - Create proper TableHeader objects with name, column index, and data type
   - Extract ALL table data as structured rows (dictionaries)
   - Include table titles, captions, and notes from the document
   - Do NOT leave data arrays empty - extract the actual table content
3. For FIGURES/CHARTS (if extract_figures=True):
   - Provide detailed descriptions of charts, graphs, diagrams, and images
   - Include any captions, titles, or labels visible in the figure
   - Describe visual elements, trends, relationships shown
   - Extract any text or numbers visible in the figure
4. Detect the document language accurately
5. Maintain reading order and document layout relationships
6. Be thorough - do not skip content or leave fields empty unless truly no data exists""",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""Analyze this PDF page (page {page_number + 1}) and extract:

TEXT CONTENT:
- Convert all text to clean markdown with proper headings, paragraphs, lists
- Preserve document structure and formatting

TABLES (extract_tables={extract_tables}):
- For each table: extract headers with proper names and data types
- Extract ALL table rows as structured data - do not leave data empty
- Include table titles, captions, footnotes
- Create complete TableHeader objects with id, column, name, dtype
- Populate data array with actual table content as dictionaries

FIGURES (extract_figures={extract_figures}):
- Describe all charts, graphs, diagrams, images in detail
- Include titles, captions, axis labels, legends
- Explain what the figure shows, trends, relationships
- Extract any visible text or numerical data

LANGUAGE:
- Detect the primary language of the page content

Be thorough and complete - extract ALL visible content and data.""",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=4000,
                temperature=0.1,  # Low temperature for consistent extraction
            )

            # Get token usage from the completion object
            tokens_used = 0
            if hasattr(completion, "_raw_response") and completion._raw_response:
                usage = getattr(completion._raw_response, "usage", None)
                if usage:
                    tokens_used = usage.total_tokens

            # Return both the parsed page data and token usage
            return completion, tokens_used

        except Exception as e:
            # Log the error for debugging
            logger.error(
                f"OpenAI Vision extraction error for page {page_number + 1}: {str(e)}"
            )

            # Return minimal page with error message and zero tokens
            return (
                MarkdownPage(
                    metadata=PageMetadata(language="en", page_number=page_number),
                    content=f"OpenAI Vision extraction failed for page {page_number + 1}. This could be due to complex layout, poor image quality, or API issues.",
                    markdown_content="",
                    tables=[],
                    figures=[],
                ),
                0,
            )

    async def extract_document_content(
        self, request: OpenAIExtractionRequest
    ) -> OpenAIExtractionResponse:
        """Extract content from entire PDF document."""
        start_time = time.time()

        try:
            # Convert PDF to images
            images = self._pdf_to_images(request.file_path)

            # Process each page concurrently (with rate limiting)
            pages = []
            total_tokens = 0

            # Process pages in batches to avoid rate limits
            batch_size = 3  # Adjust based on rate limits
            for i in range(0, len(images), batch_size):
                batch = images[i : i + batch_size]
                tasks = []

                for j, image_bytes in enumerate(batch):
                    page_number = i + j
                    image_base64 = self._encode_image_to_base64(image_bytes)

                    task = self._extract_page_content(
                        image_base64=image_base64,
                        page_number=page_number,
                        extract_tables=request.extract_tables,
                        extract_figures=request.extract_figures,
                    )
                    tasks.append(task)

                # Process batch
                batch_results = await asyncio.gather(*tasks)

                # Unpack pages and tokens from each result
                for page_data, page_tokens in batch_results:
                    pages.append(page_data)
                    total_tokens += page_tokens

                # Rate limiting - wait between batches
                if i + batch_size < len(images):
                    await asyncio.sleep(1)  # 1 second between batches

            # Create MarkdownDocument
            markdown_document = MarkdownDocument(pages=pages)

            processing_time = time.time() - start_time

            return OpenAIExtractionResponse(
                document_id=request.document_id,
                markdown_document=markdown_document,
                processing_time=processing_time,
                total_pages=len(pages),
                total_tokens_used=total_tokens,  # Now tracking actual token usage
                extraction_timestamp=datetime.now(),
            )

        except Exception as e:
            raise Exception(f"Failed to extract document content: {str(e)}")

    async def extract_single_page(
        self,
        pdf_path: str,
        page_number: int,
        extract_tables: bool = True,
        extract_figures: bool = True,
    ) -> MarkdownPage:
        """Extract content from a single page (for testing)."""
        images = self._pdf_to_images(pdf_path)

        if page_number >= len(images):
            raise ValueError(f"Page {page_number} not found in document")

        image_base64 = self._encode_image_to_base64(images[page_number])

        page_data, tokens_used = await self._extract_page_content(
            image_base64=image_base64,
            page_number=page_number,
            extract_tables=extract_tables,
            extract_figures=extract_figures,
        )

        # For single page extraction, just return the page data
        # (token usage could be logged or returned separately if needed)
        logger.info(f"Single page extraction used {tokens_used} tokens")
        return page_data


class OpenAISummaryClient:
    """Client for OpenAI API to generate document summaries."""

    def __init__(self):
        # Initialize OpenAI client for summary generation
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.client = openai_client
        self.model = "gpt-4.1"  # Using gpt-4.1 for consistency and better performance

    async def generate_summary(
        self,
        document_content: str,
        summary_type: str,
        document_title: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        include_key_points: bool = True,
        include_tables_summary: bool = True,
        include_figures_summary: bool = True,
    ) -> Dict[str, Any]:
        """Generate a summary of the document content using OpenAI."""

        # Build the system prompt based on summary type
        system_prompt = self._build_system_prompt(
            summary_type=summary_type,
            include_key_points=include_key_points,
            include_tables_summary=include_tables_summary,
            include_figures_summary=include_figures_summary,
            custom_instructions=custom_instructions,
        )

        # Build the user prompt with document content
        user_prompt = self._build_user_prompt(
            document_content=document_content,
            document_title=document_title,
            summary_type=summary_type,
        )

        try:
            start_time = time.time()

            # Generate summary using OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for more consistent summaries
                max_tokens=2000,  # Adjust based on summary type
            )

            generation_time = time.time() - start_time

            # Extract the response content
            summary_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            # Parse the structured response
            parsed_summary = self._parse_summary_response(summary_content, summary_type)

            return {
                "success": True,
                "summary": parsed_summary,
                "generation_time": generation_time,
                "tokens_used": tokens_used,
                "confidence_score": 0.85,  # Could be enhanced with actual confidence scoring
            }

        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "generation_time": time.time() - start_time,
                "tokens_used": 0,
            }

    def _build_system_prompt(
        self,
        summary_type: str,
        include_key_points: bool,
        include_tables_summary: bool,
        include_figures_summary: bool,
        custom_instructions: Optional[str],
    ) -> str:
        """Build the system prompt based on summary requirements."""

        base_prompt = """You are an expert document analyst specializing in creating high-quality summaries.
Your task is to analyze the provided document content and create a comprehensive, accurate summary."""

        # Type-specific instructions
        type_instructions = {
            "brief": "Create a concise summary in 1-2 paragraphs that captures the main points and key findings.",
            "detailed": "Create a comprehensive summary in 3-5 paragraphs with detailed analysis of all major sections.",
            "bullet_points": "Create a structured summary using clear bullet points for easy scanning and understanding.",
            "executive": "Create an executive summary suitable for business leaders, focusing on key decisions, outcomes, and implications.",
        }

        prompt = f"{base_prompt}\n\nSummary Type: {type_instructions.get(summary_type, type_instructions['brief'])}"

        # Add optional components
        if include_key_points:
            prompt += "\n\n- Extract and list the most important key points"

        if include_tables_summary:
            prompt += "\n- Summarize any tables or data presented"

        if include_figures_summary:
            prompt += "\n- Describe any figures, charts, or visual elements mentioned"

        if custom_instructions:
            prompt += f"\n\nAdditional Instructions: {custom_instructions}"

        prompt += (
            "\n\nFormat your response as structured text that can be easily parsed."
        )

        return prompt

    def _build_user_prompt(
        self, document_content: str, document_title: Optional[str], summary_type: str
    ) -> str:
        """Build the user prompt with document content."""

        prompt = "Please analyze and summarize the following document:\n\n"

        if document_title:
            prompt += f"Document Title: {document_title}\n\n"

        prompt += f"Document Content:\n{document_content}\n\n"

        # Add type-specific instructions
        if summary_type == "bullet_points":
            prompt += "Please provide the summary in clear bullet point format."
        elif summary_type == "executive":
            prompt += (
                "Please focus on executive-level insights and actionable information."
            )

        return prompt

    def _parse_summary_response(
        self, content: str, summary_type: str
    ) -> Dict[str, Any]:
        """Parse the OpenAI response into structured summary data."""

        # For now, return the content as overview
        # This could be enhanced to parse structured responses
        lines = content.strip().split("\n")

        # Extract title if present (first line if it looks like a title)
        title = None
        overview_start = 0

        if lines and (lines[0].startswith("#") or lines[0].endswith(":")):
            title = lines[0].strip("#").strip(":").strip()
            overview_start = 1

        # Join remaining content as overview
        overview = "\n".join(lines[overview_start:]).strip()

        # Extract key points if bullet format
        key_points = []
        if summary_type == "bullet_points" or "•" in overview or "-" in overview:
            for line in lines:
                line = line.strip()
                if line.startswith(("•", "-", "*")) or line.startswith(
                    tuple(f"{i}." for i in range(1, 20))
                ):
                    point = line.lstrip("•-* ").split(".", 1)[-1].strip()
                    if point:
                        key_points.append(point)

        return {
            "title": title,
            "overview": overview,
            "key_points": key_points,
            "sections": [],  # Could be enhanced for detailed summaries
        }
