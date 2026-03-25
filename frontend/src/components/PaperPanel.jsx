import { useEffect } from 'react'
import {
  X, ExternalLink, BookOpen, Users, Calendar,
  Hash, Star, Brain, GitCompare, Loader2, Sparkles, ChevronRight
} from 'lucide-react'
import { useStore } from '../store/index.js'
import { storeMemory } from '../services/api.js'
import toast from 'react-hot-toast'
import clsx from 'clsx'

export default function PaperPanel() {
  const {
    selectedPaper, paperSummary, summaryLoading,
    clearSelection, toggleCompare, compareList, memoryNote, setMemoryNote,
  } = useStore()

  const paper = selectedPaper
  if (!paper) return null

  const inCompare = compareList.some(p => p.id === paper.id)
  const arxivId = paper.external_ids?.arxiv
  const doi = paper.external_ids?.DOI

  async function saveToMemory() {
    if (!memoryNote.trim()) {
      toast.error('Add a note first')
      return
    }
    try {
      await storeMemory(memoryNote, paper.id, [`paper:${paper.id}`])
      toast.success('Saved to Membrain memory')
      setMemoryNote('')
    } catch {
      // handled by interceptor
    }
  }

  const fieldColors = {
    'Computer Science': 'bg-accent/15 text-accent-glow',
    'Mathematics': 'bg-emerald/15 text-emerald',
    'Physics': 'bg-blue-500/15 text-blue-400',
    'Biology': 'bg-green-500/15 text-green-400',
    'Medicine': 'bg-red-500/15 text-red-400',
  }

  return (
    <aside className="w-80 xl:w-96 shrink-0 bg-panel border-l border-border flex flex-col overflow-hidden animate-slide-in z-30">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border gap-2">
        <div className="flex-1 min-w-0">
          <h2 className="font-display font-semibold text-sm text-text-primary leading-snug line-clamp-3">
            {paper.title}
          </h2>
        </div>
        <button
          onClick={clearSelection}
          className="shrink-0 text-muted hover:text-text-primary transition-colors mt-0.5"
        >
          <X size={15} />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Metadata */}
        <div className="p-4 flex flex-col gap-3 border-b border-border">
          {/* Authors */}
          {paper.authors?.length > 0 && (
            <div className="flex items-start gap-2">
              <Users size={12} className="text-muted mt-0.5 shrink-0" />
              <p className="text-xs text-text-secondary leading-relaxed">
                {paper.authors.slice(0, 4).map(a => a.name || a).join(', ')}
                {paper.authors.length > 4 && ` +${paper.authors.length - 4}`}
              </p>
            </div>
          )}

          {/* Year + Venue */}
          <div className="flex items-center gap-3">
            {paper.year && (
              <div className="flex items-center gap-1.5">
                <Calendar size={11} className="text-muted" />
                <span className="text-xs font-mono text-text-secondary">{paper.year}</span>
              </div>
            )}
            {paper.citation_count > 0 && (
              <div className="flex items-center gap-1.5">
                <Star size={11} className="text-amber-400" />
                <span className="text-xs font-mono text-amber-400">{paper.citation_count} citations</span>
              </div>
            )}
          </div>

          {/* Fields */}
          {paper.fields?.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {paper.fields.slice(0, 4).map(f => (
                <span
                  key={f}
                  className={clsx('pill text-[10px]', fieldColors[f] || 'bg-dim text-muted')}
                >
                  {f}
                </span>
              ))}
            </div>
          )}

          {/* Links */}
          <div className="flex items-center gap-2">
            {paper.pdf_url && (
              <a
                href={paper.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[11px] text-accent hover:text-accent-glow transition-colors"
              >
                <BookOpen size={11} /> PDF
              </a>
            )}
            {arxivId && (
              <a
                href={`https://arxiv.org/abs/${arxivId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[11px] text-text-secondary hover:text-accent transition-colors"
              >
                <ExternalLink size={11} /> arXiv
              </a>
            )}
            {doi && (
              <a
                href={`https://doi.org/${doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[11px] text-text-secondary hover:text-accent transition-colors"
              >
                <Hash size={11} /> DOI
              </a>
            )}
          </div>
        </div>

        {/* Abstract */}
        {paper.abstract && (
          <div className="p-4 border-b border-border">
            <p className="text-[11px] uppercase tracking-widest text-muted font-display mb-2">Abstract</p>
            <p className="text-xs text-text-secondary leading-relaxed">{paper.abstract}</p>
          </div>
        )}

        {/* AI Summary */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={12} className="text-accent" />
            <p className="text-[11px] uppercase tracking-widest text-muted font-display">AI Summary</p>
          </div>

          {summaryLoading ? (
            <div className="flex items-center gap-2 text-xs text-muted">
              <Loader2 size={12} className="animate-spin" />
              Generating summary…
            </div>
          ) : paperSummary ? (
            <div className="flex flex-col gap-3">
              {/* TL;DR */}
              {paperSummary.tldr && (
                <div className="bg-accent/5 border border-accent/20 rounded-lg p-3">
                  <p className="text-[10px] uppercase tracking-widest text-accent mb-1.5 font-display">TL;DR</p>
                  <p className="text-xs text-text-primary leading-relaxed">{paperSummary.tldr}</p>
                </div>
              )}

              {/* Deep summary */}
              {paperSummary.deep_summary && (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-muted mb-1.5 font-display">Deep Dive</p>
                  <p className="text-xs text-text-secondary leading-relaxed">{paperSummary.deep_summary}</p>
                </div>
              )}

              {/* Key concepts */}
              {paperSummary.key_concepts?.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-muted mb-1.5 font-display">Key Concepts</p>
                  <div className="flex flex-wrap gap-1">
                    {paperSummary.key_concepts.map(c => (
                      <span key={c} className="pill bg-dim text-text-secondary text-[10px]">{c}</span>
                    ))}
                  </div>
                </div>
              )}

              {paperSummary.is_fallback && (
                <p className="text-[10px] text-muted italic">Summary generated from abstract (LLM offline)</p>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted">Summary will appear here when a paper is selected.</p>
          )}
        </div>

        {/* Memory note */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2 mb-2">
            <Brain size={12} className="text-amber-400" />
            <p className="text-[11px] uppercase tracking-widest text-muted font-display">Membrain Note</p>
          </div>
          <textarea
            value={memoryNote}
            onChange={e => setMemoryNote(e.target.value)}
            placeholder="Add a personal note about this paper…"
            rows={3}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-xs text-text-primary placeholder-muted resize-none focus:outline-none focus:border-amber-400/50 transition-colors"
          />
          <button
            onClick={saveToMemory}
            disabled={!memoryNote.trim()}
            className="mt-2 w-full py-1.5 text-xs font-medium rounded-md bg-amber-400/10 text-amber-400 border border-amber-400/30 hover:bg-amber-400/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Save to Memory
          </button>
        </div>
      </div>

      {/* Footer actions */}
      <div className="p-3 border-t border-border flex gap-2">
        <button
          onClick={() => toggleCompare(paper)}
          className={clsx(
            'flex-1 py-1.5 text-xs font-medium rounded-md flex items-center justify-center gap-1.5 transition-all',
            inCompare
              ? 'bg-emerald/15 text-emerald border border-emerald/30'
              : 'bg-dim text-text-secondary border border-border hover:border-emerald/30 hover:text-emerald'
          )}
        >
          <GitCompare size={11} />
          {inCompare ? 'In compare' : 'Compare'}
        </button>
      </div>
    </aside>
  )
}
