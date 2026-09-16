import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export function Navbar() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    return (
        <nav className="sticky top-0 z-50 bg-neutral-950/95 backdrop-blur border-b border-neutral-900">
            <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                <Link to="/" className="text-xl font-bold text-white tracking-tight">
                    Stream<span className="text-red-600">Sync</span> AI
                </Link>

                <div className="flex items-center gap-6">
                    <Link to="/" className="text-sm text-neutral-300 hover:text-white transition">
                        Home
                    </Link>
                    <Link to="/search" className="text-sm text-neutral-300 hover:text-white transition">
                        Search
                    </Link>
                    <Link to="/dashboard" className="text-sm text-neutral-300 hover:text-white transition">
                        My List
                    </Link>

                    {user && (
                        <div className="flex items-center gap-4 pl-4 border-l border-neutral-800">
                            <span className="text-sm text-neutral-400">{user.email}</span>
                            <button
                                onClick={handleLogout}
                                className="text-sm text-neutral-300 hover:text-red-500 transition font-medium"
                            >
                                Logout
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    )
}