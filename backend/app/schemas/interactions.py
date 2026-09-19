from pydantic import BaseModel


class ContentIdRequest(BaseModel):
    content_id: str


class RatingRequest(BaseModel):
    content_id: str
    rating: float  # 0.5 - 5.0


class WatchProgressRequest(BaseModel):
    content_id: str
    progress_percent: float = 100.0