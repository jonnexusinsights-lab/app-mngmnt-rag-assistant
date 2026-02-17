import os
from pathlib import Path
from typing import List, Optional, Any, Dict, Union
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
from src.core.errors import (
    LLMServiceError,
    VectorDatabaseError,
    DocumentIngestionError,
    InfrastructureError,
    BaseAppError
)

class CustomReranker(BaseNodePostprocessor):
    """
    Custom Reranker using sentence-transformers CrossEncoder.
    Avoids need for separate llama-index integration package.
    """
    top_n: int = Field(default=3)
    _model: CrossEncoder = PrivateAttr()

    def __init__(self, model_name: str, top_n: int = 3) -> None:
        super().__init__(top_n=top_n)
        self._model = CrossEncoder(model_name)

    def _postprocess_nodes(self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None) -> List[NodeWithScore]:
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
    embed_model: HuggingFaceEmbedding
    llm: Ollama
    vector_store: LanceDBVectorStore
    storage_context: StorageContext
    reranker: CustomReranker
    chat_engine: Optional[Any] # Specific LlamaIndex types can be complex, Any is safer for top-level engine
    current_domain: Optional[str]

    def __init__(self) -> None:
        # Initialize Embedding Model (Local)
        self.embed_model = HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL_NAME)
        LlamaSettings.embed_model = self.embed_model

        # Initialize LLM (Ollama)
        try:
            self.llm = Ollama(base_url=settings.OLLAMA_BASE_URL, model=settings.LLM_MODEL, request_timeout=300.0)
            LlamaSettings.llm = self.llm
        except Exception as e:
            raise LLMServiceError(f"Could not initialize Ollama: {str(e)}") from e

        # Initialize LanceDB
        self.vector_store = LanceDBVectorStore(
            uri=str(settings.LANCEDB_URI),
            table_name=settings.TABLE_NAME,
            mode="append"
        )
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        # Reranker (Cross-Encoder)
        self.reranker = CustomReranker(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            top_n=3
        )

        # Chat Engine State
        self.chat_engine = None
        self.current_domain = None

    def ingest_documents(self, file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        """
        Ingest a list of documents into the vector store (Append mode).
        Standardizes metadata to prevent schema mismatches and data loss.
        """
        try:
            # 1. Load Data (Convert to strings for SimpleDirectoryReader)
            str_paths = [str(p) for p in file_paths]
            documents = SimpleDirectoryReader(input_files=str_paths).load_data()

            # 2. Standardize Metadata
            for doc in documents:
                # 1. Capture vital info before filtering
                f_path = Path(doc.metadata.get("file_path", str_paths[0]))
                f_name = doc.metadata.get("file_name") or f_path.name
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
                index.insert_nodes(documents)
                print(f"Appended {len(documents)} documents to existing index.")
            except Exception as e:
                # 4. Handle Case: Index/Table doesn't exist yet OR Schema Mismatch
                import lancedb
                db = lancedb.connect(settings.LANCEDB_URI)
                if settings.TABLE_NAME not in db.table_names():
                     # Create fresh
                     VectorStoreIndex.from_documents(
                        documents,
                        storage_context=self.storage_context
                    )
                else:
                    raise VectorDatabaseError(f"Failed to append to existing table: {str(e)}") from e

            # Force FTS re-creation/verification
            self._ensure_fts_index()

            # Reset chat engine to force reload of index with new data
            self.chat_engine = None

            return {"status": "success", "chunks": len(documents)}
        except Exception as e:
            if isinstance(e, BaseAppError):
                raise e
            raise DocumentIngestionError(f"Ingestion failed: {str(e)}") from e

    def _ensure_fts_index(self) -> None:
        """
        Ensure Full Text Search (FTS) index exists for Hybrid Search.
        """
        try:
            import lancedb
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

    def _initialize_chat_engine(self, domain: str) -> None:
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
            raise InfrastructureError(f"Error initializing chat engine: {str(e)}") from e

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

    def query(self, message: str, domain: str = "hr") -> Dict[str, Any]:
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
            if isinstance(e, BaseAppError):
                raise e
            raise InfrastructureError(f"Error querying RAG: {str(e)}") from e

    def reset(self) -> bool:
        """
        Reset the chat history.
        """
        if self.chat_engine:
            self.chat_engine.reset()
            return True
        return False

    def list_documents(self) -> List[str]:
        """
        List all ingested documents by querying LanceDB metadata.
        """
        try:
            import lancedb
            db = lancedb.connect(str(settings.LANCEDB_URI))
            if settings.TABLE_NAME not in db.table_names():
                return []

            tbl = db.open_table(settings.TABLE_NAME)

            try:
                # Flat distinct list of file names
                df = tbl.to_pandas()
                files = set()

                if "metadata" in df.columns:
                    for _, row in df.iterrows():
                        meta = row.get("metadata", {})
                        if isinstance(meta, dict) and "file_name" in meta:
                            files.add(meta["file_name"])
                return sorted(list(files))
            except ImportError:
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

    def delete_document(self, filename: str) -> bool:
        """
        Delete a document from the vector store by filename.
        """
        try:
            import lancedb
            db = lancedb.connect(str(settings.LANCEDB_URI))
            if settings.TABLE_NAME not in db.table_names():
                return False

            tbl = db.open_table(settings.TABLE_NAME)

            # Delete syntax: table.delete("metadata.file_name = 'value'")
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
