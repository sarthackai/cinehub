export interface User {
    user_id: string
    email: string
}

export interface AuthResponse {
    access_token: string
    refresh_token: string
    user_id: string
    email: string
}

export interface ContentItem {
    content_id?: string
    external_id?: string | number
    title: string
    overview?: string
    poster_path?: string
    backdrop_path?: string
    release_date?: string
    rating?: number
    vote_count?: number
    popularity?: number
}

export interface RecommendationItem {
    content_id: string
    title: string
    final_score?: number | null
    similarity_score?: number | null
    explanation?: string | null
}

export interface RecommendationResponse {
    count: number
    results: RecommendationItem[]
}

export interface ApiError {
    error: boolean
    message: string
    path?: string
    details?: unknown
}