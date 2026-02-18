# Active Context: Project Handoff

## Session Metadata

- **Last Updated:** 2026-02-17
- **Active Role:** Architect / Developer
- **Mode:** HANDOFF

## Accomplished

- **Environment Setup**: Python 3.13, uvicorn, and ACE-Framework initialized.
- **RAG Core Engine**:
  - Integrated LlamaIndex with local HuggingFace embeddings (`BAAI/bge-small-en-v1.5`).
  - Implemented LanceDB vector storage with metadata standardization to prevent schema mismatches.
  - Added Hybrid Search (Vector + FTS) and Reranking (`ms-marco-MiniLM-L-6-v2`).
  - Implemented Query Transformation (silent rewrite) for better retrieval accuracy.
- **FastAPI Backend**:
  - Created endpoints for `/ingest` (multi-file), `/chat` (stateful/domain-specific), `/documents` (list/delete), and `/reset`.
  - Fixed uvicorn startup issues and command typos.
- **Frontend**: Basic web UI for document management and chat interaction at `/static`.
- **Git Sync**: Local `main` branch fully synchronized with `origin/main` (pulled 15 commits).

## Current State of Components

- **FastAPI App (`src/main.py`)**: Fully functional. Handles multi-file ingestion, chat, and document management.
- **RAG Core**: Split into `IngestionService` and `RetrievalService` (LlamaIndex + LanceDB).
- **Storage**: LanceDB local storage at `./storage/lancedb`. Metadata standardized to `file_name` and `page_label`.
- **Configuration**: Centralized in `src/core/config.py`.

## Pending Decisions

- **Domain Expansion**: Currently supports `hr` and `tech`. New domains require YAML prompts in `src/prompts/`.
- **LLM Selection**: Currently hardcoded to Ollama `llama3`. Evaluation of `llama3.1` or `mistral` pending.

## Known Issues

- **FTS Warm-up**: FTS index creation might fail silently if the table is empty during initialization; it auto-verifies on first ingestion.
- **Deployment**: Local-only configuration for now. Needs containerization for cloud deployment.
- **Error Handling**: Batch ingestion logs errors but continues processing; partial success is possible.

## Recommended Next Steps

1. [ ] **Prompt Engineering**: Refine `manager_sop.yaml` and `coding_standard.yaml` based on user feedback.
2. [ ] **Evaluation Cluster**: Set up a basic evaluation script to measure RAG accuracy.
3. [ ] **UI Polish**: Enhance the `/static` frontend with better streaming feedback and source visualization.
4. [ ] **Containerization**: Create a `Dockerfile` for easy deployment and replication.
5. [ ] **Testing**: Increase coverage for `rag_engine` edge cases (e.g., malformed PDFs).

## Active Constraints

- Local-first architecture (Ollama + local embeddings).
- LanceDB schema strictness requires metadata standardization.

## Session Notes

- Framework initialized via create-ace-framework CLI
- Refactored error handling to typed hierarchy in `refactor/error-handling` branch.
- Successfully pushed branch to GitHub: [refactor/error-handling](https://github.com/jonnexusinsights-lab/app-mngmnt-rag-assistant/tree/refactor/error-handling)
