import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.lancedb import LanceDBVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings as LlamaSettings
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from sentence_transformers import CrossEncoder
from pydantic import Field, PrivateAttr
from src.core.config import settings
from src.core.prompts import prompt_manager

class CustomReranker(BaseNodePostprocessor):
    """
    Custom Reranker using sentence-transformers CrossEncoder.
    Avoids need for separate llama-index integration package.
    """
    top_n: int = Field(default=3)
    _model: CrossEncoder = PrivateAttr()

    def __init__(self, model_name: str, top_n: int = 3):
        super().__init__(top_n=top_n)
        self._model = CrossEncoder(model_name)

    def _postprocess_nodes(self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None) -> list[NodeWithScore]:
        if not nodes:
            return []

        query_str = query_bundle.query_str if query_bundle else ""

        # Prepare pairs for Cross-Encoder
        # (query, document_text)
        pairs = [[query_str, node.node.get_content()] for node in nodes]

        # Get scores
        scores = self._model.predict(pairs)

        # Update scores and sort
        for i, node in enumerate(nodes):
            node.score = float(scores[i])

        # Sort by score descending
        nodes.sort(key=lambda x: x.score, reverse=True)

        return nodes[:self.top_n]

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
        # mode="append" ensures we don't wipe the table on initialization/connection
        # However, if table doesn't exist, it should create it.
        self.vector_store = LanceDBVectorStore(
            uri=settings.LANCEDB_URI,
            table_name=settings.TABLE_NAME,
            mode="append"
        )
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        # Reranker (Cross-Encoder)
        # Use a lightweight but effective model
        self.reranker = CustomReranker(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            top_n=3 # Rerank top-k (5) -> top-n (3)
        )

        # Chat Engine State
        self.chat_engine = None
        self.current_domain = None

    def ingest_documents(self, file_paths: list[str]):
        """
        Ingest a list of documents into the vector store (Append mode).
        Standardizes metadata to prevent schema mismatches and data loss.
        """
        try:
            # 1. Load Data
            documents = SimpleDirectoryReader(input_files=file_paths).load_data()

            # 2. Standardize Metadata (Crucial to prevent schema errors)
            # LanceDB is strict about schema. If a new doc has numeric 'page_label'
            # and old docs had string, or missing keys, it might fail.
            # 2. Standardize Metadata (Crucial to prevent schema errors)
            # LanceDB is strict. Table only has 'file_name', 'page_label'.
            # SimpleDirectoryReader adds 'file_path', 'creation_date', etc. which causes mismatch.
            allowed_keys = ["file_name", "page_label"]
            for doc in documents:
                # 1. Capture vital info before filtering
                f_name = doc.metadata.get("file_name") or os.path.basename(doc.metadata.get("file_path", file_paths[0]))
                p_label = doc.metadata.get("page_label", "1")

                # 2. Replace metadata with ONLY allowed keys
                doc.metadata = {
                    "file_name": str(f_name),
                    "page_label": str(p_label)
                }

            # 3. Try to load existing index and insert
            try:
                # Load index from storage
                index = VectorStoreIndex.from_vector_store(vector_store=self.vector_store)

                # Check if table exists (via simple query or checking tables) to avoid 'Table not found' on insert
                # LanceDBVectorStore handles this usually, but let's be safe.

                index.insert_nodes(documents) # Insert as nodes/documents

                # Debug: Check table size
                import lancedb
                _db = lancedb.connect(settings.LANCEDB_URI)
                if settings.TABLE_NAME in _db.table_names():
                    _tbl = _db.open_table(settings.TABLE_NAME)
                    print(f"Debug: Table size after insert: {len(_tbl)}")

                print(f"Appended {len(documents)} documents to existing index.")
            except Exception as e:
                # 4. Handle Case: Index/Table doesn't exist yet OR Schema Mismatch (Recoverable)
                print(f"Insert failed/Index not found ({e}). Attempting to create new index (Merging schema if possible)...")

                # If it's a schema mismatch, LanceDB might throw.
                # In a production "Append" scenario, we shouldn't drop the table unless explicitly requested.
                # But for this MVP, if the table exists and is incompatible, we previously dropped it.
                # To FIX DATA LOSS: We will try to merge or ignore, but if we MUST drop, we should warn.
                # For now, let's assume 'Standardized Metadata' fixes 90% of issues.
                # If it fails, we fall back to creating from scratch ONLY if table is missing.

                import lancedb
                db = lancedb.connect(settings.LANCEDB_URI)
                if settings.TABLE_NAME not in db.table_names():
                     # Create fresh
                     index = VectorStoreIndex.from_documents(
                        documents,
                        storage_context=self.storage_context
                    )
                else:
                    # Table exists but insert failed.
                    # It could be a true schema conflict.
                    # We will log error but NOT DROP TABLE automatically to preserve data.
                    print("CRITICAL: Failed to append to existing table. Schema mismatch likely.")
                    print("To fix: Standardize your document metadata or manually reset the DB if this is a fresh start.")
                    # For MVP "Auto-fix" behavior (User requested "Context" capability implies adding to it, not replacing):
                    # We re-raise to alert the user, rather than silently wiping data.
                    # OR we could try to coerce schema.
                    raise e

            # Force FTS re-creation/verification
            self._ensure_fts_index()

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
                        # Use replace=True to rebuild the FTS index for new documents
                        tbl.create_fts_index("text", replace=True)
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
                similarity_top_k=10, # Fetch more candidates (10) for reranking
                vector_store_query_mode="hybrid", # Enable Hybrid in LanceDB
                alpha=0.6 # Weight for Semantic (0.6) vs Keyword (0.4)
            )

            from llama_index.core.chat_engine import ContextChatEngine
            self.chat_engine = ContextChatEngine.from_defaults(
                retriever=retriever,
                node_postprocessors=[self.reranker], # Apply Reranking
                llm=self.llm,
                system_prompt=system_prompt
            )
            self.current_domain = domain
            print(f"Chat Engine initialized for domain: {domain} (Hybrid Search + Reranking Enabled)")

        except Exception as e:
            print(f"Error initializing chat engine: {e}")
            raise e

    def rewrite_query(self, query: str) -> str:
        """
        Rewrite the user query to better match document content (Query Transformation).
        """
        prompt = (
            f"Please rewrite the following query to improve its clarity and matching potential "
            f"for a retrieval system containing Standard Operating Procedures (SOPs). "
            f"Expand any common acronyms if possible. "
            f"Return ONLY the rewritten query, nothing else.\n\n"
            f"Original Query: {query}\n"
            f"Rewritten Query:"
        )
        try:
            response = self.llm.complete(prompt)
            rewritten = response.text.strip().replace('"', '')
            print(f"Query Transformation: '{query}' -> '{rewritten}'")
            return rewritten
        except Exception as e:
            print(f"Query rewrite failed: {e}")
            return query

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

            # 1. Query Transformation
            # usage: We can optionally rewrite. For ChatEngine context mode,
            # modifying the input message might confuse the history,
            # BUT efficient RAG often transforms the query *for retrieval* while keeping the original for chat.
            # LlamaIndex ContextChatEngine doesn't easily separate "retrieval query" vs "chat message" without custom logic.
            # For this MVP, we will simpler pass the rewritten query as the message,
            # explaining to the user if needed, OR just use it silently.
            # Let's try silent rewriting for better accuracy.

            # Simple heuristic: Only rewrite if query is short or looks like a keyword search
            if len(message.split()) < 10:
                search_query = self.rewrite_query(message)
            else:
                search_query = message

            # Query (Chat)
            # We pass the POTENTIALLY rewritten query.
            # Note: This means the chat history will record the REWRITTEN query.
            response = self.chat_engine.chat(search_query)

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
