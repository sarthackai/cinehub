import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { browseContent } from '../services/content'
import { ContentCard } from '../components/content/ContentCard'
import type { ContentItem } from '../types'

export function Browse() {
    const { type } = useParams<{ type: string }>()
    const contentType = type === 'tv' ? 'tv' : 'movie'
    const [items, setItems] = useState<ContentItem[]>([])
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        setIsLoading(true)
        browseContent(contentType)
            .then(setItems)
            .catch((err) => console.error('Failed to load content:', err))
            .finally(() => setIsLoading(false))
    }, [contentType])

    return (
        <div className="min-h-screen bg-base pt-10 px-6 pb-10">
            <h1 className="text-3xl font-bold text-text-primary mb-8">
                {contentType === 'tv' ? 'TV Shows' : 'Movies'}
            </h1>

            {isLoading && <p className="text-text-secondary">Loading...</p>}

            {!isLoading && items.length === 0 && (
                <p className="text-text-secondary">No content available yet.</p>
            )}

            {!isLoading && items.length > 0 && (
                <div className="flex flex-wrap gap-4">
                    {items.map((item) => (
                        <ContentCard key={item.content_id} item={item} posterUrl={item.poster_url ?? undefined} />
                    ))}
                </div>
            )}
        </div>
    )
}