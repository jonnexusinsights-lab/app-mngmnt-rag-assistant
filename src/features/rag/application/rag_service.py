import os
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings as LlamaSettings
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from sentence_transformers import CrossEncoder
from pydantic import Field, PrivateAttr
from src.core.config import settings
from src.core.prompts import prompt_manager
from src.features.rag.infrastructure.rag_repository import RagRepository
from src.features.rag.api.dtos import (
    IngestionResult,
    SourceNode,
    QueryResult
)
from src.shared.errors.app_errors import (
    LLMServiceError,
    DocumentIngestionError,
    InfrastructureError,
    BaseAppError
)

class CustomReranker(BaseNodePostprocessor):
    top_n: int = Field(default=3)
    _model: CrossEncoder = PrivateAttr()

    def __init__(self, model_name: str, top_n: int = 3):
        super().__init__(top_n=top_n)
        self._model = CrossEncoder(model_name)

    def _postprocess_nodes(self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None) -> list[NodeWithScore]:
        if not nodes:
            return []

        query_str = query_bundle.query_str if query_bundle else ""
        pairs = [[query_str, node.node.get_content()] for node in nodes]
        scores = self._model.predict(pairs)

        for i, node in enumerate(nodes):
            node.score = float(scores[i])

        nodes.sort(key=lambda x: x.score, reverse=True)
        return nodes[:self.top_n]

class RagService:
    repository: RagRepository
    embed_model: HuggingFaceEmbedding
    llm: Ollama
    reranker: CustomReranker
    chat_engine: BaseNodePostprocessor | None
    current_domain: str | None

    def __init__(self):
        self.repository = RagRepository()

        # Initialize Embedding Model
        self.embed_model = HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL_NAME)
        LlamaSettings.embed_model = self.embed_model

        # Initialize LLM
        try:
            self.llm = Ollama(base_url=settings.OLLAMA_BASE_URL, model=settings.LLM_MODEL, request_timeout=300.0)
            LlamaSettings.llm = self.llm
        except Exception as e:
            raise LLMServiceError(f"Could not initialize Ollama: {str(e)}") from e

        # Initialize Reranker using config
        self.reranker = CustomReranker(
            model_name=settings.RERANKER_MODEL,
            top_n=3
        )

        self.chat_engine = None
        self.current_domain = None

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
            self.chat_engine = None
            return IngestionResult(status="success", chunks=len(documents))
        except Exception as e:
            if isinstance(e, BaseAppError): raise e
            raise DocumentIngestionError(f"Ingestion failed: {str(e)}") from e

    def _initialize_chat_engine(self, domain: str):
        try:
            # Reload index via repository
            index = self.repository.get_index()
            self.repository.ensure_fts_index()

            system_prompt = settings.DEFAULT_SYSTEM_PROMPT
            try:
                if domain not in ["hr", "tech"]: domain = "hr"
                system_prompt = prompt_manager.load_prompt(domain, "manager_sop")
            except Exception as e:
                print(f"Warning: Failed to load prompt: {e}")

            retriever = index.as_retriever(
                similarity_top_k=10,
                vector_store_query_mode="hybrid",
                alpha=0.6
            )

            from llama_index.core.chat_engine import ContextChatEngine
            self.chat_engine = ContextChatEngine.from_defaults(
                retriever=retriever,
                node_postprocessors=[self.reranker],
                llm=self.llm,
                system_prompt=system_prompt
            )
            self.current_domain = domain
        except Exception as e:
            raise InfrastructureError(f"Error initializing chat engine: {str(e)}") from e

    def rewrite_query(self, query: str) -> str:
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
            return response.text.strip().replace('"', '')
        except Exception:
            return query

    def query(self, message: str, domain: str = "hr") -> QueryResult:
        try:
            # Check if system has data
            if not self.list_documents():
                 return QueryResult(response="System is not ready. Please upload documents first.", sources=[])

            if self.chat_engine is None or self.current_domain != domain:
                self._initialize_chat_engine(domain)

            if not self.chat_engine:
                 return QueryResult(response="System is not ready. Please upload documents first.", sources=[])

            search_query = self.rewrite_query(message) if len(message.split()) < 10 else message
            response = self.chat_engine.chat(search_query)

            sources: list[SourceNode] = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    meta = node.metadata
                    source_entry = SourceNode(
                        file=meta.get('file_name', 'Unknown'),
                        page=meta.get('page_label', 'N/A'),
                        score=float(node.score)
                    )
                    if source_entry not in sources:
                        sources.append(source_entry)

            return QueryResult(response=str(response), sources=sources)
        except Exception as e:
            if isinstance(e, BaseAppError): raise e
            raise InfrastructureError(f"Error querying RAG: {str(e)}") from e

    def reset(self) -> bool:
        if self.chat_engine:
            self.chat_engine.reset()
            return True
        return False

    def list_documents(self) -> list[str]:
        return self.repository.list_documents()

    def delete_document(self, filename: str) -> bool:
        success = self.repository.delete_document(filename)
        if success: self.chat_engine = None
        return success

    def is_ready(self) -> bool:
        # 1. Check Repository (LanceDB)
        if not self.repository.is_healthy():
            return False
        # 2. Check LLM (Basic instantiation check)
        if not self.llm:
            return False
        return True

rag_service = RagService()
