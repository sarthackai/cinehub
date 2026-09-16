import { useEffect, useState } from 'react'
import { ContentCarousel } from '../components/content/ContentCarousel'
import { getTrending, getUserRecommendations } from '../services/content'
import type { ContentItem, RecommendationItem } from '../types'

export function Home() {
    const [trending, setTrending] = useState<ContentItem[]>([])
    const [recommendations, setRecommendations] = useState<RecommendationItem[]>([])
    const [isLoadingTrending, setIsLoadingTrending] = useState(true)
    const [isLoadingRecs, setIsLoadingRecs] = useState(true)

    useEffect(() => {
        getTrending('movie')
            .then(setTrending)
            .catch((err) => console.error('Failed to load trending:', err))
            .finally(() => setIsLoadingTrending(false))

        getUserRecommendations(10)
            .then(setRecommendations)
            .catch((err) => console.error('Failed to load recommendations:', err))
            .finally(() => setIsLoadingRecs(false))
    }, [])

    return (
        <div className="min-h-screen bg-base pt-8">
            <div className="mb-10 px-6">
                <h1 className="text-3xl font-bold text-text-primary mb-1">Welcome back</h1>
                <p className="text-text-secondary">Here's what we think you'll enjoy</p>
            </div>

            <ContentCarousel
                title="Recommended For You"
                items={recommendations}
                isLoading={isLoadingRecs}
                getPosterUrl={(item) => ('poster_url' in item ? item.poster_url ?? undefined : undefined)}
            />

            <ContentCarousel
                title="Trending Now"
                items={trending}
                isLoading={isLoadingTrending}
                getPosterUrl={(item) =>
                    'poster_path' in item && item.poster_path
                        ? `https://image.tmdb.org/t/p/w342${item.poster_path}`
                        : undefined
                }
            />
        </div>
    )
}