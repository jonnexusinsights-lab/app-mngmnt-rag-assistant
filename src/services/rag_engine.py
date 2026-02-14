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

            return {"status": "success", "chunks": len(documents)}
        except Exception as e:
            print(f"Ingestion Error: {e}")
            return {"status": "error", "message": str(e)}

    def query(self, message: str, domain: str = "hr"):
        """
        Query the RAG engine using the Agentic Loop.
        """
        try:
            # Load index from storage
            index = VectorStoreIndex.from_vector_store(vector_store=self.vector_store)

            # Configure Retriever
            retriever = index.as_retriever(similarity_top_k=5)

            # Configure Query Engine
            # Use RetrieverQueryEngine for custom retriever + LLM
            from llama_index.core.query_engine import RetrieverQueryEngine
            from llama_index.core import get_response_synthesizer

            # Configure Response Synthesizer to use Ollama
            response_synthesizer = get_response_synthesizer(
                llm=self.llm,
                streaming=False
            )

            query_engine = RetrieverQueryEngine(
                retriever=retriever,
                response_synthesizer=response_synthesizer
            )

            # Get Prompt Template
            try:
                # Load the appropriate prompt for the domain
                # Default validation to ensure we fallback if needed
                if domain not in ["hr", "tech"]:
                    print(f"Warning: Unknown domain {domain}, defaulting to HR.")
                    domain = "hr"

                prompt_template_str = prompt_manager.load_prompt(domain, "manager_sop")

                # Update Query Engine Prompts
                # LlamaIndex expects specific keys for prompt templates
                from llama_index.core import PromptTemplate
                new_summary_tmpl = PromptTemplate(prompt_template_str)
                query_engine.update_prompts(
                    {"response_synthesizer:text_qa_template": new_summary_tmpl}
                )
            except Exception as e:
                print(f"Warning: Failed to load/apply prompt for domain {domain}: {e}")

            response = query_engine.query(message)

            # Extract sources
            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    # node is NodeWithScore object
                    # metadata is a dict
                    meta = node.metadata
                    file_name = meta.get('file_name', 'Unknown')
                    page_label = meta.get('page_label', 'N/A')
                    score = node.score

                    # Avoid duplicates if multiple chunks from same page
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

# Singleton Instance
rag_service = RAGService()
