// Field-of-study color palette
const FIELD_COLORS = {
  'Computer Science': '#7c6af7',
  'Mathematics': '#2dd4bf',
  'Physics': '#60a5fa',
  'Biology': '#34d399',
  'Medicine': '#f87171',
  'Chemistry': '#fbbf24',
  'Engineering': '#a78bfa',
  'default': '#6b7280',
}

export const getNodeColor = (fields = []) => {
  for (const f of fields) {
    if (FIELD_COLORS[f]) return FIELD_COLORS[f]
  }
  return FIELD_COLORS.default
}

export const cytoscapeStylesheet = [
  // ── Default node ───────────────────────────────────────────────────────────
  {
    selector: 'node',
    style: {
      shape: 'round-rectangle',
      width: 'data(width)',
      height: 28,
      label: 'data(label)',
      'text-valign': 'center',
      'text-halign': 'center',
      'font-size': 11,
      'font-family': '"DM Sans", sans-serif',
      'font-weight': '400',
      color: '#e8e8f0',
      'text-wrap': 'wrap',
      'text-max-width': 'data(width)',
      'background-color': '#11111c',
      'border-width': 1.5,
      'border-color': 'data(borderColor)',
      'padding': 8,
      'transition-property': 'background-color, border-color, border-width, width',
      'transition-duration': '0.15s',
      'min-zoomed-font-size': 9,
      'text-overflow-wrap': 'anywhere',
    },
  },
  // ── Selected ────────────────────────────────────────────────────────────────
  {
    selector: 'node:selected',
    style: {
      'border-width': 2.5,
      'border-color': '#7c6af7',
      'background-color': '#1a1a2e',
      'shadow-blur': 16,
      'shadow-color': '#7c6af7',
      'shadow-opacity': 0.6,
      'shadow-offset-x': 0,
      'shadow-offset-y': 0,
    },
  },
  // ── Hover ───────────────────────────────────────────────────────────────────
  {
    selector: 'node.hover',
    style: {
      'border-width': 2,
      'border-color': '#9d8fff',
      'background-color': '#16162a',
    },
  },
  // ── Membrain node ───────────────────────────────────────────────────────────
  {
    selector: 'node[?membrain]',
    style: {
      'border-color': '#f4a261',
      'border-width': 2,
      'shadow-blur': 12,
      'shadow-color': '#f4a261',
      'shadow-opacity': 0.5,
      'shadow-offset-x': 0,
      'shadow-offset-y': 0,
    },
  },
  // ── Gap node ────────────────────────────────────────────────────────────────
  {
    selector: 'node.gap',
    style: {
      'border-color': '#fb7185',
      'border-width': 2,
      'border-style': 'dashed',
    },
  },
  // ── Dimmed (during selection) ───────────────────────────────────────────────
  {
    selector: 'node.dimmed',
    style: {
      opacity: 0.25,
    },
  },
  // ── Default edge ────────────────────────────────────────────────────────────
  {
    selector: 'edge',
    style: {
      width: 'data(width)',
      'line-color': 'data(color)',
      'target-arrow-color': 'data(color)',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.8,
      'curve-style': 'bezier',
      opacity: 0.5,
      'transition-property': 'opacity',
      'transition-duration': '0.15s',
    },
  },
  {
    selector: 'edge:selected',
    style: { opacity: 1, width: 2.5 },
  },
  {
    selector: 'edge.dimmed',
    style: { opacity: 0.06 },
  },
  {
    selector: 'edge.highlighted',
    style: { opacity: 0.9 },
  },
]

export const buildCytoscapeElements = (nodes, edges, gapPaperIds = new Set(), edgeFilter = []) => {
  const cyNodes = nodes.map(n => {
    const color = getNodeColor(n.fields || [])
    const isMembrain = false // will be set dynamically
    const isGap = gapPaperIds.has(n.id)
    const labelLen = (n.label || '').length
    const width = Math.max(100, Math.min(180, 60 + labelLen * 5.5))

    return {
      data: {
        id: n.id,
        label: n.label || n.title?.slice(0, 40) || n.id,
        title: n.title,
        year: n.year,
        citation_count: n.citation_count,
        authors: n.authors,
        fields: n.fields,
        source: n.source,
        borderColor: isGap ? '#fb7185' : color,
        nodeColor: color,
        membrain: isMembrain,
        width,
      },
      classes: isGap ? 'gap' : '',
    }
  })

  const cyEdges = edges
    .filter(e => !edgeFilter.length || edgeFilter.includes(e.type))
    .map((e, i) => {
      const colorMap = {
        citation: '#4a4a6a',
        similarity: '#3b82f6',
        coauthor: '#2dd4bf',
        membrain: '#f4a261',
      }
      return {
        data: {
          id: `e_${i}`,
          source: e.source,
          target: e.target,
          type: e.type,
          weight: e.weight || 1,
          color: colorMap[e.type] || '#4a4a6a',
          width: e.type === 'similarity' ? 1.5 : e.type === 'membrain' ? 2 : 1,
        },
      }
    })

  return [...cyNodes, ...cyEdges]
}
