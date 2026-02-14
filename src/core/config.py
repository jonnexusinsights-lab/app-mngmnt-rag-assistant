import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "App Management RAG Assistant"
    APP_VERSION: str = "0.1.0"

    # LLM Settings (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3"

    # Embedding Settings (HuggingFace)
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"  # Local robust model

    # Database Settings
    LANCEDB_URI: str = "data/lancedb"
    TABLE_NAME: str = "sop_docs"

    # Prompt Repository
    PROMPT_DIR: str = "src/prompts"

    class Config:
        env_file = ".env"

settings = Settings()
