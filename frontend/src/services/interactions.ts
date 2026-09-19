import { api } from './api'
import type { ContentItem } from '../types'

export async function addFavorite(contentId: string) {
    await api.post('/api/favorites', { content_id: contentId })
}

export async function removeFavorite(contentId: string) {
    await api.delete(`/api/favorites/${contentId}`)
}

export async function listFavorites() {
    const response = await api.get<{ count: number; results: ContentItem[] }>('/api/favorites')
    return response.data.results
}

export async function addToWatchlist(contentId: string) {
    await api.post('/api/watchlist', { content_id: contentId })
}

export async function removeFromWatchlist(contentId: string) {
    await api.delete(`/api/watchlist/${contentId}`)
}

export async function listWatchlist() {
    const response = await api.get<{ count: number; results: ContentItem[] }>('/api/watchlist')
    return response.data.results
}

export async function rateContent(contentId: string, rating: number) {
    await api.post('/api/ratings', { content_id: contentId, rating })
}

export async function listRatings() {
    const response = await api.get<{ count: number; results: { content_id: string; rating: number }[] }>(
        '/api/ratings'
    )
    return response.data.results
}

export async function recordWatch(contentId: string, progressPercent = 100) {
    await api.post('/api/watch-history', { content_id: contentId, progress_percent: progressPercent })
}

export async function removeRating(contentId: string) {
    await api.delete(`/api/ratings/${contentId}`)
}