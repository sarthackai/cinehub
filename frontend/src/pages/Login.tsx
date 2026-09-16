import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'

export function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const { login } = useAuth()
    const navigate = useNavigate()

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError('')
        setIsLoading(true)
        try {
            await login(email, password)
            navigate('/')
        } catch (err: any) {
            setError(err.response?.data?.message || err.response?.data?.detail || 'Login failed')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-neutral-950 flex items-center justify-center px-4">
            <div className="w-full max-w-md">
                <h1 className="text-3xl font-bold text-white mb-2 text-center">StreamSync AI</h1>
                <p className="text-neutral-400 text-center mb-8">Sign in to continue</p>

                <form
                    onSubmit={handleSubmit}
                    className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-8 flex flex-col gap-5"
                >
                    <Input
                        id="email"
                        label="Email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        required
                    />
                    <Input
                        id="password"
                        label="Password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                    />

                    {error && (
                        <p className="text-sm text-red-500 bg-red-950/50 border border-red-900 rounded-lg px-3 py-2">
                            {error}
                        </p>
                    )}

                    <Button type="submit" isLoading={isLoading} className="w-full mt-2">
                        Sign In
                    </Button>
                </form>

                <p className="text-center text-neutral-500 mt-6">
                    Don't have an account?{' '}
                    <Link to="/signup" className="text-red-500 hover:text-red-400 font-medium">
                        Sign up
                    </Link>
                </p>
            </div>
        </div>
    )
}