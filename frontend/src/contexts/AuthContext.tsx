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
        // On app load, restore session from localStorage if present.
        const storedUser = localStorage.getItem('user')
        const storedToken = localStorage.getItem('access_token')
        if (storedUser && storedToken) {
            setUser(JSON.parse(storedUser))
        }
        setIsLoading(false)
    }, [])

    const persistSession = (userId: string, email: string, accessToken: string) => {
        const userObj: User = { user_id: userId, email }
        localStorage.setItem('access_token', accessToken)
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
        persistSession(user_id, respEmail, access_token)
    }

    const login = async (email: string, password: string) => {
        const response = await api.post('/api/auth/login', { email, password })
        const { user_id, email: respEmail, access_token } = response.data
        persistSession(user_id, respEmail, access_token)
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