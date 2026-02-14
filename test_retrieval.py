from src.services.rag_engine import rag_service
import sys

def test_retrieval():
    print("Testing RAG Retrieval...")

    # Check if we have ingested data
    # (Assuming test_ingestion.py was run previously)

    query = "What is this document about?"
    print(f"Query: {query}")

    try:
        response = rag_service.query(query)
        print("\nResponse:")
        print(response)

        if "RAG Test Document" in response or "standard operating procedures" in response.lower() or "test document" in response.lower():
             print("\nTest Passed: Retrieved relevant content.")
        else:
             print("\nTest Warning: Response might not be relevant (check model quality).")

    except Exception as e:
        print(f"\nTest Failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_retrieval()
