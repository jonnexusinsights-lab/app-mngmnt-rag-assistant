# Implementation Plan: App Management RAG Assistant MVP

**Status**: Draft
**Created**: 2026-02-14
**Author**: Architect (Plan)
**Goal**: Build the "Walking Skeleton" - a local Agentic RAG system that ingests PDFs, indexes them using local embeddings, and allows Q&A via a basic web UI.

## User Review Required

> [!IMPORTANT]
> **Hardware Requirement**: Ensure `ollama` is installed and running `llama3`. Ensure Python 3.13.12 is installed.
> **GPU Check**: This plan assumes CUDA availability for HuggingFace embeddings. If CPU-only, ingestion will be slower but functional.

## Tasks

### Task 1: Project Structure & Configuration

- **Objective**: Initialize the project with the agreed folder structure and core configuration.
- **Files**:
  - `src/main.py`
  - `src/core/config.py`
  - `requirements.txt`
  - `src/services/__init__.py`
  - `src/static/index.html`
  - `src/static/app.js`
  - `src/static/style.css`
- **Acceptance Criteria**:
  - Directory structure matches the plan
  - `pip install -r requirements.txt` succeeds
  - Config loads from environment variables or defaults
- **Complexity**: S

### Task 2: RAG Core Engine (Ingestion)

- **Objective**: Implement the PDF ingestion pipeline using LlamaIndex, HuggingFace Embeddings, and LanceDB.
- **Files**:
  - `src/services/rag_engine.py` (Create)
  - `src/core/config.py` (Update)
- **Tests**:
  - Unit test: Transform a sample string to embedding using the local HF model
  - Integration: Ingest a dummy PDF and verify LanceDB table creation
- **Acceptance Criteria**:
  - PDF text is extracted correctly
  - Embeddings are generated locally without API calls
  - Vectors are stored in LanceDB
- **Complexity**: M

### Task 3: Prompt Repository & Management

- **Objective**: Create a system to load and manage versioned prompts for different domains.
- **Files**:
  - `src/core/prompts.py` (Create)
  - `src/prompts/hr/manager_sop.yaml` (Create)
  - `src/prompts/tech/coding_standard.yaml` (Create)
- **Tests**:
  - Unit: Load a prompt template from YAML and format it with variables
  - Unit: Fallback to default prompt if file missing (optional)
- **Acceptance Criteria**:
  - Prompts are loaded from YAML files
  - Different agents can load different prompt sets
- **Complexity**: S

### Task 4: RAG Core Engine (Retrieval & Agent)

- **Objective**: Implement the Agentic Retrieval loop using LlamaIndex.
- **Files**:
  - `src/services/rag_engine.py` (Update)
- **Tests**:
  - Integration: Query the RAG engine and get a response derived from the ingested PDF
- **Acceptance Criteria**:
  - Agent can answer questions based on the ingested PDF
  - Agent cites the source file
- **Complexity**: M

### Task 5: API & Frontend Integration

- **Objective**: Expose RAG functionality via FastAPI and connect the Frontend.
- **Files**:
  - `src/main.py` (Update)
  - `src/static/app.js` (Update)
  - `src/static/index.html` (Update)
- **Tests**:
  - Manual: Upload a PDF via UI and see success message
  - Manual: Chat with the agent via UI and see streaming/final response
- **Acceptance Criteria**:
  - `/ingest` endpoint accepts PDF uploads
  - `/chat` endpoint returns relevant answers
  - UI is responsive and functional per "Design Aesthetics"
- **Complexity**: M

## Verification Plan

### Automated Tests

Run `pytest` (once tests are created) to verify:

1.  **Ingestion Logic**: Ensure embeddings are generated and stored.
2.  **Retrieval Logic**: Ensure query engine returns results.

### Manual Verification

1.  **Start System**: `uvicorn src.main:app --reload`
2.  **Ingest**: Open `http://localhost:8000`, upload a sample SOP PDF.
3.  **Verify Logs**: Check terminal for "Ingestion complete" and LanceDB stats.
4.  **Chat**: Ask a question specific to the SOP.
5.  **Validate**: Confirm the answer is accurate and prompt.
