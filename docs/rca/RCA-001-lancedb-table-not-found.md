# RCA-001: LanceDB Initialization Failure

## Status

**Resolved**

## Incident

**Date:** 2026-02-17
**Component:** `RagRepository` (LanceDB Vector Store)
**Impact:** 500 Internal Server Error on Ingestion and Chat initialization.

## Root Cause

The `LanceDBVectorStore` initialization used `mode="append"`, which is not a valid argument for the installed version of `llama-index-vector-stores-lancedb`.
Additionally, attempting to initialize `ChatEngine` on an empty database caused a crash because no index existed.

## Resolution

1. **Ingestion Fix**: Refactored `_initialize_vector_store` to manually check for table existence using the `lancedb` client.
   - If table exists: Open it and pass to `LanceDBVectorStore`.
   - If not: Initialize with `mode="create"`.
2. **Chat Fix**: Added a guard clause in `RagService.query` to check `list_documents()` before attempting `_initialize_chat_engine`.

## Regression Guard

- **Automated Test**: `tests/unit/test_validation.py` (for input validation).
- **Manual Verification**: `reproduce_ingest.py` and `reproduce_500.py` scripts were used to verify the fixes.
- **Code Pattern**: Ensure `RagRepository` always checks table existence before initialization.
