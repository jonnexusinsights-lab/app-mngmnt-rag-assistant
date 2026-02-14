from src.services.rag_engine import rag_service
import sys

def test_citations():
    print("Testing Source Citations...")

    # Query something liable to bring up the test doc
    query = "What is the standard operating procedure?"

    try:
        result = rag_service.query(query, domain="hr")
        # result should be a dict

        if not isinstance(result, dict):
            print(f"FAILED: Result is not a dict. Got {type(result)}")
            return

        print("Response Keys:", result.keys())

        response_text = result.get("response", "")
        sources = result.get("sources", [])

        print("\nResponse Preview:", response_text[:100] + "...")
        print(f"\nNumber of Sources: {len(sources)}")

        if len(sources) > 0:
            print("First Source:", sources[0])
            if "file" in sources[0] and "page" in sources[0]:
                print("SUCCESS: Sources contain file and page metadata.")
            else:
                print("FAILED: Sources missing required metadata fields.")
        else:
            print("WARNING: No sources returned. (This might be expected if no relevance or LLM didn't use context, but usually it should found something for generic query).")

    except Exception as e:
        print(f"FAILED with error: {e}")

if __name__ == "__main__":
    test_citations()
