import { api } from './api'
import type { DashboardData } from '../types'

export async function getDashboard() {
    const response = await api.get<DashboardData>('/api/user/dashboard')
    return response.data
}