# Requirements Analysis: SOP Agent for Managers

## Goal Description

Develop a Generative AI RAG agent to function as a Standard Operating Procedure (SOP) support system for managers. The agent will assist with people management, client/stakeholder management, new business, and technical proficiency evaluation across multiple projects and stacks.

**Key capabilities:**

1.  **Agentic RAG**: Learns from "Live" SOP ingested by the web app with minute-level freshness.
2.  **Multi-modal Ingestion**: Handles text, transcripts, podcasts, videos, docs and PDFs.
3.  **Multi-indexing**: Creating and maintaining separate, specialized search indexes for different data types, segments, or search strategies within the same knowledge base.
4.  **Hooping-over**: Agent "hops" between different pieces of information to find an answer that isn't in a single document.
5.  **Self-Correction & Verification**: Avoid the hallucination in the hopping-over strategy.
6.  **Semantic Understanding**: Uses semantic chunking to preserve context (e.g., keeping "Conflict Resolution" as one unit).
7.  **Performance & Reliability**
8.  **Dashboards**: Design a "Technical Observability & Ingestion Dashboard" for the team.

## Functional Requirements

1.  **Interfaces**:
    - **CLI**: For quick admin tasks and testing.
    - **Web App**: Primary interface for managers without login screen, 2 pages, 1 with the ingestion process and the agent chat, the second one with the dashboards.
2.  **Multi-Domain Support**:
    - People Management
    - Client/Stakeholder Management
    - New Business Development
    - Technical Proficiency Evaluation
3.  **Knowledge Base (Agentic RAG)**:
    - **Vector DB**: LanceDB to handle multi-modal/multi-vector data (text, audio, video and image embeddings).
    - **Ingestion Pipeline**: API integrations and ingestion of files exclusive.
    - **Chunking Strategy**: Semantic chunking based on headers and intent.
    - **Multi-modal processing**:Implement Feature Extraction pipelines for non-text assets: Whisper v3 for audio transcription, Vision-LLMs for image-to-text description, and frame-sampling for video summarization. Standardize all multimodal outputs into a unified relational schema within LanceDB to allow cross-media querying.
    - **Multi-indexing**: Deploy a Partitioned Indexing strategy (e.g., separate tables or metadata-filtered indices) for different domains: Technical Stacks, HR/People Management, and Client/SOPs. Utilize Hybrid Search (Keyword + Vector) per index to ensure high precision for specific technical terms and SKU-like identifiers.
    - **Hooping-over**: Implement a Stateful Agentic Loop (via LangGraph) that evaluates if a retrieved context is sufficient; if not, it generates a "follow-up query" to retrieve data from a secondary index. Enable Cross-Reference Reasoning to link high-level management SOPs with specific project technical logs.

## Phase 2: DISCUSS (Finalized Decisions)

### 1. Frontend Technology

- **Decision**: HTML5, Vanilla JS, and CSS served by FastAPI.
- **Rationale**: User confirmed preference for a modern, lightweight web app without heavy frontend frameworks.

### 2. The "Walking Skeleton" (MVP)

- **Decision**: Full end-to-end PDF Ingestion + Agentic Retrieval.
- **Scope**: The MVP will support uploading a PDF, extracting text using local HuggingFace embeddings, indexing in LanceDB, and querying via the Agent.

### 3. Hardware & Local Inference

- **Decision**: Local CPU/GPU with Ollama (Llama 3).
- **Embeddings**: HuggingFace models running locally (CPU/GPU) to avoid API limits and ensure speed.

### 4. Python Environment

- **Decision**: Python 3.13.12.

4.  **Self-Correction & Verification**:
    - **Verification Layer**: After retrieving data, the agent must perform a "Self-Correction" pass. It should ask itself: "Does this SOP snippet actually answer the user's specific question about Python deployment?"
    - **Fact-Checking**: The agent should cite the specific source and timestamp (especially for podcasts/videos) for every claim it makes.
5.  **Performance & Reliability**:
    - **Cold-Start & Latency**: Since managers use this for "Live" support, define an acceptable Time-to-First-Token (TTFT). If Ollama is too slow on your local hardware, you need a strategy for Model Quantization or a cloud-fallback.
    - **Cache Strategy**: Implement Semantic Caching. If two managers ask similar questions about a common SOP, the system should serve the previous answer instead of re-running the expensive Agentic RAG loop.
6.  **Dashboard**:
    - **Ingestion Tracking**: Log every "Manager Action" suggestion (LangSmith / Arize Phoenix).
    - **RAG Health**: Propose a UI view for "RAGAS" metrics (Faithfulness, Answer Relevancy, and Context Precision).
    - **LanceDB Monitoring**: Suggest metrics for tracking vector search latency and "Stale Document" flags.
7.  **Terminal Log Tracking (ETL & Observability)**:
    - **Chunking (Log-Specific)**: Implement Time-Window Chunking mixed with Level-Aware Splitting (Error, Warn, Info). Ensure stack traces are kept as single atomic units to prevent losing the context of a crash.
    - **Ingestion**: Develop a Streaming Listener (via WebSockets or tailing logic) to capture live terminal output and system logs. Support for Batch Uploads of historical log files (.log, .txt, .json) for post-mortem analysis.
    - **Embedding**: Utilize Code-Specific Embedding Models (like text-embedding-3-small or jina-embeddings-v2-code) that understand the syntax and semantics of log patterns and error codes.
    - **Storing**: Use LanceDB’s Columnar Storage to keep raw log text alongside vectors for fast retrieval during debugging. Apply TTL (Time-To-Live) policies on log data to automatically purge or archive old logs to keep the "Brain" lean.
    - **Querying**: Implement Natural Language to Log-Query translation (Text-to-SQL or Text-to-Filter). Enable Anomaly Correlation: Allow managers to ask, "Did this error happen during the last SOP update?" by querying across the Log Index and the SOP Index.
8.  **LLM**: Ollama (Llama 3).

## Proposed Architecture Logic

- **Framework**: Python 3.13.12 + LlamaIndex (for superior hierarchical data handling).
- **Frontend**: Web App (Framework uvicorn+python) + CLI.
- **Backend API**: Python (FastAPI/Flask) to expose agent capabilities.
- **RAG Engine**:
  - **Orchestrator**: LlamaIndex workflows for routing (e.g., "Technical Eval" vs "HR Issue").
  - **Storage**: LanceDB embedded database.
  - **Middleware**:
- **LLM Interface**: Ollama (Llama 3).

## Next Steps

1.  Formalize architecture in `docs/planning/implementation_plan.md`.
2.  Create `ADR-002` for the Tech Stack.
3.  Set up the development environment.
