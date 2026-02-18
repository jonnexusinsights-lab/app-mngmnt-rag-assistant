from pydantic import BaseModel, Field

class IngestionResult(BaseModel):
    status: str
    chunks: int
    message: str | None = None

class SourceNode(BaseModel):
    file: str
    page: str
    score: float

class QueryResult(BaseModel):
    response: str
    sources: list[SourceNode]

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User query message")
    domain: str = Field(default="hr", pattern="^(hr|tech)$", description="Knowledge domain (hr or tech)")

class GenericResponse(BaseModel):
    status: str
    message: str

class IngestResponse(BaseModel):
    message: str
    total_files: int
    engine_result: IngestionResult

class DocumentListResponse(BaseModel):
    documents: list[str]

class DeleteResponse(BaseModel):
    status: str
    message: str
