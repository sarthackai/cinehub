import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getAdminAnalytics, triggerFullSync } from '../services/admin'
import { Button } from '../components/ui/Button'
import type { AdminAnalytics } from '../types'

function StatCard({ label, value }: { label: string; value: number | string }) {
    return (
        <div className="bg-surface rounded-xl px-6 py-5">
            <p className="text-3xl font-bold text-text-primary">{value}</p>
            <p className="text-sm text-text-muted mt-1">{label}</p>
        </div>
    )
}

function StatusBadge({ status }: { status: string }) {
    const colors: Record<string, string> = {
        success: 'bg-green-950 text-green-400 border-green-900',
        partial: 'bg-yellow-950 text-yellow-400 border-yellow-900',
        failed: 'bg-red-950 text-red-400 border-red-900',
    }
    return (
        <span
            className={`text-xs px-2 py-0.5 rounded-full border ${colors[status] || 'bg-surface text-text-muted'}`}
        >
            {status}
        </span>
    )
}

export function Admin() {
    const { user } = useAuth()
    const [data, setData] = useState<AdminAnalytics | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isSyncing, setIsSyncing] = useState(false)
    const [syncMessage, setSyncMessage] = useState('')

    const loadAnalytics = () => {
        setIsLoading(true)
        getAdminAnalytics()
            .then(setData)
            .catch((err) => console.error('Failed to load admin analytics:', err))
            .finally(() => setIsLoading(false))
    }

    useEffect(() => {
        loadAnalytics()
    }, [])

    const handleFullSync = async () => {
        setIsSyncing(true)
        setSyncMessage('')
        try {
            const result = await triggerFullSync()
            setSyncMessage(
                `Sync complete: ${result.jobs_run - result.jobs_failed}/${result.jobs_run} jobs succeeded, ${result.total_rows_processed} rows processed.`
            )
            loadAnalytics()
        } catch (err) {
            setSyncMessage('Sync failed. Check backend logs.')
            console.error(err)
        } finally {
            setIsSyncing(false)
        }
    }

    if (!user?.is_admin) {
        return <Navigate to="/" />
    }

    if (isLoading || !data) {
        return (
            <div className="min-h-screen bg-base flex items-center justify-center">
                <p className="text-text-secondary">Loading admin dashboard...</p>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-base pt-10 px-6 pb-10">
            <div className="max-w-6xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <h1 className="text-3xl font-bold text-text-primary">Admin Dashboard</h1>
                    <Button onClick={handleFullSync} isLoading={isSyncing}>
                        Run Full Sync Now
                    </Button>
                </div>

                {syncMessage && (
                    <p className="text-sm text-text-secondary bg-surface rounded-lg px-4 py-2 mb-6">
                        {syncMessage}
                    </p>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
                    <StatCard label="Total Content" value={data.totals.content} />
                    <StatCard label="Movies" value={data.totals.movies} />
                    <StatCard label="TV Shows" value={data.totals.tv_shows} />
                    <StatCard label="Users" value={data.totals.users} />
                </div>

                <div className="grid md:grid-cols-2 gap-8">
                    {/* Sync history */}
                    <div className="bg-surface rounded-xl p-6">
                        <h2 className="text-lg font-semibold text-text-primary mb-4">Recent Syncs</h2>
                        <div className="space-y-2 max-h-96 overflow-y-auto carousel-scroll pr-2">
                            {data.recent_syncs.map((sync, i) => (
                                <div
                                    key={i}
                                    className="flex items-center justify-between bg-base rounded-lg px-3 py-2 text-sm"
                                >
                                    <div>
                                        <p className="text-text-primary font-medium">
                                            {sync.job_name} <span className="text-text-muted">({sync.provider})</span>
                                        </p>
                                        <p className="text-text-muted text-xs">
                                            {new Date(sync.started_at).toLocaleString()}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <StatusBadge status={sync.status} />
                                        <p className="text-text-muted text-xs mt-1">{sync.rows_processed} rows</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Most favorited */}
                    <div className="bg-surface rounded-xl p-6">
                        <h2 className="text-lg font-semibold text-text-primary mb-4">Most Favorited Content</h2>
                        {data.most_favorited.length === 0 ? (
                            <p className="text-text-muted text-sm">No favorites recorded yet.</p>
                        ) : (
                            <div className="space-y-2">
                                {data.most_favorited.map((item) => (
                                    <div
                                        key={item.content_id}
                                        className="flex items-center gap-3 bg-base rounded-lg px-3 py-2"
                                    >
                                        {item.poster_url && (
                                            <img
                                                src={item.poster_url}
                                                alt={item.title}
                                                className="w-10 h-14 object-cover rounded"
                                            />
                                        )}
                                        <p className="text-text-primary text-sm flex-1">{item.title}</p>
                                        <span className="text-accent text-sm font-medium">{item.favorite_count} ♥</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Popular searches */}
                <div className="bg-surface rounded-xl p-6 mt-8">
                    <h2 className="text-lg font-semibold text-text-primary mb-4">Popular Searches</h2>
                    {data.popular_searches.length === 0 ? (
                        <p className="text-text-muted text-sm">No searches recorded yet.</p>
                    ) : (
                        <div className="flex flex-wrap gap-2">
                            {data.popular_searches.map((s, i) => (
                                <span key={i} className="bg-base px-3 py-1.5 rounded-full text-sm text-text-secondary">
                                    {s.query} <span className="text-text-muted">({s.count})</span>
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}