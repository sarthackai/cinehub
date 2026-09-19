from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user_id
from app.ml.model_registry import get_model
from app.schemas.recommendations import (
    RecommendationResponse,
    RecommendationItem,
    SimilarContentRequest,
    SemanticSearchRequest,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/user", response_model=RecommendationResponse)
def get_user_recommendations(
    top_n: int = 10,
    content_type: str | None = None,
    user_id: str = Depends(get_current_user_id),
):
    """Personalized hybrid recommendations for the logged-in user."""
    model = get_model()
    results = model.recommend_for_user(user_id, top_n=top_n, content_type=content_type)
    return RecommendationResponse(
        count=len(results),
        results=[RecommendationItem(**r) for r in results],
    )


@router.post("/content", response_model=RecommendationResponse)
def get_similar_content(payload: SimilarContentRequest):
    """Content-based 'more like this' recommendations for a given content_id."""
    model = get_model()
    if model.content_model.df is None or model.content_model.df.empty:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation model not ready — no content available yet.",
        )
    results = model.content_model.get_similar(payload.content_id, top_n=payload.top_n)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found in the current recommendation model.",
        )
    return RecommendationResponse(
        count=len(results),
        results=[RecommendationItem(**r) for r in results],
    )


@router.post("/semantic-search", response_model=RecommendationResponse)
def semantic_search(payload: SemanticSearchRequest, user_id: str = Depends(get_current_user_id)):
    """Natural language / semantic search over content."""
    from app.database.supabase_client import get_supabase_client

    get_supabase_client().table("search_history").insert(
        {"user_id": user_id, "query": payload.query}
    ).execute()

    model = get_model()
    if model.semantic_model.df is None or model.semantic_model.df.empty:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation model not ready — no content available yet.",
        )
    raw_results = model.semantic_model.search_by_text(payload.query, top_n=payload.top_n)
    results = [
        {
            "content_id": r["content_id"],
            "title": r["title"],
            "poster_url": r.get("poster_url"),
            "similarity_score": r["similarity_score"],
        }
        for r in raw_results
    ]
    return RecommendationResponse(
        count=len(results),
        results=[RecommendationItem(**r) for r in results],
    )