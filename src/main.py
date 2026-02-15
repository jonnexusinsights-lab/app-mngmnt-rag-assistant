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
async def ingest_documents(files: list[UploadFile] = File(...)):
    """
    Ingest multiple documents into the RAG system.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    uploaded_count = 0
    errors = []

    # Create temporary directory if it doesn't exist
    temp_dir = "temp_ingest"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        saved_paths = []
        for file in files:
            try:
                # Sanitize filename
                safe_filename = os.path.basename(file.filename)
                file_location = os.path.join(temp_dir, safe_filename)

                with open(file_location, "wb+") as file_object:
                    file_object.write(await file.read())
                saved_paths.append(file_location)
            except Exception as e:
                errors.append(f"Failed to save {file.filename}: {str(e)}")

        # Process the saved files
        if saved_paths:
            # Call the batch ingestion method
            # Note: We need to ensure rag_engine has this method. It was added in previous steps.
            result = rag_service.ingest_documents(saved_paths)

            if result.get("status") == "success":
                uploaded_count = result.get("chunks", 0) # API returns chunks count, or meaningful stats
            else:
                errors.append(f"Engine Ingestion Error: {result.get('message')}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp files
        if 'saved_paths' in locals():
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

    return {
        "message": f"Processed batch.",
        "errors": errors,
        "total_files": len(files)
    }

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
