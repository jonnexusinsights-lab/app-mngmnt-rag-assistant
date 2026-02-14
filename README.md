# App Management RAG Assistant

A local, Agentic RAG system for managing Application SOPs, built with the ACE Framework.

> **Developer Setup**: For detailed configuration and initialization steps, see [Developer Configuration Quickstart](dev_configuration_quickstart.md).

## Features

- **Local RAG**: Uses `Ollama` (Llama 3) and HuggingFace Embeddings (`BAAI/bge-m3`).
- **Vector Database**: `LanceDB` for embedded vector storage.
- **Agentic Retrieval**: Uses `LlamaIndex` with custom prompts for domain-specific answers (HR Mode).
- **FastAPI Backend**: Exposes `/ingest` and `/chat` endpoints.
- **Simple Frontend**: Vanilla JS/HTML interface for file upload and chat.

## Prerequisites

1. **Python 3.13** (or compatible).
2. **Ollama**: Must be installed and running (`ollama serve`).
   - Run `ollama pull llama3` to get the required model.
3. **Node.js** (Optional, frontend is served statically by FastAPI).

## Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Start Ollama** (in a separate terminal):
   ```bash
   ollama serve
   ```
2. **Start the Backend Server**:
   ```bash
   uvicorn src.main:app --reload
   ```
3. **Access the Application**:
   - Open your browser to: [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html)

## Usage

1. **Upload Documents**: Use the "Choose File" button to upload PDF SOPs (e.g., `test_doc.pdf`).
2. **Chat**: Ask questions about the uploaded documents. The assistant defaults to "HR Manager" persona for SOP queries.

## Testing

- **API Tests**: `python test_api.py`
- **Ingestion Test**: `python test_ingestion.py`
- **Retrieval Test**: `python test_retrieval.py`
