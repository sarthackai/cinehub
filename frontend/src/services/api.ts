import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_BACKEND_API_URL || 'http://127.0.0.1:8000'

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Attach the stored access token to every outgoing request, if present.
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// If a request comes back 401 (expired/invalid token), clear the stored
// session so the app can redirect to login rather than looping on stale auth.
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('access_token')
            localStorage.removeItem('user')
        }
        return Promise.reject(error)
    }
)