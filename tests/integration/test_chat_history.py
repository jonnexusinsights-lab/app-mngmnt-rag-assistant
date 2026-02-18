from src.features.rag.application.rag_service import rag_service
import sys

def test_chat_history():
    print("Testing Chat History...")

    # 1. Reset to start clean
    rag_service.reset()

    # 2. Ask a question about the SOP (assuming we have one ingested, or just generic conversation)
    # The default system prompt for "hr" is restrictive, but let's try to simulate context.
    # Note: RAG retrieval might interfere if we ask something not in docs.
    # Let's try to "inject" knowledge via conversation if possible, or rely on the fact that
    # the ChatEngine keeps previous QA pairs.

    print("\n--- Turn 1 ---")
    q1 = "What documents are usually required for travel reimbursement?"
    print(f"User: {q1}")
    r1 = rag_service.query(q1, domain="hr")
    print(f"Agent: {r1.response[:100]}...")

    print("\n--- Turn 2 (Follow-up) ---")
    q2 = "Are receipts mandatory for that?"
    # "that" refers to "travel reimbursement"
    print(f"User: {q2}")
    r2 = rag_service.query(q2, domain="hr")
    print(f"Agent: {r2.response[:100]}...")

    if "reimbursement" in r2.response.lower() or "receipt" in r2.response.lower():
        print("SUCCESS: Context seems to be maintained (Agent understood the context).")
    else:
        print("WARNING: Context might be missed. Check response relevance.")

    print("\n--- Resetting Chat ---")
    rag_service.reset()

    print("\n--- Turn 3 (After Reset) ---")
    q3 = "Are receipts mandatory for that?"
    print(f"User: {q3}")
    r3 = rag_service.query(q3, domain="hr")
    print(f"Agent: {r3.response[:100]}...")

    if "context" in r3.response.lower() or "what" in r3.response.lower() or "clarify" in r3.response.lower():
        print("SUCCESS: Context correctly lost after reset.")
    else:
        print("OBSERVATION: Agent response after reset. (Ideally should ask for clarification or fail to answer specific 'that').")

if __name__ == "__main__":
    test_chat_history()
