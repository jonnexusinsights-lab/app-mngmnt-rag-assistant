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

    def _initialize_chat_engine(self, domain: str):
        """
        Initialize the ContextChatEngine with specific domain prompts.
        """
        try:
            # Load index from storage
            index = VectorStoreIndex.from_vector_store(vector_store=self.vector_store)

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

            # Initialize Chat Engine (Context Mode)
            # chat_mode='context' retrieves context from index and puts it in system message
            self.chat_engine = index.as_chat_engine(
                chat_mode="context",
                llm=self.llm,
                system_prompt=system_prompt,
                similarity_top_k=5
            )
            self.current_domain = domain
            print(f"Chat Engine initialized for domain: {domain}")

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

# Singleton Instance
rag_service = RAGService()
