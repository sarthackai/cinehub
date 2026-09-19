import { api } from './api'
import type { AdminAnalytics } from '../types'

export async function getAdminAnalytics() {
    const response = await api.get<AdminAnalytics>('/api/admin/analytics')
    return response.data
}

export async function triggerFullSync() {
    const response = await api.post('/api/admin/sync/full')
    return response.data
}