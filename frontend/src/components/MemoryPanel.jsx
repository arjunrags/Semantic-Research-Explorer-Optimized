import { useState, useEffect } from 'react'
import { Brain, Search, BarChart2, X, Loader2, Sparkles, RefreshCw } from 'lucide-react'
import { useStore } from '../store/index.js'
import { searchMemory, getMemoryStats } from '../services/api.js'

export default function MemoryPanel() {
  const { setActiveTab } = useStore()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)

  useEffect(() => {
    loadStats()
  }, [])

  async function loadStats() {
    setStatsLoading(true)
    try {
      const data = await getMemoryStats()
      setStats(data)
    } catch {
      setStats({ available: false })
    } finally {
      setStatsLoading(false)
    }
  }

  async function handleSearch(e) {
    e?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      const data = await searchMemory(query, 'both')
      setResults(data)
    } catch {
      setResults({ memories: [], available: false })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col p-6 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display font-semibold text-lg text-text-primary flex items-center gap-2">
            <Brain size={18} className="text-amber-400" />
            Research Memory
          </h2>
          <p className="text-xs text-muted mt-0.5">Personal knowledge via Membrain API</p>
        </div>
        <button onClick={() => setActiveTab('graph')} className="text-muted hover:text-text-primary">
          <X size={18} />
        </button>
      </div>

      {/* Stats */}
      {stats && stats.available !== false && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: 'Total Memories', value: stats.total_memories || stats.count || '—', color: 'text-amber-400' },
            { label: 'Tagged Papers', value: stats.tagged_items || '—', color: 'text-accent' },
            { label: 'Graph Nodes', value: stats.graph_nodes || '—', color: 'text-emerald' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-panel border border-border rounded-xl p-3 text-center">
              <div className={`text-xl font-display font-bold ${color}`}>{value}</div>
              <div className="text-[10px] text-muted mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}

      {stats?.available === false && (
        <div className="flex items-center gap-2 bg-amber-500/5 border border-amber-500/20 rounded-xl p-3 mb-5 text-xs text-text-secondary">
          <Brain size={13} className="text-amber-400 shrink-0" />
          Membrain API unavailable – memories stored locally in PostgreSQL as fallback.
        </div>
      )}

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search your research memories…"
            className="w-full bg-panel border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-text-primary placeholder-muted focus:outline-none focus:border-amber-400/50 transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-4 py-2.5 bg-amber-400/15 text-amber-400 border border-amber-400/30 rounded-xl text-sm font-medium hover:bg-amber-400/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
        </button>
      </form>

      {/* Results */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-4">
        {results?.interpreted && (
          <div className="bg-amber-400/5 border border-amber-400/20 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={12} className="text-amber-400" />
              <p className="text-[10px] uppercase tracking-widest text-amber-400 font-display">Interpreted Insight</p>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">{results.interpreted}</p>
          </div>
        )}

        {results?.memories?.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-muted font-mono">{results.memories.length} memories</p>
            {results.memories.map((mem, i) => (
              <div key={i} className="bg-panel border border-border rounded-xl p-3">
                <p className="text-sm text-text-primary leading-relaxed">
                  {mem.content || mem.text || JSON.stringify(mem)}
                </p>
                {mem.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {mem.tags.map(tag => (
                      <span key={tag} className="pill bg-dim text-muted text-[10px]">{tag}</span>
                    ))}
                  </div>
                )}
                {mem.created_at && (
                  <p className="text-[10px] text-muted/60 mt-1.5">
                    {new Date(mem.created_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {results && !results.memories?.length && !results.interpreted && (
          <div className="text-center py-12 text-muted">
            <Brain size={28} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No memories found</p>
            <p className="text-xs mt-1 opacity-60">Save notes on papers using the paper panel</p>
          </div>
        )}

        {!results && (
          <div className="text-center py-12 text-muted">
            <Brain size={36} className="mx-auto mb-4 text-amber-400/20" />
            <p className="text-sm mb-1">Your research memory</p>
            <p className="text-xs opacity-60 max-w-xs mx-auto">
              Notes and facts you save while reading papers are stored here via Membrain's semantic memory API.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
