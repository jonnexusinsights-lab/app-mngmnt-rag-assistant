# ADR-002: Technology Stack Selection

## Status

Accepted

## Date

2026-02-14

## Context

We need to select the technology stack for the `app-mngmnt-rag-assistant` project. The system requires a RAG (Retrieval-Augmented Generation) pipeline, a user interface for managers, and must run locally with potential for GPU acceleration.

## Decision

We will use the following stack:

- **Language**: Python 3.13.12
- **Backend API**: FastAPI (served via Uvicorn)
- **Frontend**: HTML5, Vanilla JS, CSS (served as static files by FastAPI or separate service)
- **LLM Runtime**: Ollama (running Llama 3 locally)
- **Embeddings**: HuggingFace (running locally on CPU/GPU)
- **Vector Database**: LanceDB (embedded, multimodal support)
- **Orchestrator**: LlamaIndex
- **Prompt Management**: YAML/JSON based repository (versioned in git)

## Consequences

### Positive

- **Performance**: FastAPI ensuring high performance. Vanilla JS ensures a lightweight frontend.
- **Privacy & Cost**: All inference (LLM + Embeddings) is local, incurring no API costs and keeping data private.
- **Simplicity**: Python-centric stack (except for minimal JS) reduces context switching.
- **Future-Proofing**: LanceDB supports multi-modal data (images, video) for future requirements.

### Negative

- **Local Resource Usage**: Running LLM and Embeddings locally requires significant RAM/VRAM.
- **Frontend Complexity**: Vanilla JS requires more boilerplate for state management compared to frameworks like React/Vue, but for this scope, it keeps dependencies low.

## Compliance

- All Python code must be compatible with 3.13.12.
- Docker containers (if used) must comply with local GPU passthrough requirements.
