import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts'
import { getDashboard } from '../services/dashboard'
import { listFavorites, listWatchlist } from '../services/interactions'
import { ContentCarousel } from '../components/content/ContentCarousel'
import type { DashboardData, ContentItem } from '../types'

const CHART_COLORS = ['#E8A33D', '#F2B457', '#C9CAD9', '#6B6C7E']

function StatCard({ label, value }: { label: string; value: number | string }) {
    return (
        <div className="bg-surface rounded-xl px-6 py-5">
            <p className="text-3xl font-bold text-text-primary">{value}</p>
            <p className="text-sm text-text-muted mt-1">{label}</p>
        </div>
    )
}

export function Dashboard() {
    const [data, setData] = useState<DashboardData | null>(null)
    const [favorites, setFavorites] = useState<ContentItem[]>([])
    const [watchlist, setWatchlist] = useState<ContentItem[]>([])
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        Promise.all([getDashboard(), listFavorites(), listWatchlist()])
            .then(([dashboardData, favs, wl]) => {
                setData(dashboardData)
                setFavorites(favs)
                setWatchlist(wl)
            })
            .catch((err) => console.error('Failed to load dashboard:', err))
            .finally(() => setIsLoading(false))
    }, [])

    if (isLoading) {
        return (
            <div className="min-h-screen bg-base flex items-center justify-center">
                <p className="text-text-secondary">Loading your dashboard...</p>
            </div>
        )
    }

    if (!data) {
        return (
            <div className="min-h-screen bg-base flex items-center justify-center">
                <p className="text-text-secondary">Couldn't load your dashboard.</p>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-base pt-10 px-6 pb-10">
            <div className="max-w-6xl mx-auto">
                <h1 className="text-3xl font-bold text-text-primary mb-8">My Dashboard</h1>

                {/* Stat cards */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-10">
                    <StatCard label="Watched" value={data.totals.watched} />
                    <StatCard label="Rated" value={data.totals.rated} />
                    <StatCard label="Favorites" value={data.totals.favorites} />
                    <StatCard label="Watchlist" value={data.totals.watchlist} />
                    <StatCard
                        label="Avg. Rating Given"
                        value={data.average_rating_given !== null ? data.average_rating_given.toFixed(1) : '—'}
                    />
                </div>

                {/* Favorite genres chart */}
                {data.favorite_genres.length > 0 && (
                    <div className="bg-surface rounded-xl p-6 mb-10">
                        <h2 className="text-lg font-semibold text-text-primary mb-4">Your Favorite Genres</h2>
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart data={data.favorite_genres} layout="vertical" margin={{ left: 20 }}>
                                <XAxis type="number" hide />
                                <YAxis
                                    type="category"
                                    dataKey="genre"
                                    width={120}
                                    tick={{ fill: '#C9CAD9', fontSize: 13 }}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: '#151520',
                                        border: '1px solid #1D1D2B',
                                        borderRadius: 8,
                                    }}
                                    labelStyle={{ color: '#F5F5F7' }}
                                />
                                <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                                    {data.favorite_genres.map((_, i) => (
                                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </div>

            <ContentCarousel
                title="My Favorites"
                items={favorites}
                getPosterUrl={(item) => ('poster_url' in item ? item.poster_url ?? undefined : undefined)}
            />

            <ContentCarousel
                title="My Watchlist"
                items={watchlist}
                getPosterUrl={(item) => ('poster_url' in item ? item.poster_url ?? undefined : undefined)}
            />
        </div>
    )
}