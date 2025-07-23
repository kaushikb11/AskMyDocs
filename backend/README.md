# Document Intelligence Platform - Backend

FastAPI backend for the intelligent document processing platform with hybrid RAG search.

## 🚀 Quick Start

👉 **For immediate setup and testing**: See **[QUICKSTART.md](QUICKSTART.md)**

### TL;DR - 3 Commands
```bash
cd backend && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Then test at: http://localhost:8000/docs

### What Happens Automatically
- ✅ Database setup (SQLite) with table creation
- ✅ Upload directory creation  
- ✅ FastAPI server with auto-reload
- ✅ Interactive API documentation

### API Documentation
Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🧪 Testing

### ⭐ Recommended: Swagger UI Testing
1. Start the server: `python main.py`
2. Open **http://localhost:8000/docs** 
3. **Interactive testing** with visual interface:
   - Click endpoints → "Try it out" → Execute
   - Upload PDFs directly in the browser
   - See live request/response examples

### Manual cURL Testing
```bash
# Upload a document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your_document.pdf"

# List documents
curl http://localhost:8000/api/v1/documents
```

## 📁 Project Structure

```
backend/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration and settings
├── constants.py         # Application constants and enums
├── exceptions.py        # Custom exception classes
├── requirements.txt     # Python dependencies
├── db/                  # Database layer
│   ├── __init__.py      # Database engine and initialization
│   └── models.py        # Database models (SQLModel entities)
├── schemas/             # API response schemas
│   ├── __init__.py      # Schema exports
│   └── responses.py     # API response models
├── dto/                 # Data Transfer Objects
│   ├── chat_dto.py      # Chat database operations
│   ├── chat_models.py   # Chat request/response models
│   ├── documents_dto.py # Document database operations
│   ├── openai_models.py # OpenAI API models
│   └── upload_dto.py    # Document upload models
├── routes/              # API route handlers
│   ├── chat.py          # Chat/Q&A endpoints
│   └── documents.py     # Document management endpoints
└── utils/               # Utility functions
    ├── agentic_rag.py   # Agentic RAG system with LangGraph
    ├── document_processor.py # Document processing pipeline
    ├── logging.py       # Logging configuration
    ├── openai_client.py # OpenAI Vision API client
    ├── qdrant_client.py # Qdrant vector database client
    ├── serialization.py # JSON serialization utilities
    └── smart_chunker.py # Smart document chunking
```

## 🔧 API Endpoints

### Document Management
- `POST /api/v1/documents/upload` - Upload PDF document
- `GET /api/v1/documents` - List uploaded documents  
- `GET /api/v1/documents/{doc_id}` - Get document details
- `GET /api/v1/documents/{doc_id}/status` - Check processing status
- `DELETE /api/v1/documents/{doc_id}` - Delete document

### Chat & Q&A
- `POST /api/v1/chat/ask` - Ask questions about documents using Agentic RAG
- `POST /api/v1/chat/refresh-rag` - Refresh the RAG system
- `GET /api/v1/chat/status` - Check RAG system status

## 🔍 Features

- **OpenAI Vision Integration**: Advanced PDF content extraction with GPT-4 Vision
- **Structured Content Parsing**: Extracts text, tables, and figures as MarkdownDocument
- **Qdrant Vector Database**: Production-ready vector search and indexing
- **Semantic Chunking**: Intelligent text segmentation with overlap
- **Vector Search**: High-performance similarity search with embeddings
- **Document Processing Pipeline**: Automated extraction and indexing workflow
- **REST API**: Clean FastAPI endpoints for all operations
- **Processing Status Tracking**: Real-time monitoring of document processing

## 🛠 Development

### Running in Development Mode
```bash
# With auto-reload
python main.py

# Or with uvicorn
uvicorn main:app --reload --log-level debug
```

### Testing
```bash
pytest
```

### Code Formatting
```bash
black .
```

## 🏗️ **Architecture Overview**

### **PDF Upload & Processing Pipeline**
```
PDF Upload → OpenAI Vision Extraction → MarkdownDocument → Qdrant Indexing → Vector Search
```

1. **PDF Upload**: Secure file upload with validation
2. **OpenAI Vision**: Extract structured content as MarkdownDocument (text, tables, figures)
3. **Chunking**: Convert MarkdownDocument to searchable chunks with overlap
4. **Qdrant Indexing**: Generate embeddings and store in vector database
5. **Vector Search**: Semantic search across document content

### **Key Components**
- `OpenAIVisionClient`: Handles GPT-4 Vision API for content extraction
- `QdrantVectorStore`: Vector database operations and semantic search
- `DocumentProcessor`: Orchestrates the entire pipeline
- `DocumentsAPI`: REST API endpoints for upload and processing

## 📋 Implementation Status

✅ **Completed Tasks**
1. **Core Foundation**
   - FastAPI app setup with middleware
   - Configuration management with environment variables
   - Database models (SQLModel) and DTOs

2. **Document Processing Pipeline**
   - OpenAI Vision integration for PDF content extraction
   - MarkdownDocument structure for structured content
   - Qdrant vector database integration
   - Semantic chunking with overlap strategy
   - Embedding generation and indexing

3. **API Endpoints**
   - Document upload and management
   - Document processing (OpenAI + Qdrant)
   - Vector search functionality
   - Processing status tracking

4. **Chat/Q&A System**
   - Agentic RAG system with LangGraph
   - Enhanced question answering with context
   - Source attribution with chunk references
   - Session-based conversation support

🎯 **System Architecture**
- **Agentic RAG**: LangGraph-based intelligent document querying
- **Hybrid Search**: Semantic + keyword search with Qdrant
- **Document Processing**: OpenAI Vision + smart chunking
- **Production Ready**: Environment-based configuration, proper logging
