import type { ContentItem, RecommendationItem } from '../../types'
import { ContentCard } from './ContentCard'

interface ContentCarouselProps {
    title: string
    items: (ContentItem | RecommendationItem)[]
    getPosterUrl?: (item: ContentItem | RecommendationItem) => string | undefined
    isLoading?: boolean
}

export function ContentCarousel({ title, items, getPosterUrl, isLoading }: ContentCarouselProps) {
    if (!isLoading && items.length === 0) {
        return null
    }

    return (
        <section className="mb-10">
            <h2 className="text-xl font-semibold text-text-primary mb-4 px-6">{title}</h2>
            <div className="flex gap-4 overflow-x-auto px-6 pb-4 snap-x snap-mandatory scroll-pl-6 carousel-scroll">
                {isLoading
                    ? Array.from({ length: 6 }).map((_, i) => (
                        <div
                            key={i}
                            className="flex-shrink-0 w-44 aspect-[2/3] rounded-lg bg-surface animate-pulse snap-start"
                        />
                    ))
                    : items.map((item, i) => (
                        <ContentCard
                            key={('content_id' in item ? item.content_id : item.external_id) || i}
                            item={item}
                            posterUrl={getPosterUrl?.(item)}
                        />
                    ))}
            </div>
        </section>
    )
}