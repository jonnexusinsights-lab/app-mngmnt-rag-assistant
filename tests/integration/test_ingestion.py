from src.features.rag.application.rag_service import rag_service
import os

def test_ingestion():
    pdf_path = "test_doc.pdf"
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return

    print(f"Ingesting {pdf_path}...")
    result = rag_service.ingest_documents([pdf_path])
    print("Ingestion Result:", result)

    if result.status == "success":
        print("Ingestion Successful!")
    else:
        print("Ingestion Failed.")

if __name__ == "__main__":
    test_ingestion()
