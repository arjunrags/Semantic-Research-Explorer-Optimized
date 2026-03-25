import { useEffect, useRef, useCallback, useState } from 'react'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { useStore } from '../store/index.js'
import { cytoscapeStylesheet, buildCytoscapeElements } from '../services/cytoscapeConfig.js'
import { getSummary, fetchNeighbors } from '../services/api.js'
import { ZoomIn, ZoomOut, Maximize2, Filter, Eye, EyeOff } from 'lucide-react'
import clsx from 'clsx'

cytoscape.use(fcose)

const EDGE_TYPE_LABELS = {
  citation: { label: 'Citations', color: '#4a4a6a' },
  similarity: { label: 'Similarity', color: '#3b82f6' },
  coauthor: { label: 'Co-author', color: '#2dd4bf' },
  membrain: { label: 'Membrain', color: '#f4a261' },
}

export default function GraphCanvas() {
  const cyRef = useRef(null)
  const containerRef = useRef(null)
  const {
    graphNodes, graphEdges, gaps, selectedPaper,
    selectPaper, setSummary, setSummaryLoading,
    edgeFilter, setEdgeFilter, highlightGaps, toggleHighlightGaps,
    setSidebarOpen,
  } = useStore()

  const [tooltip, setTooltip] = useState(null)
  const [showLegend, setShowLegend] = useState(true)

  const gapPaperIds = new Set(gaps.flatMap(g => g.paper_ids || []))

  const initCy = useCallback(() => {
    if (!containerRef.current || !graphNodes.length) return

    // Destroy existing
    if (cyRef.current) cyRef.current.destroy()

    const elements = buildCytoscapeElements(graphNodes, graphEdges, gapPaperIds, edgeFilter)

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: cytoscapeStylesheet,
      layout: {
        name: 'fcose',
        animate: true,
        animationDuration: 600,
        animationEasing: 'ease-out',
        randomize: true,
        quality: 'default',
        nodeDimensionsIncludeLabels: true,
        uniformNodeDimensions: false,
        packComponents: true,
        step: 'all',
        nodeRepulsion: 4500,
        idealEdgeLength: 80,
        edgeElasticity: 0.45,
        nestingFactor: 0.1,
        gravity: 0.25,
        numIter: 2500,
        tile: true,
        tilingPaddingVertical: 10,
        tilingPaddingHorizontal: 10,
      },
      minZoom: 0.1,
      maxZoom: 4,
      wheelSensitivity: 0.3,
      boxSelectionEnabled: false,
      autounselectify: false,
    })

    // Tap on node → select paper + load summary
    cy.on('tap', 'node', async (evt) => {
      const node = evt.target
      const data = node.data()
      const paper = graphNodes.find(n => n.id === data.id)
      if (!paper) return

      selectPaper(paper)
      setSidebarOpen(true)

      // Highlight neighborhood
      cy.elements().addClass('dimmed')
      node.removeClass('dimmed').addClass('selected')
      const neighborhood = node.neighborhood().add(node)
      neighborhood.removeClass('dimmed').addClass('highlighted')
      cy.edges().removeClass('highlighted')
      node.connectedEdges().addClass('highlighted').removeClass('dimmed')

      // Load summary
      setSummaryLoading(true)
      try {
        const summary = await getSummary(paper.id)
        setSummary(summary)
      } catch {
        setSummary(null)
      } finally {
        setSummaryLoading(false)
      }
    })

    // Tap on background → deselect
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass('dimmed highlighted selected')
        selectPaper(null)
      }
    })

    // Hover tooltip
    cy.on('mouseover', 'node', (evt) => {
      const node = evt.target
      const renderedPos = node.renderedPosition()
      const d = node.data()
      node.addClass('hover')
      setTooltip({
        x: renderedPos.x + 12,
        y: renderedPos.y - 20,
        title: d.title,
        year: d.year,
        citations: d.citation_count,
        type: d.source,
      })
    })

    cy.on('mouseout', 'node', (evt) => {
      evt.target.removeClass('hover')
      setTooltip(null)
    })

    cyRef.current = cy

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [graphNodes.length, graphEdges.length, edgeFilter.join(','), highlightGaps])

  useEffect(() => {
    initCy()
  }, [initCy])

  // Fit / zoom controls
  const fitGraph = () => cyRef.current?.fit(undefined, 40)
  const zoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.3)
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.77)

  const toggleEdgeType = (type) => {
    const next = edgeFilter.includes(type)
      ? edgeFilter.filter(t => t !== type)
      : [...edgeFilter, type]
    setEdgeFilter(next)
  }

  return (
    <div className="relative w-full h-full graph-bg overflow-hidden">
      {/* Cytoscape canvas */}
      <div ref={containerRef} className="cy-container absolute inset-0" />

      {/* Empty state */}
      {graphNodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
          <div className="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-4">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <circle cx="8" cy="8" r="3" stroke="#7c6af7" strokeWidth="1.5"/>
              <circle cx="24" cy="8" r="3" stroke="#7c6af7" strokeWidth="1.5"/>
              <circle cx="16" cy="24" r="3" stroke="#7c6af7" strokeWidth="1.5"/>
              <line x1="10.5" y1="9.5" x2="21.5" y2="9.5" stroke="#7c6af7" strokeWidth="1" strokeDasharray="2 2"/>
              <line x1="9" y1="11" x2="14.5" y2="21.5" stroke="#7c6af7" strokeWidth="1" strokeDasharray="2 2"/>
              <line x1="23" y1="11" x2="17.5" y2="21.5" stroke="#7c6af7" strokeWidth="1" strokeDasharray="2 2"/>
            </svg>
          </div>
          <p className="text-text-secondary text-sm font-body mb-1">No papers in graph yet</p>
          <p className="text-muted text-xs max-w-xs">
            Use the ingest bar above to search and import papers from Semantic Scholar or arXiv.
          </p>
        </div>
      )}

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute pointer-events-none z-30 max-w-[220px]"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className="bg-panel border border-border rounded-lg p-2.5 shadow-xl">
            <p className="text-xs text-text-primary font-medium leading-snug line-clamp-2">{tooltip.title}</p>
            <div className="flex items-center gap-2 mt-1.5">
              {tooltip.year && <span className="text-[10px] text-muted font-mono">{tooltip.year}</span>}
              {tooltip.citations > 0 && (
                <span className="text-[10px] text-accent">↗ {tooltip.citations}</span>
              )}
              {tooltip.type && (
                <span className="pill bg-dim text-muted capitalize">{tooltip.type?.replace('_', ' ')}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Controls – top right */}
      <div className="absolute top-3 right-3 flex flex-col gap-1.5 z-20">
        <button onClick={zoomIn} className="ctrl-btn" title="Zoom in"><ZoomIn size={13}/></button>
        <button onClick={zoomOut} className="ctrl-btn" title="Zoom out"><ZoomOut size={13}/></button>
        <button onClick={fitGraph} className="ctrl-btn" title="Fit graph"><Maximize2 size={13}/></button>
        <div className="w-full h-px bg-border my-0.5"/>
        <button
          onClick={toggleHighlightGaps}
          className={clsx('ctrl-btn', highlightGaps && 'text-rose-400 bg-rose-500/10')}
          title={highlightGaps ? 'Hide gap overlay' : 'Show research gaps'}
        >
          {highlightGaps ? <Eye size={13}/> : <EyeOff size={13}/>}
        </button>
      </div>

      {/* Legend + edge filters – bottom left */}
      <div className="absolute bottom-3 left-3 z-20">
        <button
          onClick={() => setShowLegend(v => !v)}
          className="ctrl-btn mb-1.5 w-auto px-2 gap-1 flex items-center"
        >
          <Filter size={11}/> <span className="text-[10px]">Legend</span>
        </button>

        {showLegend && (
          <div className="bg-panel/90 backdrop-blur-sm border border-border rounded-lg p-2.5 flex flex-col gap-1.5 animate-fade-up">
            {Object.entries(EDGE_TYPE_LABELS).map(([type, { label, color }]) => (
              <button
                key={type}
                onClick={() => toggleEdgeType(type)}
                className={clsx(
                  'flex items-center gap-2 text-[11px] transition-opacity',
                  edgeFilter.includes(type) ? 'opacity-100' : 'opacity-35'
                )}
              >
                <span
                  className="w-4 h-0.5 rounded-full block"
                  style={{ background: color }}
                />
                <span className="text-text-secondary">{label}</span>
              </button>
            ))}

            <div className="h-px bg-border my-0.5"/>

            {/* Gap indicator */}
            <div className="flex items-center gap-2 text-[11px]">
              <span className="w-4 h-0.5 rounded-full block border border-dashed border-rose-400"/>
              <span className="text-text-secondary">Research gap</span>
            </div>

            {/* Membrain indicator */}
            <div className="flex items-center gap-2 text-[11px]">
              <span className="w-3 h-3 rounded-sm border border-amber-400" style={{ boxShadow: '0 0 4px rgba(244,162,97,0.5)' }}/>
              <span className="text-text-secondary">Membrain</span>
            </div>
          </div>
        )}
      </div>

      {/* Graph stats – bottom right */}
      {graphNodes.length > 0 && (
        <div className="absolute bottom-3 right-3 z-20 text-right">
          <p className="text-[10px] text-muted font-mono">
            {graphNodes.length} nodes · {graphEdges.length} edges
          </p>
          {gaps.length > 0 && (
            <p className="text-[10px] text-rose-400 font-mono">{gaps.length} gap regions</p>
          )}
        </div>
      )}

      <style>{`
        .ctrl-btn {
          width: 28px; height: 28px;
          border-radius: 6px;
          background: rgba(17,17,28,0.85);
          border: 1px solid #1e1e2e;
          color: #9090aa;
          display: flex; align-items: center; justify-content: center;
          cursor: pointer; transition: all 0.15s; backdrop-filter: blur(8px);
        }
        .ctrl-btn:hover { background: #1e1e2e; color: #e8e8f0; }
        .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
      `}</style>
    </div>
  )
}
