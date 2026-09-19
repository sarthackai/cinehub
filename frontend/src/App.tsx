import { Routes, Route, Navigate } from 'react-router-dom'
import { Login } from './pages/Login'
import { Signup } from './pages/Signup'
import { Home } from './pages/Home'
import { Navbar } from './components/common/Navbar'
import { useAuth } from './contexts/AuthContext'
import { ContentDetails } from './pages/ContentDetails'
import { Search } from './pages/Search'
import { Dashboard } from './pages/Dashboard'
import { Browse } from './pages/Browse'

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" />
  return (
    <div className="min-h-screen bg-base">
      <Navbar />
      {children}
    </div>
  )
}

function App() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <p className="text-text-primary">Loading...</p>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
      <Route path="/signup" element={user ? <Navigate to="/" /> : <Signup />} />
      <Route
        path="/"
        element={
          <ProtectedLayout>
            <Home />
          </ProtectedLayout>
        }
      />
      <Route
        path="/content/:id"
        element={
          <ProtectedLayout>
            <ContentDetails />
          </ProtectedLayout>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedLayout>
            <Search />
          </ProtectedLayout>
        }
      />
      <Route
        path="/browse/:type"
        element={
          <ProtectedLayout>
            <Browse />
          </ProtectedLayout>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedLayout>
            <Dashboard />
          </ProtectedLayout>
        }
      />
    </Routes>
  )
}

export default App