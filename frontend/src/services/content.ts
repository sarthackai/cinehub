import { api } from './api'
import type { ContentItem, RecommendationResponse } from '../types'

export async function getTrending(contentType: 'movie' | 'tv' = 'movie') {
    const response = await api.get<{ count: number; results: ContentItem[] }>(
        '/api/content/trending',
        { params: { content_type: contentType } }
    )
    return response.data.results
}

export async function getUserRecommendations(topN = 10) {
    const response = await api.get<RecommendationResponse>('/api/recommendations/user', {
        params: { top_n: topN },
    })
    return response.data.results
}

export async function semanticSearch(query: string, topN = 10) {
    const response = await api.post<RecommendationResponse>('/api/recommendations/semantic-search', {
        query,
        top_n: topN,
    })
    return response.data.results
}