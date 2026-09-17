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
    poster_url?: string | null
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

export interface CastMember {
    name: string
    character?: string | null
    profile_image_url?: string | null
}

export interface CrewMember {
    name: string
    role: string
}

export interface ContentDetails {
    id: string
    title: string
    original_title?: string | null
    overview?: string | null
    poster_url?: string | null
    backdrop_url?: string | null
    release_date?: string | null
    language?: string | null
    runtime_minutes?: number | null
    number_of_seasons?: number | null
    number_of_episodes?: number | null
    provider_rating?: number | null
    provider_vote_count?: number | null
    popularity?: number | null
    genres: string[]
    cast: CastMember[]
    crew: CrewMember[]
}