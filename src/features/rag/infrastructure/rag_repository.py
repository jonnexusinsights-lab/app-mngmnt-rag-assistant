import os
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.lancedb import LanceDBVectorStore
from src.core.config import settings
from src.shared.errors.app_errors import VectorDatabaseError, InfrastructureError

class RagRepository:
    def __init__(self):
        self.vector_store = self._initialize_vector_store()
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def _initialize_vector_store(self) -> LanceDBVectorStore:
        try:
            import lancedb
            db = lancedb.connect(settings.LANCEDB_URI)
            table_name = settings.TABLE_NAME

            if table_name in db.table_names():
                table = db.open_table(table_name)
                return LanceDBVectorStore(
                    uri=settings.LANCEDB_URI,
                    table_name=table_name,
                    table=table
                )
            else:
                return LanceDBVectorStore(
                    uri=settings.LANCEDB_URI,
                    table_name=table_name,
                    mode="create"
                )
        except Exception as e:
            raise VectorDatabaseError(f"Failed to initialize LanceDB: {str(e)}") from e

    def get_index(self) -> VectorStoreIndex:
        try:
            return VectorStoreIndex.from_vector_store(vector_store=self.vector_store)
        except Exception as e:
            # If no index exists, return None or raise specific error to be handled by service
            # For now, let's propagate as Infra error
             raise VectorDatabaseError(f"Failed to load index: {str(e)}") from e

    def create_index_from_documents(self, documents) -> VectorStoreIndex:
        return VectorStoreIndex.from_documents(
            documents,
            storage_context=self.storage_context
        )

    def ensure_fts_index(self) -> None:
        """
        Ensure Full Text Search (FTS) index exists for Hybrid Search.
        """
        try:
            import lancedb
            db = lancedb.connect(settings.LANCEDB_URI)
            if settings.TABLE_NAME in db.table_names():
                tbl = db.open_table(settings.TABLE_NAME)
                try:
                    if len(tbl) > 0:
                        tbl.create_fts_index("text", replace=True)
                        print("FTS index verified/created.")
                except Exception as e:
                    print(f"Warning: Could not create FTS index: {e}")
        except Exception as e:
            print(f"Error checking FTS index: {e}")

    def list_documents(self) -> list[str]:
        try:
            import lancedb
            db = lancedb.connect(settings.LANCEDB_URI)
            if settings.TABLE_NAME not in db.table_names():
                return []

            tbl = db.open_table(settings.TABLE_NAME)
            df = tbl.to_pandas()
            files: set[str] = set()

            if "metadata" in df.columns:
                for _, row in df.iterrows():
                    meta = row.get("metadata", {})
                    if isinstance(meta, dict) and "file_name" in meta:
                        files.add(str(meta["file_name"]))

            return sorted(list(files))
        except Exception as e:
            return []

    def delete_document(self, filename: str) -> bool:
        try:
            import lancedb
            db = lancedb.connect(settings.LANCEDB_URI)
            if settings.TABLE_NAME not in db.table_names():
                return False

            tbl = db.open_table(settings.TABLE_NAME)
            safe_filename = filename.replace("'", "''")
            tbl.delete(f"metadata.file_name = '{safe_filename}'")
            return True
        except Exception:
            return False

    def is_healthy(self) -> bool:
        try:
            import lancedb
            lancedb.connect(settings.LANCEDB_URI)
            return True
        except Exception:
            return False
