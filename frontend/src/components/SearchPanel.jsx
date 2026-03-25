import { useState, useCallback } from 'react'
import { Search, Loader2, ArrowRight, Calendar, Star, X } from 'lucide-react'
import { useStore } from '../store/index.js'
import { searchPapers } from '../services/api.js'
import { getSummary } from '../services/api.js'
import clsx from 'clsx'

export default function SearchPanel() {
  const { setActiveTab, selectPaper, setSummary, setSummaryLoading } = useStore()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [yearMin, setYearMin] = useState('')
  const [yearMax, setYearMax] = useState('')

  async function handleSearch(e) {
    e?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const filters = {}
      if (yearMin) filters.year_min = parseInt(yearMin)
      if (yearMax) filters.year_max = parseInt(yearMax)
      const data = await searchPapers(query, 20, Object.keys(filters).length ? filters : null)
      setResults(data.results || [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  async function openPaper(paper) {
    selectPaper(paper)
    setActiveTab('graph')
    setSummaryLoading(true)
    try {
      const summary = await getSummary(paper.id)
      setSummary(summary)
    } catch {
      setSummary(null)
    } finally {
      setSummaryLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col p-6 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display font-semibold text-lg text-text-primary">Semantic Search</h2>
          <p className="text-xs text-muted mt-0.5">Hybrid FAISS + BM25 + cross-encoder reranking</p>
        </div>
        <button onClick={() => setActiveTab('graph')} className="text-muted hover:text-text-primary transition-colors">
          <X size={18} />
        </button>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="flex flex-col gap-3 mb-6">
        <div className="relative">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            autoFocus
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search papers semantically… e.g. 'attention mechanisms in vision transformers'"
            className="w-full bg-panel border border-border rounded-xl pl-10 pr-4 py-3 text-sm text-text-primary placeholder-muted focus:outline-none focus:border-accent/60 transition-colors"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Calendar size={12} className="text-muted" />
            <input
              value={yearMin}
              onChange={e => setYearMin(e.target.value)}
              placeholder="From"
              type="number"
              min="1900" max="2030"
              className="w-20 bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-accent/40 placeholder-muted"
            />
            <span className="text-muted text-xs">–</span>
            <input
              value={yearMax}
              onChange={e => setYearMax(e.target.value)}
              placeholder="To"
              type="number"
              min="1900" max="2030"
              className="w-20 bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-accent/40 placeholder-muted"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="ml-auto flex items-center gap-2 px-5 py-2 bg-accent/20 text-accent border border-accent/40 rounded-xl text-sm font-medium hover:bg-accent/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            Search
          </button>
        </div>
      </form>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="bg-panel border border-border rounded-xl p-4 flex flex-col gap-2">
                <div className="skeleton h-4 w-3/4 rounded" />
                <div className="skeleton h-3 w-1/2 rounded" />
                <div className="skeleton h-3 w-full rounded" />
              </div>
            ))}
          </div>
        ) : results.length > 0 ? (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-muted mb-2 font-mono">{results.length} results</p>
            {results.map((paper) => (
              <button
                key={paper.id}
                onClick={() => openPaper(paper)}
                className="w-full text-left bg-panel hover:bg-surface border border-border hover:border-accent/30 rounded-xl p-4 transition-all group"
              >
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-sm text-text-primary font-medium leading-snug line-clamp-2 group-hover:text-accent transition-colors">
                    {paper.title}
                  </h3>
                  <ArrowRight size={14} className="text-muted group-hover:text-accent shrink-0 mt-0.5 transition-colors" />
                </div>

                <div className="flex items-center gap-3 mt-2">
                  {paper.authors?.[0]?.name && (
                    <span className="text-[11px] text-muted truncate max-w-[140px]">
                      {paper.authors[0].name}{paper.authors.length > 1 ? ` +${paper.authors.length - 1}` : ''}
                    </span>
                  )}
                  {paper.year && (
                    <span className="text-[11px] text-muted font-mono">{paper.year}</span>
                  )}
                  {paper.citation_count > 0 && (
                    <span className="flex items-center gap-0.5 text-[11px] text-amber-400">
                      <Star size={9} /> {paper.citation_count}
                    </span>
                  )}
                  {paper.source && (
                    <span className="pill bg-dim text-muted text-[10px] capitalize ml-auto">
                      {paper.source.replace('_', ' ')}
                    </span>
                  )}
                </div>

                {paper.abstract && (
                  <p className="text-[11px] text-muted mt-2 leading-relaxed line-clamp-2">
                    {paper.abstract}
                  </p>
                )}
              </button>
            ))}
          </div>
        ) : searched ? (
          <div className="text-center py-16 text-muted">
            <Search size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No results found</p>
            <p className="text-xs mt-1">Try ingesting papers first via the top bar</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 opacity-60">
            {['transformer attention mechanisms', 'graph neural network applications', 'diffusion models image generation', 'retrieval augmented generation RAG'].map(suggestion => (
              <button
                key={suggestion}
                onClick={() => { setQuery(suggestion); handleSearch() }}
                className="text-left bg-panel border border-border rounded-xl p-3 hover:border-accent/30 transition-colors"
              >
                <p className="text-xs text-text-secondary leading-snug">{suggestion}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
