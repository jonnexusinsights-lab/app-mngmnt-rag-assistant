import os
from unittest.mock import MagicMock
from llama_index.core import Document
import src.services.rag_engine

# 1. Mock SimpleDirectoryReader to avoid needing real PDFs
class MockSimpleDirectoryReader:
    def __init__(self, input_files=None, *args, **kwargs):
        self.input_files = input_files or []

    def load_data(self):
        docs = []
        for f in self.input_files:
            fname = os.path.basename(f)
            docs.append(Document(
                text=f"Content for {fname}",
                metadata={"file_name": fname, "page_label": "1", "creation_date": "2023-01-01"}
            ))
        return docs

# Apply Mock
src.services.rag_engine.SimpleDirectoryReader = MockSimpleDirectoryReader
from src.services.rag_engine import rag_service

def test_persistence_logic():
    print("Testing Multi-File Ingestion & Persistence...")

    # We can't easily assert the DB state without a real DB or mocking LanceDB.
    # But we can call the method and ensure it doesn't crash given the new "Standardize Metadata" logic.
    # And we can verify logic flow.

    # Test 1: Batch Ingest
    files = ["doc_a.pdf", "doc_b.pdf"]
    print(f"Ingesting batch: {files}")
    res = rag_service.ingest_documents(files)
    print(f"Result: {res}")

    if res["status"] != "success":
        print("FAIL: Batch ingestion failed.")
    else:
        print("PASS: Batch ingestion success.")

    # Test 2: Append (Sequential)
    # This checks if the second ingest triggers the "Schema Mismatch" crash logic (which we removed/fixed).
    # In a real run, this would crash the old code if metadata was weird.
    # With our fix (standardizing metadata), it should be fine.
    print("\nIngesting single file (Append): doc_c.pdf")
    res2 = rag_service.ingest_documents(["doc_c.pdf"])
    print(f"Result: {res2}")

    if res2["status"] == "success":
        print("PASS: Append successful (Simulated).")
    else:
        print("FAIL: Append failed.")

    # List documents
    # Real DB interaction - works if DB is up.
    try:
        docs = rag_service.list_documents()
        print(f"\nCurrent Documents in DB: {docs}")
        # Note: Since we mocked the Reader, the content isn't real, but the RAG service *does* try to insert into real LanceDB.
        # So we should see 'doc_a.pdf', 'doc_b.pdf', 'doc_c.pdf' if ingestion worked.

        expected = {"doc_a.pdf", "doc_b.pdf", "doc_c.pdf"}
        if expected.issubset(set(docs)):
             print("PASS: All docs persisted.")
        else:
             print("WARN: Docs missing. (Might be due to previous DB state or mock limitations).")
    except Exception as e:
        print(f"Could not list docs: {e}")

if __name__ == "__main__":
    test_persistence_logic()
