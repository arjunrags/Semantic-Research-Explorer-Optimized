import { useEffect } from 'react'
import { useStore } from './store/index.js'
import { fetchGraph, fetchGaps } from './services/api.js'
import Topbar from './components/Topbar.jsx'
import Sidebar from './components/Sidebar.jsx'
import GraphCanvas from './components/GraphCanvas.jsx'
import PaperPanel from './components/PaperPanel.jsx'
import SearchPanel from './components/SearchPanel.jsx'
import GapsPanel from './components/GapsPanel.jsx'
import MemoryPanel from './components/MemoryPanel.jsx'
import CompareBar from './components/CompareBar.jsx'
import toast from 'react-hot-toast'

export default function App() {
  const {
    setGraphData, setGaps, activeTab,
    graphNodes, graphEdges, selectedPaper, compareList,
  } = useStore()

  useEffect(() => {
    loadGraph()
    loadGaps()
  }, [])

  async function loadGraph() {
    try {
      const data = await fetchGraph(150)
      setGraphData(data.nodes || [], data.edges || [])
    } catch {
      toast.error('Could not load graph – is the backend running?')
    }
  }

  async function loadGaps() {
    try {
      const data = await fetchGaps()
      setGaps(data.gaps || [])
    } catch { /* silent */ }
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-void">
      <Topbar onReloadGraph={loadGraph} />

      <div className="flex flex-1 overflow-hidden relative">
        {/* Left sidebar – nav tabs */}
        <Sidebar />

        {/* Main content area */}
        <main className="flex-1 relative overflow-hidden">
          {/* Graph is always mounted; other panels overlay it */}
          <GraphCanvas />

          {activeTab === 'search' && (
            <div className="absolute inset-0 z-10 bg-void/95 backdrop-blur-sm">
              <SearchPanel />
            </div>
          )}

          {activeTab === 'gaps' && (
            <div className="absolute inset-0 z-10 bg-void/95 backdrop-blur-sm">
              <GapsPanel onRefresh={loadGaps} />
            </div>
          )}

          {activeTab === 'memory' && (
            <div className="absolute inset-0 z-10 bg-void/95 backdrop-blur-sm">
              <MemoryPanel />
            </div>
          )}
        </main>

        {/* Right panel – paper details */}
        {selectedPaper && <PaperPanel />}
      </div>

      {/* Compare bar */}
      {compareList.length > 0 && <CompareBar />}
    </div>
  )
}
