# ADR-003: RAG Architecture - Local Agentic System

## Status

Accepted

## Date

2026-02-14

## Context

We are building a "SOP Agent for Managers" that requires high-quality retrieval and synthesis of documents (PDFs, Markdown) related to people management and technical procedures. The system must run entirely locally, support future multi-modal ingestion, and use an agentic approach for "hopping" between SOPs.

## Decision

We will implement the following RAG architecture:

### 1. Ingestion Pipeline

- **Framework**: LlamaIndex `IngestionPipeline`.
- **Parser**: `LlamaParse` (or robust local PDF parsers like `pymupdf` if LlamaParse is cloud-dependent). _Optimization_: Use `PyMuPDF` for local-only reliability.
- **Chunking**: Semantic Chunking (using LlamaIndex `SemanticSplitterNodeParser`) to preserve context.
- **Embeddings**: HuggingFace local models (e.g., `BAAI/bge-m3` or `nomic-embed-text-v1.5`) running on CPU/GPU.

### 2. Storage

- **Vector Store**: LanceDB (embedded).
- **Schema**: Single table with metadata columns for `doc_type` (SOP, HR, Tech), `timestamp`, and `source_id`.

### 3. Retrieval & Generation

- **LLM**: Ollama running Llama 3 (8B or 70B depending on hardware).
- **Agent Framework**: LlamaIndex Agent (ReAct or OpenAI-like agent if supported by Ollama model).
- **Pattern**: "Agentic RAG" where the LLM can formulate search queries, critique results, and issue follow-up queries ("Hooping-over").
- **Prompt Engineering**:
  - **Storage**: `src/prompts/<domain>/<template>.yaml`.
  - **Loading**: Dynamic loading at runtime based on the active domain (HR, Tech, etc.).
  - **Versioning**: Git-based.

## Consequences

### Positive

- **Data Privacy**: No data leaves the local machine.
- **Cost**: Zero inference cost.
- **Flexibility**: LanceDB allows easy migration to multi-modal data later.
- **Accuracy**: Agentic loop allows self-correction before answering.

### Negative

- **Latency**: Agentic loops (reasoning + multiple retrieval steps) are slower than naive RAG.
- **Hardware Dependency**: Token generation speed depends entirely on local hardware.

## Compliance

- Maintain separation of concerns: Ingestion service vs. Query service.
- Ensure embedding model dimension matches LanceDB schema.
