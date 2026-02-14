from src.services.rag_engine import rag_service
import os

def test_ingestion():
    pdf_path = "test_doc.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return

    print(f"Ingesting {pdf_path}...")
    result = rag_service.ingest_document(pdf_path)
    print("Ingestion Result:", result)

    if result.get("status") == "success":
        print("Ingestion Successful!")
    else:
        print("Ingestion Failed.")

if __name__ == "__main__":
    test_ingestion()
