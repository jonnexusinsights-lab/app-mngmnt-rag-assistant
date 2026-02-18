from src.features.rag.api.dtos import ChatRequest
from pydantic import ValidationError

def test_chat_request_validation_valid():
    req = ChatRequest(message="Hello world", domain="hr")
    assert req.message == "Hello world"
    assert req.domain == "hr"

def test_chat_request_validation_empty_message():
    try:
        ChatRequest(message="", domain="hr")
        raise AssertionError("Should have raised ValidationError")
    except ValidationError:
        pass

def test_chat_request_validation_too_long_message():
    long_msg = "a" * 1001
    try:
        ChatRequest(message=long_msg, domain="hr")
        raise AssertionError("Should have raised ValidationError")
    except ValidationError:
        pass

def test_chat_request_validation_invalid_domain():
    try:
        ChatRequest(message="Hello", domain="marketing")
        raise AssertionError("Should have raised ValidationError")
    except ValidationError:
        pass

def test_chat_request_default_domain():
    req = ChatRequest(message="Hello")
    assert req.domain == "hr"

if __name__ == "__main__":
    try:
        test_chat_request_validation_valid()
        print("test_chat_request_validation_valid: PASS")

        test_chat_request_validation_empty_message()
        print("test_chat_request_validation_empty_message: PASS")

        test_chat_request_validation_too_long_message()
        print("test_chat_request_validation_too_long_message: PASS")

        test_chat_request_validation_invalid_domain()
        print("test_chat_request_validation_invalid_domain: PASS")

        test_chat_request_default_domain()
        print("test_chat_request_default_domain: PASS")

        print("\nAll validation tests passed!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        exit(1)
