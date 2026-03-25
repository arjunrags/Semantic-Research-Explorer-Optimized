import { useState } from 'react'
import { GitCompare, X, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { useStore } from '../store/index.js'
import { comparePapers, generateLitReview } from '../services/api.js'
import toast from 'react-hot-toast'

export default function CompareBar() {
  const { compareList, toggleCompare, clearCompare } = useStore()
  const [comparing, setComparing] = useState(false)
  const [result, setResult] = useState(null)
  const [expanded, setExpanded] = useState(false)
  const [litReview, setLitReview] = useState(null)
  const [litLoading, setLitLoading] = useState(false)

  async function handleCompare() {
    if (compareList.length !== 2) {
      toast.error('Select exactly 2 papers to compare')
      return
    }
    setComparing(true)
    setResult(null)
    setExpanded(true)
    try {
      const data = await comparePapers(compareList.map(p => p.id))
      setResult(data.comparison)
    } catch {
      // handled
    } finally {
      setComparing(false)
    }
  }

  async function handleLitReview() {
    setLitLoading(true)
    try {
      const data = await generateLitReview(compareList.map(p => p.id))
      setLitReview(data.review)
      setExpanded(true)
    } catch {
      // handled
    } finally {
      setLitLoading(false)
    }
  }

  return (
    <div className="border-t border-border bg-panel/95 backdrop-blur-sm z-40">
      {/* Expanded result */}
      {expanded && (result || litReview) && (
        <div className="max-h-48 overflow-y-auto p-4 border-b border-border">
          {result && (
            <div>
              <p className="text-[10px] uppercase tracking-widest text-muted font-display mb-2">Comparison</p>
              <p className="text-xs text-text-secondary leading-relaxed">{result}</p>
            </div>
          )}
          {litReview && (
            <div className="mt-3">
              <p className="text-[10px] uppercase tracking-widest text-muted font-display mb-2">Literature Review</p>
              <p className="text-xs text-text-secondary leading-relaxed whitespace-pre-wrap">{litReview}</p>
            </div>
          )}
        </div>
      )}

      {/* Bar */}
      <div className="flex items-center gap-3 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <GitCompare size={13} className="text-emerald shrink-0" />
          <span className="text-xs text-text-secondary font-medium">Compare mode</span>
        </div>

        <div className="flex items-center gap-2 flex-1">
          {compareList.map((paper, i) => (
            <div key={paper.id} className="flex items-center gap-1.5 bg-surface border border-emerald/20 rounded-lg px-2.5 py-1">
              <span className="text-[10px] text-emerald font-mono">{String.fromCharCode(65 + i)}</span>
              <span className="text-xs text-text-secondary truncate max-w-[140px]">{paper.title?.slice(0, 35)}…</span>
              <button
                onClick={() => toggleCompare(paper)}
                className="text-muted hover:text-rose-400 transition-colors ml-1"
              >
                <X size={10} />
              </button>
            </div>
          ))}
          {compareList.length < 2 && (
            <span className="text-[11px] text-muted italic">Select {2 - compareList.length} more paper{compareList.length === 0 ? 's' : ''} from graph…</span>
          )}
        </div>

        <div className="flex items-center gap-2 ml-auto">
          {compareList.length === 2 && (
            <>
              <button
                onClick={handleCompare}
                disabled={comparing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald/10 text-emerald border border-emerald/30 rounded-lg hover:bg-emerald/20 transition-all disabled:opacity-50"
              >
                {comparing ? <Loader2 size={11} className="animate-spin" /> : <GitCompare size={11} />}
                Compare
              </button>
              <button
                onClick={handleLitReview}
                disabled={litLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-accent/10 text-accent border border-accent/30 rounded-lg hover:bg-accent/20 transition-all disabled:opacity-50"
              >
                {litLoading ? <Loader2 size={11} className="animate-spin" /> : null}
                Lit Review
              </button>
            </>
          )}

          {(result || litReview) && (
            <button onClick={() => setExpanded(v => !v)} className="text-muted hover:text-text-primary transition-colors">
              {expanded ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            </button>
          )}

          <button
            onClick={() => { clearCompare(); setResult(null); setLitReview(null); setExpanded(false) }}
            className="text-muted hover:text-rose-400 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
