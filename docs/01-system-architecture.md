# System Architecture Overview

This document provides a comprehensive overview of the Document Intelligence Platform architecture, showing how the frontend, backend, AI services, and data storage layers interact.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React Frontend<br/>Port: 5173]
        APP[App.tsx<br/>Main Application]
        CHAT[ChatInterface<br/>Conversation UI]
        DOCS[DocumentList<br/>Document Management]
        UPLOAD[FileUpload<br/>PDF Upload]
    end

    subgraph "Backend Layer"
        API[FastAPI Server<br/>Port: 8000]
        DOC_API[Documents API<br/>/api/v1/documents]
        CHAT_API[Chat API<br/>/api/v1/chat]
        PROC[DocumentProcessor<br/>Processing Pipeline]
    end

    subgraph "AI Services"
        OPENAI[OpenAI Vision<br/>gpt-4.1]
        RAG[Agentic RAG<br/>LangGraph]
        EMBEDDING[Text Embedding<br/>text-embedding-3-small]
    end

    subgraph "Data Storage"
        DB[(SQLite Database<br/>Documents & Chats)]
        VECTOR[(Qdrant Vector DB<br/>Hybrid Search)]
        FILES[File Storage<br/>./uploads/]
    end

    subgraph "Document Processing Flow"
        PDF[PDF Upload] --> EXTRACT[Vision Extraction]
        EXTRACT --> CHUNK[Smart Chunking]
        CHUNK --> EMBED[Generate Embeddings]
        EMBED --> INDEX[Vector Indexing]
    end

    %% Frontend to Backend
    UI --> API
    APP --> DOC_API
    APP --> CHAT_API
    CHAT --> CHAT_API
    DOCS --> DOC_API
    UPLOAD --> DOC_API

    %% Backend to AI Services
    DOC_API --> PROC
    CHAT_API --> RAG
    PROC --> OPENAI
    RAG --> OPENAI
    PROC --> EMBEDDING

    %% Backend to Storage
    DOC_API --> DB
    CHAT_API --> DB
    DOC_API --> FILES
    PROC --> VECTOR
    RAG --> VECTOR

    %% Document Processing
    DOC_API --> PDF
    PDF --> OPENAI
    OPENAI --> CHUNK
    CHUNK --> EMBEDDING
    EMBEDDING --> VECTOR

    style UI fill:#e1f5fe
    style API fill:#f3e5f5
    style OPENAI fill:#fff3e0
    style VECTOR fill:#e8f5e8
    style DB fill:#fff8e1
```

## Architecture Components

### Frontend Layer
- **React Frontend**: Modern SPA built with React 19, TypeScript, and Tailwind CSS
- **Main Application**: Central App.tsx component managing view states and routing
- **Chat Interface**: Real-time conversation interface with session support
- **Document Management**: List, upload, and manage PDF documents
- **File Upload**: Drag-and-drop PDF upload with validation

### Backend Layer
- **FastAPI Server**: High-performance async Python web framework
- **Documents API**: RESTful endpoints for document management and processing
- **Chat API**: Conversational endpoints with agentic RAG integration
- **Document Processor**: Orchestrates the complete document processing pipeline

### AI Services
- **OpenAI Vision**: GPT-4.1 for advanced PDF content extraction
- **Agentic RAG**: LangGraph-powered intelligent document querying
- **Text Embedding**: OpenAI embeddings for semantic search

### Data Storage
- **SQLite Database**: Document metadata, conversations, and chat history
- **Qdrant Vector DB**: High-performance vector search with hybrid capabilities
- **File Storage**: Local filesystem storage for uploaded PDFs

## Key Features

1. **Intelligent Document Processing**: Vision-based PDF extraction with structured content parsing
2. **Hybrid Search**: Combines semantic and keyword search for optimal retrieval
3. **Conversational AI**: Session-based chat with document context awareness
4. **Real-time Processing**: Background document processing with status tracking
5. **Modern UI/UX**: Responsive design with dark/light theme support

## Technology Stack

### Frontend
- React 19 + TypeScript
- Tailwind CSS + Shadcn UI
- Vite build system
- React Query for state management

### Backend
- Python 3.9+ with FastAPI
- SQLModel for database ORM
- Pydantic for data validation
- LangGraph for agentic workflows

### AI & Data
- OpenAI GPT-4.1 Vision API
- Qdrant vector database
- LangChain for AI orchestration
- PyMuPDF for PDF processing 
