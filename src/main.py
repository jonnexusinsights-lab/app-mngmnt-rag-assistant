from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import time
from src.core.config import settings
from src.features.rag.application.rag_service import rag_service
from src.features.rag.api.dtos import (
    ChatRequest,
    GenericResponse,
    IngestResponse,
    DocumentListResponse,
    DeleteResponse,
    QueryResult
)
from src.shared.errors.app_errors import BaseAppError, DomainError, InfrastructureError, ApplicationError

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# Security: CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(BaseAppError)
async def app_exception_handler(request: Request, exc: BaseAppError):
    status_code = 500
    if isinstance(exc, DomainError):
        status_code = 400
    elif isinstance(exc, ApplicationError):
        status_code = 401 # Default for app errors, can be refined

    return JSONResponse(
        status_code=status_code,
        content={
            "errors": [
                {
                    "code": exc.__class__.__name__,
                    "message": exc.message,
                    "details": exc.details
                }
            ],
            "meta": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "path": request.url.path
            }
        }
    )

# Serve static files for Frontend
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
async def root():
    return {"message": "ACE-Framework RAG Assistant is running"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": settings.APP_VERSION}

@app.get("/health/live")
async def liveness_check() -> dict[str, str]:
    return {"status": "live", "version": settings.APP_VERSION}

@app.get("/health/ready")
async def readiness_check() -> dict[str, str]:
    if not rag_service.is_ready():
         raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready", "version": settings.APP_VERSION}

@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents(files: list[UploadFile] = File(...)) -> IngestResponse:
    """
    Ingest multiple documents into the RAG system.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Create temporary directory if it doesn't exist
    temp_dir = "temp_ingest"
    os.makedirs(temp_dir, exist_ok=True)

    saved_paths: list[str] = []
    try:
        for file in files:
            safe_filename = os.path.basename(str(file.filename))
            file_location = os.path.join(temp_dir, safe_filename)

            with open(file_location, "wb+") as file_object:
                file_object.write(await file.read())
            saved_paths.append(file_location)

        # Process the saved files
        result = rag_service.ingest_documents(saved_paths)
        return IngestResponse(
            message="Processed batch.",
            total_files=len(files),
            engine_result=result
        )

    finally:
        # Cleanup temp files
        for path in saved_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        try:
             if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                 os.rmdir(temp_dir)
        except:
            pass

@app.post("/chat", response_model=QueryResult)
async def chat(request: ChatRequest) -> QueryResult:
    return rag_service.query(request.message, request.domain)

@app.post("/reset", response_model=GenericResponse)
async def reset_chat() -> GenericResponse:
    success = rag_service.reset()
    return GenericResponse(
        status="success" if success else "error",
        message="Chat history cleared"
    )

@app.get("/documents", response_model=DocumentListResponse)
async def list_docs() -> DocumentListResponse:
    docs = rag_service.list_documents()
    return DocumentListResponse(documents=docs)

@app.delete("/documents/{filename}", response_model=DeleteResponse)
async def delete_doc(filename: str) -> DeleteResponse:
    success = rag_service.delete_document(filename)
    if not success:
         raise HTTPException(status_code=404, detail=f"Document {filename} not found or could not be deleted")
    return DeleteResponse(status="success", message=f"Deleted {filename}")
