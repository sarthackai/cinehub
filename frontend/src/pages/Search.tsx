import { useState, type FormEvent } from 'react'
import { keywordSearch, semanticSearch } from '../services/content'
import { ContentCard } from '../components/content/ContentCard'
import type { ContentItem, RecommendationItem } from '../types'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'

type SearchMode = 'keyword' | 'ai'

export function Search() {
    const [query, setQuery] = useState('')
    const [mode, setMode] = useState<SearchMode>('keyword')
    const [results, setResults] = useState<(ContentItem | RecommendationItem)[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [hasSearched, setHasSearched] = useState(false)

    const handleSearch = async (e: FormEvent) => {
        e.preventDefault()
        if (!query.trim()) return

        setIsLoading(true)
        setHasSearched(true)
        try {
            if (mode === 'keyword') {
                const items = await keywordSearch(query)
                setResults(items)
            } else {
                const items = await semanticSearch(query, 20)
                setResults(items)
            }
        } catch (err) {
            console.error('Search failed:', err)
            setResults([])
        } finally {
            setIsLoading(false)
        }
    }

    const getPosterUrl = (item: ContentItem | RecommendationItem) => {
        if ('poster_url' in item && item.poster_url) return item.poster_url
        if ('poster_path' in item && item.poster_path)
            return `https://image.tmdb.org/t/p/w342${item.poster_path}`
        return undefined
    }

    return (
        <div className="min-h-screen bg-base pt-10 px-6">
            <div className="max-w-3xl mx-auto mb-8">
                <h1 className="text-3xl font-bold text-text-primary mb-6">Search</h1>

                <div className="flex gap-2 mb-4">
                    <button
                        onClick={() => setMode('keyword')}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition ${mode === 'keyword'
                                ? 'bg-accent text-base'
                                : 'bg-surface text-text-secondary hover:text-text-primary'
                            }`}
                    >
                        Title Search
                    </button>
                    <button
                        onClick={() => setMode('ai')}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition ${mode === 'ai'
                                ? 'bg-accent text-base'
                                : 'bg-surface text-text-secondary hover:text-text-primary'
                            }`}
                    >
                        Ask AI ✨
                    </button>
                </div>

                <form onSubmit={handleSearch} className="flex gap-3">
                    <div className="flex-1">
                        <Input
                            id="search"
                            label=""
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder={
                                mode === 'keyword'
                                    ? 'Search by title...'
                                    : "e.g. 'a funny movie under 2 hours' or 'like Interstellar'"
                            }
                        />
                    </div>
                    <Button type="submit" isLoading={isLoading}>
                        Search
                    </Button>
                </form>

                {mode === 'ai' && (
                    <p className="text-xs text-text-muted mt-2">
                        Describe what you're in the mood for — no need for exact titles or genres.
                    </p>
                )}
            </div>

            <div className="max-w-6xl mx-auto">
                {isLoading && <p className="text-text-secondary text-center py-10">Searching...</p>}

                {!isLoading && hasSearched && results.length === 0 && (
                    <p className="text-text-secondary text-center py-10">
                        No results found. Try a different search.
                    </p>
                )}

                {!isLoading && results.length > 0 && (
                    <div className="flex flex-wrap gap-4">
                        {results.map((item, i) => (
                            <ContentCard
                                key={('content_id' in item ? item.content_id : item.external_id) || i}
                                item={item}
                                posterUrl={getPosterUrl(item)}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}