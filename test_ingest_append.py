from src.services.rag_engine import rag_service
import os

def test_ingest_append():
    print("Testing Ingestion Append...")

    # We will assume test_doc.pdf is already ingested or we ingest it first.
    # Let's create a temporary dummy PDF or text file logic?
    # SimpleDirectoryReader content is easiest.

    # Actually, let's just create a dummy file
    dummy_file = "temp_test_append.txt"
    with open(dummy_file, "w") as f:
        f.write("This is a NEW appended document for testing purposes. It contains unique keyword: ZEBRA123.")

    try:
        print("Ingesting new document...")
        result = rag_service.ingest_document(dummy_file)
        print("Ingestion Result:", result)

        print("Querying for new keyword...")
        response = rag_service.query("What does the ZEBRA123 document say?")
        print("Query Response:", response)

        if "ZEBRA123" in str(response) or "new appended document" in str(response).lower():
            print("SUCCESS: Found new document content.")
        else:
            print("WARNING: Did not find specific content (might be summarization issue or index overwrite).")

    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

if __name__ == "__main__":
    test_ingest_append()
