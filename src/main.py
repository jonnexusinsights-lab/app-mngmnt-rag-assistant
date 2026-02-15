from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import shutil
import os
from src.core.config import settings
from src.services.rag_engine import rag_service

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# Serve static files for Frontend
app.mount("/static", StaticFiles(directory="src/static"), name="static")

class ChatRequest(BaseModel):
    message: str
    domain: str = "hr"

@app.get("/")
async def root():
    return {"message": "ACE-Framework RAG Assistant is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    # Save temp file
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ingest
        result = rag_service.ingest_document(file_path)

        # Cleanup
        os.remove(file_path)

        if result["status"] == "error":
             raise HTTPException(status_code=500, detail=result["message"])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    # response is now a dict with 'response' and 'sources'
    return rag_service.query(request.message, request.domain)

@app.post("/reset")
async def reset_chat():
    success = rag_service.reset()
    return {"status": "success" if success else "error", "message": "Chat history cleared"}

@app.get("/documents")
async def list_docs():
    docs = rag_service.list_documents()
    return {"documents": docs}

@app.delete("/documents/{filename}")
async def delete_doc(filename: str):
    success = rag_service.delete_document(filename)
    if not success:
         raise HTTPException(status_code=500, detail="Failed to delete document")
    return {"status": "success", "message": f"Deleted {filename}"}
