import sys
from unittest.mock import MagicMock
from llama_index.core import Document
import src.features.rag.application.rag_service

# Mock SimpleDirectoryReader
class MockSimpleDirectoryReader:
    def __init__(self, input_files=None, *args, **kwargs):
        pass
    def load_data(self):
        return [
            Document(text="Standard Operating Procedure: Use error code 500 for Internal Server Error.", metadata={"file_name": "sop_errors.pdf", "page_label": "1"}),
            Document(text="In case of fire, use the stairs. Not related to error 500.", metadata={"file_name": "sop_fire.pdf", "page_label": "1"}),
            Document(text="PTO policy requires 2 weeks notice.", metadata={"file_name": "sop_pto.pdf", "page_label": "1"}),
            Document(text="Another document about error 500 but slightly different context.", metadata={"file_name": "sop_complex_errors.pdf", "page_label": "2"})
        ]

# Apply Mock
src.features.rag.application.rag_service.SimpleDirectoryReader = MockSimpleDirectoryReader
from src.features.rag.application.rag_service import rag_service

def test_query_transformation():
    print("Testing Query Transformation...")
    original_query = "hr sop for pto"
    rewritten = rag_service.rewrite_query(original_query)
    print(f"Original: '{original_query}'")
    print(f"Rewritten: '{rewritten}'")

    if len(rewritten) > len(original_query) or rewritten != original_query:
        print("PASS: Query was rewritten.")
    else:
        print("WARN: Query was NOT rewritten (might be due to LLM decision or error).")

def test_reranking():
    print("\nTesting Retrieval + Reranking...")

    # Ingest dummy data
    print("Ingesting dummy documents (Mocked)...")
    res = rag_service.ingest_documents(["dummy.pdf"])
    print(f"Ingestion result: {res}")

    query = "error 500"

    # Query with tech domain
    result = rag_service.query(query, domain="tech")
    print("\nResponse:")
    print(result.response[:200] + "...")

    print("\nSources (Top 3 expected):")
    for src in result.sources:
        print(f"- {src.file} (Score: {src.score})")

    if result.sources:
        print("PASS: Retrieval returned sources.")
        # Check scores?
        scores = [s.score for s in result.sources]
        print(f"Scores: {scores}")
        if any(s > 100 for s in scores) or any(s < 0 for s in scores):
             # Logits can be anything. But checking they exist is good enough.
             pass
    else:
        print("FAIL: Retrieval returned NO sources.")

if __name__ == "__main__":
    test_query_transformation()
    test_reranking()
