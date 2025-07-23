from contextlib import asynccontextmanager

from config import settings
from exceptions import DocumentIntelligenceError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from schemas.responses import HealthCheckResponse, ResponseHelper
from utils.logging import get_logger, setup_logging

# Setup structured logging
setup_logging(
    debug=settings.debug,
    structured_logs=False,  # Use colored logs for development
    log_level="DEBUG" if settings.debug else "INFO",
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Document Intelligence Platform...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Upload directory: {settings.upload_dir}")

    try:
        logger.info("🗄️  Initializing database...")
        from db import create_db_and_tables, get_engine

        create_db_and_tables()

        engine = get_engine()
        from sqlalchemy import text
        from sqlmodel import Session

        with Session(engine) as session:
            result = session.execute(text("SELECT 1"))
            result.fetchone()

        logger.info("✅ Database initialized successfully")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise e

    import os

    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info(f"📁 Upload directory ready: {settings.upload_dir}")

    logger.info("✅ Application startup complete!")
    logger.info("🌐 Server will start at: http://localhost:8000")
    logger.info("📖 Interactive API docs: http://localhost:8000/docs")
    logger.info("🔍 Health check: http://localhost:8000/health")
    logger.info("📋 Available endpoints:")
    logger.info("   • POST /api/v1/documents/upload - Upload PDF")
    logger.info("   • GET  /api/v1/documents - List documents")
    logger.info("   • GET  /api/v1/documents/{id} - Get document")
    logger.info("   • GET  /api/v1/documents/{id}/status - Check status")
    logger.info("   • DELETE /api/v1/documents/{id} - Delete document")

    yield

    logger.info("👋 Shutting down Document Intelligence Platform...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="An intelligent PDF reader and document Q&A assistant with hybrid RAG search",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
)


@app.exception_handler(DocumentIntelligenceError)
async def document_intelligence_exception_handler(
    request, exc: DocumentIntelligenceError
):
    logger.error(
        f"Application error: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unexpected exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INT_001",
            "message": str(exc) if settings.debug else "Internal server error occurred",
            "timestamp": f"{__import__('datetime').datetime.now().isoformat()}",
        },
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    services = {
        "database": True,
        "vector_store": True,
        "openai_api": True,
    }

    return ResponseHelper.health_check(services=services, version="1.0.0")


@app.get("/")
async def root():
    return {
        "message": "Welcome to Document Intelligence Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


from routes.chat import ChatAPI
from routes.documents import DocumentsAPI

documents_api = DocumentsAPI()
chat_api = ChatAPI()

app.include_router(documents_api.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(chat_api.router, prefix="/api/v1/chat", tags=["chat"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
