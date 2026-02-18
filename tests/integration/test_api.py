from fastapi.testclient import TestClient
from src.main import app
import os

client = TestClient(app)

def test_api():
    # Test Health
    response = client.get("/health")
    assert response.status_code == 200
    print("Health Check Passed")

    # Test Ingestion
    pdf_path = "test_doc.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            response = client.post("/ingest", files={"file": ("test_doc.pdf", f, "application/pdf")})
            print("\nIngestion Response:", response.json())
            assert response.status_code == 200

    # Test Chat
    response = client.post("/chat", json={"message": "What is this document about?", "domain": "hr"})
    print("\nChat Response:", response.json())
    assert response.status_code == 200
    assert "response" in response.json()

if __name__ == "__main__":
    test_api()
