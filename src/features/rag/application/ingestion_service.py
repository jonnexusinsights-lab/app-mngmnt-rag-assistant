import os
from llama_index.core import SimpleDirectoryReader
from src.features.rag.infrastructure.rag_repository import RagRepository
from src.features.rag.api.dtos import IngestionResult
from src.shared.errors.app_errors import (
    DocumentIngestionError,
    BaseAppError
)

class IngestionService:
    repository: RagRepository

    def __init__(self):
        self.repository = RagRepository()

    def ingest_documents(self, file_paths: list[str]) -> IngestionResult:
        try:
            documents = SimpleDirectoryReader(input_files=file_paths).load_data()

            for doc in documents:
                f_name = doc.metadata.get("file_name") or os.path.basename(doc.metadata.get("file_path", file_paths[0]))
                p_label = doc.metadata.get("page_label", "1")
                doc.metadata = {"file_name": str(f_name), "page_label": str(p_label)}

            try:
                # Try appending to existing index
                index = self.repository.get_index()
                index.insert_nodes(documents)
            except Exception:
                # Create new index if fails
                self.repository.create_index_from_documents(documents)

            self.repository.ensure_fts_index()
            # Note: We don't reset chat engine here explicitly because they are now decoupled.
            # RetrievalService might need a way to know index is updated, or it just reloads on next query.
            return IngestionResult(status="success", chunks=len(documents))
        except Exception as e:
            if isinstance(e, BaseAppError): raise e
            raise DocumentIngestionError(f"Ingestion failed: {str(e)}") from e

    def list_documents(self) -> list[str]:
        return self.repository.list_documents()

    def delete_document(self, filename: str) -> bool:
        return self.repository.delete_document(filename)

    def is_healthy(self) -> bool:
        return self.repository.is_healthy()

ingestion_service = IngestionService()
