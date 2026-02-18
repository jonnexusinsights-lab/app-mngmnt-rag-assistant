from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
from src.features.rag.application.rag-service import RAGService
from src.features.rag.infrastructure.vector-store import VectorStoreManager
from src.features.rag.infrastructure.llm-client import LLMClient
from src.features.rag.infrastructure.reranker import CustomReranker

# Dependency Injection for the Router
# In a real app, this might be handled via a DI container or FastAPI Depends
# For this MVP, we initialize the service instance here or pass it in.
vs_manager = VectorStoreManager()
llm_client = LLMClient()
reranker = CustomReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
rag_service = RAGService(vs_manager, llm_client, reranker)

router = APIRouter(prefix="/rag", tags=["RAG"])

class ChatRequest(BaseModel):
    message: str
    domain: str = "hr"

@router.post("/ingest")
async def ingest_documents(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    temp_dir = Path("temp_ingest")
    temp_dir.mkdir(exist_ok=True)
    saved_paths: List[Path] = []

    try:
        for file in files:
            if not file.filename: continue
            file_location = temp_dir / Path(file.filename).name
            with open(file_location, "wb+") as f:
                f.write(await file.read())
            saved_paths.append(file_location)

        result = rag_service.ingest_documents(saved_paths)
        return {"message": "Processed batch.", "total_files": len(files), "engine_result": result}
    finally:
        for p in saved_paths:
            if p.exists(): p.unlink()

@router.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    return rag_service.query(request.message, request.domain)

@router.post("/reset")
async def reset_chat() -> Dict[str, Any]:
    success = rag_service.reset()
    return {"status": "success" if success else "error"}

@router.get("/documents")
async def list_docs() -> Dict[str, List[str]]:
    return {"documents": rag_service.list_documents()}

@router.delete("/documents/{filename}")
async def delete_doc(filename: str) -> Dict[str, str]:
    if not rag_service.delete_document(filename):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "success"}
