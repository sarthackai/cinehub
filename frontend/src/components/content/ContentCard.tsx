import type { ContentItem, RecommendationItem } from '../../types'

interface ContentCardProps {
    item: ContentItem | RecommendationItem
    posterUrl?: string
}

export function ContentCard({ item, posterUrl }: ContentCardProps) {
    const title = item.title
    const explanation = 'explanation' in item ? item.explanation : undefined

    return (
        <div className="group flex-shrink-0 w-44 cursor-pointer">
            <div className="relative aspect-[2/3] rounded-lg overflow-hidden bg-surface transition-transform duration-200 group-hover:scale-[1.03]">
                {posterUrl ? (
                    <img
                        src={posterUrl}
                        alt={title}
                        className="w-full h-full object-cover"
                        loading="lazy"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-text-muted text-sm px-3 text-center">
                        {title}
                    </div>
                )}
            </div>
            <p className="mt-2 text-sm text-text-secondary truncate">{title}</p>
            {explanation && (
                <p className="text-xs text-text-muted truncate" title={explanation}>
                    {explanation}
                </p>
            )}
        </div>
    )
}