import { useState } from 'react'
import { Search, Network, Cpu, RefreshCw, Github } from 'lucide-react'
import { useStore } from '../store/index.js'
import { ingestPapers, checkHealth } from '../services/api.js'
import toast from 'react-hot-toast'
import clsx from 'clsx'

export default function Topbar({ onReloadGraph }) {
  const { setActiveTab, activeTab } = useStore()
  const [ingestQuery, setIngestQuery] = useState('')
  const [ingesting, setIngesting] = useState(false)
  const [health, setHealth] = useState(null)

  async function handleIngest(e) {
    e.preventDefault()
    if (!ingestQuery.trim()) return
    setIngesting(true)
    try {
      const res = await ingestPapers(ingestQuery, 15)
      toast.success(`Ingested ${res.ingested} papers (${res.new} new)`)
      setIngestQuery('')
      setTimeout(onReloadGraph, 2000) // reload after indexing starts
    } catch {
      // error handled by interceptor
    } finally {
      setIngesting(false)
    }
  }

  async function handleHealthCheck() {
    try {
      const data = await checkHealth()
      setHealth(data)
      toast.success(`Backend: ${data.status}`)
    } catch {
      toast.error('Backend unreachable')
    }
  }

  return (
    <header className="h-12 flex items-center px-4 gap-4 border-b border-border bg-surface/90 backdrop-blur-sm z-50 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-6 h-6 rounded bg-accent/20 border border-accent/40 flex items-center justify-center">
          <Network size={13} className="text-accent" />
        </div>
        <span className="font-display font-700 text-sm text-text-primary tracking-wide hidden sm:block">
          Research<span className="text-accent">Explorer</span>
        </span>
      </div>

      {/* Ingest form */}
      <form onSubmit={handleIngest} className="flex-1 flex items-center gap-2 max-w-md">
        <div className="relative flex-1">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={ingestQuery}
            onChange={e => setIngestQuery(e.target.value)}
            placeholder="Ingest papers: e.g. 'transformer attention mechanisms'"
            className="w-full bg-panel border border-border rounded-md pl-8 pr-3 py-1.5 text-xs text-text-primary placeholder-muted focus:outline-none focus:border-accent/60 transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={ingesting || !ingestQuery.trim()}
          className={clsx(
            'px-3 py-1.5 rounded-md text-xs font-medium transition-all shrink-0',
            ingesting || !ingestQuery.trim()
              ? 'bg-dim text-muted cursor-not-allowed'
              : 'bg-accent/20 text-accent border border-accent/40 hover:bg-accent/30'
          )}
        >
          {ingesting ? (
            <RefreshCw size={12} className="animate-spin" />
          ) : (
            'Ingest'
          )}
        </button>
      </form>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Status dot */}
      <button
        onClick={handleHealthCheck}
        className="flex items-center gap-1.5 text-xs text-muted hover:text-text-primary transition-colors"
        title="Check backend health"
      >
        <Cpu size={12} />
        <span className="hidden sm:block">
          {health ? (
            <span className={health.status === 'healthy' ? 'text-emerald-400' : 'text-amber-400'}>
              {health.status}
            </span>
          ) : 'status'}
        </span>
      </button>

      <a
        href="https://github.com"
        target="_blank"
        rel="noopener noreferrer"
        className="text-muted hover:text-text-primary transition-colors"
      >
        <Github size={14} />
      </a>
    </header>
  )
}
