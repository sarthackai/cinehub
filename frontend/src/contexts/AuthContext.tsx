import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { api } from '../services/api'
import type { User } from '../types'

interface AuthContextType {
    user: User | null
    isLoading: boolean
    signup: (email: string, password: string, displayName?: string) => Promise<void>
    login: (email: string, password: string) => Promise<void>
    logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        const storedToken = localStorage.getItem('access_token')
        if (storedToken) {
            // Re-fetch /me on load to get fresh is_admin status, not just cached data
            api
                .get('/api/auth/me')
                .then((res) => {
                    const storedUser = localStorage.getItem('user')
                    const baseUser = storedUser ? JSON.parse(storedUser) : {}
                    const fullUser: User = { ...baseUser, is_admin: res.data.is_admin }
                    localStorage.setItem('user', JSON.stringify(fullUser))
                    setUser(fullUser)
                })
                .catch(() => {
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('user')
                })
                .finally(() => setIsLoading(false))
        } else {
            setIsLoading(false)
        }
    }, [])

    const persistSession = async (userId: string, email: string, accessToken: string) => {
        localStorage.setItem('access_token', accessToken)
        const meResponse = await api.get('/api/auth/me', {
            headers: { Authorization: `Bearer ${accessToken}` },
        })
        const userObj: User = { user_id: userId, email, is_admin: meResponse.data.is_admin }
        localStorage.setItem('user', JSON.stringify(userObj))
        setUser(userObj)
    }

    const signup = async (email: string, password: string, displayName?: string) => {
        const response = await api.post('/api/auth/signup', {
            email,
            password,
            display_name: displayName,
        })
        const { user_id, email: respEmail, access_token } = response.data
        await persistSession(user_id, respEmail, access_token)
    }

    const login = async (email: string, password: string) => {
        const response = await api.post('/api/auth/login', { email, password })
        const { user_id, email: respEmail, access_token } = response.data
        await persistSession(user_id, respEmail, access_token)
    }

    const logout = () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        setUser(null)
    }

    return (
        <AuthContext.Provider value={{ user, isLoading, signup, login, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}