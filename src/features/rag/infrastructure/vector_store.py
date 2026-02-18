import lancedb
from typing import Optional
from llama_index.vector_stores.lancedb import LanceDBVectorStore
from llama_index.core import StorageContext
from src.shared.config.app_config import settings

class VectorStoreManager:
    """
    Manages LanceDB vector store and storage context.
    """
    def __init__(self) -> None:
        self.vector_store = LanceDBVectorStore(
            uri=str(settings.LANCEDB_URI),
            table_name=settings.TABLE_NAME,
            mode="append"
        )
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def get_vector_store(self) -> LanceDBVectorStore:
        return self.vector_store

    def get_storage_context(self) -> StorageContext:
        return self.storage_context

    def ensure_fts_index(self) -> None:
        """
        Ensure Full Text Search (FTS) index exists for Hybrid Search.
        """
        try:
            db = lancedb.connect(str(settings.LANCEDB_URI))
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

    def connect_db(self):
        return lancedb.connect(str(settings.LANCEDB_URI))
