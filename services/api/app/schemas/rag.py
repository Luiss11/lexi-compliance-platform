from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str
    document_title: str
    page: int
    clause: str | None = None
    score: float
    excerpt: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class QueryResponse(BaseModel):
    answer: str
    grounded: bool
    best_score: float
    citations: list[Citation] = []
