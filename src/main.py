from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import shutil
import os
import time
from pathlib import Path
from src.core.config import settings
from src.services.rag_engine import rag_service
from src.core.errors import BaseAppError, DomainError, InfrastructureError, ApplicationError

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# Global Exception Handler
@app.exception_handler(BaseAppError)
async def app_exception_handler(request: Request, exc: BaseAppError) -> JSONResponse:
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

class ChatRequest(BaseModel):
    message: str
    domain: str = "hr"

@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "ACE-Framework RAG Assistant is running"}

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "version": settings.APP_VERSION}

@app.post("/ingest")
async def ingest_documents(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """
    Ingest multiple documents into the RAG system.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Create temporary directory if it doesn't exist
    temp_dir = Path("temp_ingest")
    temp_dir.mkdir(exist_ok=True)

    saved_paths: List[Path] = []
    try:
        for file in files:
            # Sanitize filename
            if not file.filename:
                continue

            safe_filename = Path(file.filename).name
            file_location = temp_dir / safe_filename

            with open(file_location, "wb+") as file_object:
                file_object.write(await file.read())
            saved_paths.append(file_location)

        # Process the saved files
        result = rag_service.ingest_documents(saved_paths)
        return {
            "message": "Processed batch.",
            "total_files": len(files),
            "engine_result": result
        }

    finally:
        # Cleanup temp files
        for path in saved_paths:
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass
        try:
             if temp_dir.exists() and not any(temp_dir.iterdir()):
                 temp_dir.rmdir()
        except Exception:
            pass

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    return rag_service.query(request.message, request.domain)

@app.post("/reset")
async def reset_chat() -> Dict[str, Any]:
    success = rag_service.reset()
    return {"status": "success" if success else "error", "message": "Chat history cleared"}

@app.get("/documents")
async def list_docs() -> Dict[str, List[str]]:
    docs = rag_service.list_documents()
    return {"documents": docs}

@app.delete("/documents/{filename}")
async def delete_doc(filename: str) -> Dict[str, str]:
    success = rag_service.delete_document(filename)
    if not success:
         raise HTTPException(status_code=404, detail=f"Document {filename} not found or could not be deleted")
    return {"status": "success", "message": f"Deleted {filename}"}
