from typing import Optional
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings as LlamaSettings
from src.shared.config.app_config import settings
from src.shared.errors.app_errors import LLMServiceError

class LLMClient:
    """
    Client for interacting with LLM (Ollama) and Embedding models.
    """
    def __init__(self) -> None:
        # Initialize Embedding Model (Local)
        self.embed_model = HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL_NAME)
        LlamaSettings.embed_model = self.embed_model

        # Initialize LLM (Ollama)
        try:
            self.llm = Ollama(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.LLM_MODEL,
                request_timeout=300.0
            )
            LlamaSettings.llm = self.llm
        except Exception as e:
            raise LLMServiceError(f"Could not initialize Ollama: {str(e)}") from e

    def get_llm(self) -> Ollama:
        return self.llm

    def get_embed_model(self) -> HuggingFaceEmbedding:
        return self.embed_model
