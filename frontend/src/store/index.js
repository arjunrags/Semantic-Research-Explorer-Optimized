import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // ─── Graph data ────────────────────────────────────────────────────────────
  graphNodes: [],
  graphEdges: [],
  gaps: [],
  setGraphData: (nodes, edges) => set({ graphNodes: nodes, graphEdges: edges }),
  setGaps: (gaps) => set({ gaps }),

  // ─── Selected paper ────────────────────────────────────────────────────────
  selectedPaper: null,
  paperSummary: null,
  summaryLoading: false,
  selectPaper: (paper) => set({ selectedPaper: paper, paperSummary: null }),
  clearSelection: () => set({ selectedPaper: null, paperSummary: null }),
  setSummary: (summary) => set({ paperSummary: summary }),
  setSummaryLoading: (v) => set({ summaryLoading: v }),

  // ─── Search ────────────────────────────────────────────────────────────────
  searchQuery: '',
  searchResults: [],
  searchLoading: false,
  setSearchQuery: (q) => set({ searchQuery: q }),
  setSearchResults: (r) => set({ searchResults: r }),
  setSearchLoading: (v) => set({ searchLoading: v }),

  // ─── UI state ──────────────────────────────────────────────────────────────
  sidebarOpen: false,
  activeTab: 'graph',     // graph | search | gaps | memory
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  setActiveTab: (t) => set({ activeTab: t }),

  // ─── Compare mode ──────────────────────────────────────────────────────────
  compareList: [],
  toggleCompare: (paper) => {
    const { compareList } = get()
    const exists = compareList.find(p => p.id === paper.id)
    if (exists) {
      set({ compareList: compareList.filter(p => p.id !== paper.id) })
    } else if (compareList.length < 2) {
      set({ compareList: [...compareList, paper] })
    }
  },
  clearCompare: () => set({ compareList: [] }),

  // ─── Memory notes ──────────────────────────────────────────────────────────
  memoryNote: '',
  setMemoryNote: (v) => set({ memoryNote: v }),

  // ─── Graph filter ──────────────────────────────────────────────────────────
  edgeFilter: ['citation', 'similarity', 'membrain'],
  highlightGaps: false,
  setEdgeFilter: (f) => set({ edgeFilter: f }),
  toggleHighlightGaps: () => set((s) => ({ highlightGaps: !s.highlightGaps })),
}))
