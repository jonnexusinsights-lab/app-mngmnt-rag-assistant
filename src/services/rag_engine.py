import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.lancedb import LanceDBVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings as LlamaSettings
from src.core.config import settings
from src.core.prompts import prompt_manager

class RAGService:
    def __init__(self):
        # Initialize Embedding Model (Local)
        # This might take time to download on first run
        self.embed_model = HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL_NAME)
        LlamaSettings.embed_model = self.embed_model

        # Initialize LLM (Ollama)
        try:
            self.llm = Ollama(base_url=settings.OLLAMA_BASE_URL, model=settings.LLM_MODEL, request_timeout=300.0)
            LlamaSettings.llm = self.llm
        except Exception as e:
            print(f"Critical Error: Could not initialize Ollama: {e}")
            raise e

        # Initialize LanceDB
        self.vector_store = LanceDBVectorStore(
            uri=settings.LANCEDB_URI,
            table_name=settings.TABLE_NAME
        )
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        # Chat Engine State
        self.chat_engine = None
        self.current_domain = None

    def ingest_document(self, file_path: str):
        """
        Ingest a document into the vector store (Append mode).
        """
        try:
            documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

            # Try to load existing index and insert
            try:
                # Load index from storage
                index = VectorStoreIndex.from_vector_store(vector_store=self.vector_store)
                for doc in documents:
                    index.insert(doc)
                print(f"Appended {len(documents)} documents to existing index.")
            except Exception as e:
                # Check for specific LanceDB schema mismatch error
                error_msg = str(e).lower()
                if "schema" in error_msg and "not found" in error_msg:
                    print("Schema mismatch detected. Resetting table to strictly enforce new schema (development mode behavior).")

                    # Drop the table to allow recreation
                    import lancedb
                    import time
                    db = lancedb.connect(settings.LANCEDB_URI)
                    if settings.TABLE_NAME in db.table_names():
                        try:
                            db.drop_table(settings.TABLE_NAME)
                            print(f"Dropped table '{settings.TABLE_NAME}'.")
                        except Exception as drop_err:
                            print(f"Error dropping table: {drop_err}")

                    # Wait briefly for FS release
                    time.sleep(1.0)

                    # CRITICAL: Re-initialize the vector/storage context to clear stale schema caches
                    self.vector_store = LanceDBVectorStore(
                        uri=settings.LANCEDB_URI,
                        table_name=settings.TABLE_NAME
                    )
                    self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

                    # Re-create Index
                    # LanceDBVectorStore should now create a new table with inferred schema
                    index = VectorStoreIndex.from_documents(
                        documents,
                        storage_context=self.storage_context
                    )

                    # Force FTS re-creation since we dropped the table
                    self._ensure_fts_index()

                    # Re-create Index
                    index = VectorStoreIndex.from_documents(
                        documents,
                        storage_context=self.storage_context
                    )
                else:
                    print(f"Index not found or load failed ({e}), creating new index.")
                    # Create Index (ingests into LanceDB)
                    index = VectorStoreIndex.from_documents(
                        documents,
                        storage_context=self.storage_context
                    )

            # Reset chat engine to force reload of index with new data
            self.chat_engine = None

            return {"status": "success", "chunks": len(documents)}
        except Exception as e:
            print(f"Ingestion Error: {e}")
            return {"status": "error", "message": str(e)}

    def _ensure_fts_index(self):
        """
        Ensure Full Text Search (FTS) index exists for Hybrid Search.
        """
        try:
            import lancedb
            db = lancedb.connect(settings.LANCEDB_URI)
            if settings.TABLE_NAME in db.table_names():
                tbl = db.open_table(settings.TABLE_NAME)
                try:
                    # Create FTS index on the 'text' field (LlamaIndex default content field)
                    # replace=False means it won't rebuild if exists (LanceDB handles this)
                    # Note: FTS creation might fail if table is empty
                    if len(tbl) > 0:
                        tbl.create_fts_index("text", replace=False)
                        print("FTS index verified/created.")
                except Exception as e:
                    print(f"Warning: Could not create FTS index (Table might be empty or locked): {e}")
        except Exception as e:
            print(f"Error checking FTS index: {e}")

    def _initialize_chat_engine(self, domain: str):
        """
        Initialize the ContextChatEngine with specific domain prompts.
        """
        try:
            # Load index from storage
            index = VectorStoreIndex.from_vector_store(vector_store=self.vector_store)

            # Ensure FTS availability for Hybrid Search
            self._ensure_fts_index()

            # Determine system prompt based on domain
            system_prompt = "You are a helpful AI assistant."
            try:
                if domain not in ["hr", "tech"]:
                    domain = "hr"

                # We simply use the 'template' from yaml as the system prompt
                # (adjusting slightly for ChatEngine context calls)
                prompt_content = prompt_manager.load_prompt(domain, "manager_sop")

                # Extract the persona part or use the whole thing as system prompt
                # For ContextChatEngine, we can pass system_prompt which frames the bot
                system_prompt = prompt_content
            except Exception as e:
                print(f"Warning: Failed to load prompt: {e}")

            # Initialize Chat Engine (Context Mode) with Hybrid Search
            # We construct it manually to pass retriever args

            # Hybrid Retriever: combines Vector Search + Keyword Search (FTS)
            retriever = index.as_retriever(
                similarity_top_k=5,
                vector_store_query_mode="hybrid", # Enable Hybrid in LanceDB
                alpha=0.6 # Weight for Semantic (0.6) vs Keyword (0.4)
            )

            from llama_index.core.chat_engine import ContextChatEngine
            self.chat_engine = ContextChatEngine.from_defaults(
                retriever=retriever,
                llm=self.llm,
                system_prompt=system_prompt
            )
            self.current_domain = domain
            print(f"Chat Engine initialized for domain: {domain} (Hybrid Search Enabled)")

        except Exception as e:
            print(f"Error initializing chat engine: {e}")
            raise e

    def query(self, message: str, domain: str = "hr"):
        """
        Chat with the RAG engine (Stateful).
        """
        try:
            # Initialize or Re-initialize if domain changed or not set
            if self.chat_engine is None or self.current_domain != domain:
                self._initialize_chat_engine(domain)

            if not self.chat_engine:
                return {"response": "System is not ready (Index not found?). Upload a document first.", "sources": []}

            # Query (Chat)
            response = self.chat_engine.chat(message)

            # Extract sources
            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    meta = node.metadata
                    file_name = meta.get('file_name', 'Unknown')
                    page_label = meta.get('page_label', 'N/A')
                    score = node.score

                    source_entry = {
                        "file": file_name,
                        "page": page_label,
                        "score": score
                    }
                    if source_entry not in sources:
                        sources.append(source_entry)

            return {
                "response": str(response),
                "sources": sources
            }
        except Exception as e:
            return {
                "response": f"Error querying RAG: {str(e)}",
                "sources": []
            }

    def reset(self):
        """
        Reset the chat history.
        """
        if self.chat_engine:
            self.chat_engine.reset()
            return True
        return False

    def list_documents(self):
        """
        List all ingested documents by querying LanceDB metadata.
        """
        try:
            import lancedb
            db = lancedb.connect(settings.LANCEDB_URI)
            if settings.TABLE_NAME not in db.table_names():
                return []

            tbl = db.open_table(settings.TABLE_NAME)

            # Fetch all rows, but only metadata column.
            # Note: For large datasets this is inefficient (O(N)), but fine for MVP.
            # LanceDB doesn't support 'DISTINCT' queries directly yet via simple API.
            try:
                # Try pandas if available for ease
                # Some versions of lancedb.to_pandas() do not accept 'columns' or 'flatten' args
                df = tbl.to_pandas()
                files = set()

                # Check if 'metadata' column exists
                if "metadata" in df.columns:
                    for _, row in df.iterrows():
                        meta = row.get("metadata", {})
                        # Metadata might be a dict or a string depending on ingestion
                        if isinstance(meta, dict) and "file_name" in meta:
                            files.add(meta["file_name"])
                return sorted(list(files))
            except ImportError:
                # Fallback to Arrow if pandas is missing
                arrow_tbl = tbl.to_arrow()
                files = set()
                if "metadata" in arrow_tbl.column_names:
                    metadata_col = arrow_tbl["metadata"]
                    for i in range(len(metadata_col)):
                        meta = metadata_col[i].as_py()
                        if isinstance(meta, dict) and "file_name" in meta:
                            files.add(meta["file_name"])
                return sorted(list(files))

        except Exception as e:
            print(f"Error listing documents: {e}")
            return []

    def delete_document(self, filename: str):
        """
        Delete a document from the vector store by filename.
        """
        try:
            import lancedb
            db = lancedb.connect(settings.LANCEDB_URI)
            if settings.TABLE_NAME not in db.table_names():
                return False

            tbl = db.open_table(settings.TABLE_NAME)

            # Delete syntax: table.delete("metadata.file_name = 'value'")
            # Escape filename just in case
            safe_filename = filename.replace("'", "''")
            tbl.delete(f"metadata.file_name = '{safe_filename}'")

            # Reset chat engine to ensure no stale context
            self.chat_engine = None
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

# Singleton Instance
rag_service = RAGService()
