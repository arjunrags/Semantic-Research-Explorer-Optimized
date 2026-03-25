import { useState } from 'react'
import { AlertTriangle, RefreshCw, X, ChevronDown, ChevronUp, Network, Loader2 } from 'lucide-react'
import { useStore } from '../store/index.js'
import { triggerGapCompute } from '../services/api.js'
import toast from 'react-hot-toast'
import clsx from 'clsx'

function DensityBar({ density }) {
  const pct = Math.round(density * 100)
  const color = pct < 3 ? '#fb7185' : pct < 6 ? '#fbbf24' : '#2dd4bf'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-dim rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.max(pct * 5, 2)}%`, background: color }}
        />
      </div>
      <span className="text-[10px] font-mono" style={{ color }}>{pct}%</span>
    </div>
  )
}

function GapCard({ gap }) {
  const [expanded, setExpanded] = useState(false)
  const { setActiveTab } = useStore()

  const severity = gap.density < 0.02 ? 'critical' : gap.density < 0.04 ? 'high' : 'medium'
  const severityStyle = {
    critical: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
    high: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
    medium: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
  }

  return (
    <div className="bg-panel border border-border rounded-xl overflow-hidden hover:border-rose-400/20 transition-colors">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full text-left p-4"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={clsx('pill text-[10px]', severityStyle[severity])}>
                {severity} gap
              </span>
              <span className="text-[10px] text-muted font-mono">{gap.community_size} papers</span>
            </div>
            <h3 className="text-sm font-medium text-text-primary leading-snug">{gap.title}</h3>
          </div>
          {expanded ? <ChevronUp size={14} className="text-muted shrink-0 mt-1" /> : <ChevronDown size={14} className="text-muted shrink-0 mt-1" />}
        </div>

        <div className="mt-3">
          <p className="text-[10px] text-muted mb-1 font-display uppercase tracking-wider">Connectivity density</p>
          <DensityBar density={gap.density} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-border/50 pt-3 flex flex-col gap-3">
          {gap.explanation && (
            <div>
              <p className="text-[10px] text-muted font-display uppercase tracking-wider mb-1.5">Analysis</p>
              <p className="text-xs text-text-secondary leading-relaxed">{gap.explanation}</p>
            </div>
          )}

          {gap.paper_ids?.length > 0 && (
            <div>
              <p className="text-[10px] text-muted font-display uppercase tracking-wider mb-1.5">
                Papers in cluster ({gap.paper_ids.length})
              </p>
              <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                {gap.paper_ids.slice(0, 12).map(id => (
                  <span key={id} className="pill bg-dim text-muted text-[10px] font-mono">
                    {id.slice(0, 12)}…
                  </span>
                ))}
                {gap.paper_ids.length > 12 && (
                  <span className="pill bg-dim text-muted text-[10px]">+{gap.paper_ids.length - 12}</span>
                )}
              </div>
            </div>
          )}

          <button
            onClick={() => setActiveTab('graph')}
            className="flex items-center gap-2 text-xs text-accent hover:text-accent-glow transition-colors"
          >
            <Network size={12} /> Explore in graph
          </button>

          {gap.computed_at && (
            <p className="text-[10px] text-muted/60">
              Computed: {new Date(gap.computed_at).toLocaleDateString()}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function GapsPanel({ onRefresh }) {
  const { gaps, setActiveTab } = useStore()
  const [computing, setComputing] = useState(false)

  async function handleCompute() {
    setComputing(true)
    try {
      await triggerGapCompute()
      toast.success('Gap detection queued – results will update in a few minutes')
      setTimeout(onRefresh, 5000)
    } catch {
      // handled
    } finally {
      setComputing(false)
    }
  }

  return (
    <div className="h-full flex flex-col p-6 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="font-display font-semibold text-lg text-text-primary flex items-center gap-2">
            <AlertTriangle size={18} className="text-rose-400" />
            Research Gaps
          </h2>
          <p className="text-xs text-muted mt-0.5">Low-density graph communities · Louvain clustering</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCompute}
            disabled={computing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded-lg hover:bg-rose-500/20 transition-all disabled:opacity-50"
          >
            {computing ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
            Recompute
          </button>
          <button onClick={() => setActiveTab('graph')} className="text-muted hover:text-text-primary transition-colors">
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-2 bg-rose-500/5 border border-rose-500/15 rounded-xl p-3 mb-5 text-xs text-text-secondary leading-relaxed">
        <AlertTriangle size={12} className="text-rose-400 shrink-0 mt-0.5" />
        <span>
          Gaps are identified by computing edge density within graph communities.
          Low-density clusters (&lt;{(0.05 * 100).toFixed(0)}% connectivity) indicate sparse, underexplored research areas.
        </span>
      </div>

      {/* Gap list */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-2">
        {gaps.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-4">
              <AlertTriangle size={24} className="text-rose-400" />
            </div>
            <p className="text-sm text-muted mb-1">No gaps detected yet</p>
            <p className="text-xs text-muted/60 max-w-xs mb-4">
              Ingest papers and build the graph, then click Recompute to run community detection.
            </p>
            <button
              onClick={handleCompute}
              disabled={computing}
              className="px-4 py-2 text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded-lg hover:bg-rose-500/20 transition-all disabled:opacity-50"
            >
              {computing ? 'Computing…' : 'Run Gap Detection'}
            </button>
          </div>
        ) : (
          <>
            <p className="text-xs text-muted font-mono mb-1">{gaps.length} gap region{gaps.length !== 1 ? 's' : ''} detected</p>
            {gaps.map((gap) => (
              <GapCard key={gap.id} gap={gap} />
            ))}
          </>
        )}
      </div>
    </div>
  )
}
