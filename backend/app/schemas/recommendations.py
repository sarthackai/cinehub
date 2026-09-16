from pydantic import BaseModel


class RecommendationItem(BaseModel):
    content_id: str
    title: str
    poster_url: str | None = None
    final_score: float | None = None
    similarity_score: float | None = None
    explanation: str | None = None


class RecommendationResponse(BaseModel):
    count: int
    results: list[RecommendationItem]


class SimilarContentRequest(BaseModel):
    content_id: str
    top_n: int = 10


class SemanticSearchRequest(BaseModel):
    query: str
    top_n: int = 10