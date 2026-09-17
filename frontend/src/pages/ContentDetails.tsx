import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getContentDetails, getSimilarContent } from '../services/content'
import { ContentCarousel } from '../components/content/ContentCarousel'
import type { ContentDetails as ContentDetailsType, RecommendationItem } from '../types'

export function ContentDetails() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const [details, setDetails] = useState<ContentDetailsType | null>(null)
    const [similar, setSimilar] = useState<RecommendationItem[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isLoadingSimilar, setIsLoadingSimilar] = useState(true)

    useEffect(() => {
        if (!id) return
        getContentDetails(id)
            .then(setDetails)
            .catch((err) => console.error('Failed to load content details:', err))
            .finally(() => setIsLoading(false))

        getSimilarContent(id, 10)
            .then(setSimilar)
            .catch((err) => console.error('Failed to load similar content:', err))
            .finally(() => setIsLoadingSimilar(false))
    }, [id])

    if (isLoading) {
        return (
            <div className="min-h-screen bg-base flex items-center justify-center">
                <p className="text-text-secondary">Loading...</p>
            </div>
        )
    }

    if (!details) {
        return (
            <div className="min-h-screen bg-base flex items-center justify-center">
                <p className="text-text-secondary">Content not found.</p>
            </div>
        )
    }

    const year = details.release_date ? details.release_date.slice(0, 4) : null

    return (
        <div className="min-h-screen bg-base">
            {/* Backdrop hero */}
            <div className="relative w-full h-[60vh] overflow-hidden">
                {details.backdrop_url && (
                    <img
                        src={details.backdrop_url}
                        alt={details.title}
                        className="w-full h-full object-cover"
                    />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-base via-base/70 to-transparent" />
                <button
                    onClick={() => navigate(-1)}
                    className="absolute top-6 left-6 text-text-primary bg-black/40 hover:bg-black/60 rounded-full w-10 h-10 flex items-center justify-center transition"
                >
                    ←
                </button>
            </div>

            {/* Content info, overlapping the backdrop */}
            <div className="max-w-5xl mx-auto px-6 -mt-32 relative z-10">
                <div className="flex gap-6 items-end mb-6">
                    {details.poster_url && (
                        <img
                            src={details.poster_url}
                            alt={details.title}
                            className="w-40 rounded-lg shadow-2xl flex-shrink-0 hidden sm:block"
                        />
                    )}
                    <div>
                        <h1 className="text-4xl font-bold text-text-primary mb-2">{details.title}</h1>
                        <div className="flex items-center gap-3 text-text-secondary text-sm flex-wrap">
                            {year && <span>{year}</span>}
                            {details.runtime_minutes && <span>{details.runtime_minutes} min</span>}
                            {details.provider_rating && (
                                <span className="flex items-center gap-1 text-accent font-medium">
                                    ★ {details.provider_rating.toFixed(1)}
                                    <span className="text-text-muted">({details.provider_vote_count} votes)</span>
                                </span>
                            )}
                            {details.genres.map((g) => (
                                <span key={g} className="bg-surface px-2.5 py-0.5 rounded-full text-xs">
                                    {g}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>

                {details.overview && (
                    <p className="text-text-secondary leading-relaxed max-w-3xl mb-8">{details.overview}</p>
                )}

                {details.cast.length > 0 && (
                    <div className="mb-10">
                        <h2 className="text-xl font-semibold text-text-primary mb-4">Cast</h2>
                        <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide">
                            {details.cast.map((member, i) => (
                                <div key={i} className="flex-shrink-0 w-24 text-center">
                                    <div className="w-24 h-24 rounded-full overflow-hidden bg-surface mb-2">
                                        {member.profile_image_url && (
                                            <img
                                                src={member.profile_image_url}
                                                alt={member.name}
                                                className="w-full h-full object-cover"
                                            />
                                        )}
                                    </div>
                                    <p className="text-sm text-text-primary truncate">{member.name}</p>
                                    {member.character && (
                                        <p className="text-xs text-text-muted truncate">{member.character}</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {details.crew.length > 0 && (
                    <div className="mb-10 flex gap-8 text-sm">
                        {details.crew.map((member, i) => (
                            <div key={i}>
                                <p className="text-text-muted">{member.role}</p>
                                <p className="text-text-primary font-medium">{member.name}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <ContentCarousel
                title="More Like This"
                items={similar}
                isLoading={isLoadingSimilar}
                getPosterUrl={(item) => ('poster_url' in item ? item.poster_url ?? undefined : undefined)}
            />
        </div>
    )
}