# Developer Configuration Quickstart

Welcome to the **App Management RAG Assistant** project! This guide will help you set up your local development environment to collaborate on the project.

## 1. Prerequisites

Ensure you have the following installed on your machine:

- **Python 3.13+**: [Download Python](https://www.python.org/downloads/)
- **Ollama**: [Download Ollama](https://ollama.com/download)
  - Verify with `ollama --version`
  - Start the localized server: `ollama serve` (Keep this terminal running)
  - Pull the Llama 3 model: `ollama pull llama3`
- **Git**: [Download Git](https://git-scm.com/downloads)
- **Code Editor**: Antigravity (Recommended) with Python extension.

## 2. Clone the Repository

```bash
git clone https://github.com/jonnexusinsights-lab/app-mngmnt-rag-assistant.git
cd app-mngmnt-rag-assistant
```

## 3. Set Up Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, you should see `(.venv)` in your terminal prompt.

## 4. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## 5. Configuration

The application uses environment variables or default settings defined in `src/core/config.py`.
By default:

- **LLM Model**: `llama3` via Ollama (localhost:11434)
- **Embeddings**: `BAAI/bge-m3` (HuggingFace)
- **Vector DB**: `lancedb` (embedded in `./data`)

No `.env` file is strictly required for the MVP default setup, but you can create one if you need to override settings (e.g., `OLLAMA_BASE_URL`).

## 6. Run the Application

Start the FastAPI backend with hot-reload enabled:

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

## 7. Verify Setup

1.  **Open the Frontend**: Navigate to [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html).
2.  **Run Tests**:
    ```bash
    python test_api.py
    ```

## 8. Collaboration Workflow

- **Branching**: create new branches for features (`git checkout -b feature/my-feature`).
- **Commits**: Write clear commit messages.
- **Pull Requests**: Push your branch and open a PR on GitHub.

Happy Coding!
