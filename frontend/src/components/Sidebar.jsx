import { Network, Search, AlertTriangle, Brain, BookOpen, BarChart2 } from 'lucide-react'
import { useStore } from '../store/index.js'
import clsx from 'clsx'

const TABS = [
  { id: 'graph',  icon: Network,       label: 'Graph' },
  { id: 'search', icon: Search,        label: 'Search' },
  { id: 'gaps',   icon: AlertTriangle, label: 'Gaps' },
  { id: 'memory', icon: Brain,         label: 'Memory' },
]

export default function Sidebar() {
  const { activeTab, setActiveTab, graphNodes, graphEdges, gaps } = useStore()

  return (
    <nav className="w-12 shrink-0 flex flex-col items-center py-2 gap-1 bg-surface border-r border-border z-40">
      {TABS.map(({ id, icon: Icon, label }) => {
        const active = activeTab === id
        const badge = id === 'gaps' ? gaps.length : id === 'graph' ? graphNodes.length : null

        return (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            title={label}
            className={clsx(
              'relative w-8 h-8 rounded-lg flex items-center justify-center transition-all group',
              active
                ? 'bg-accent/20 text-accent shadow-glow-sm'
                : 'text-muted hover:text-text-primary hover:bg-dim'
            )}
          >
            <Icon size={15} />
            {badge > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-accent text-void text-[8px] font-bold flex items-center justify-center">
                {badge > 9 ? '9+' : badge}
              </span>
            )}
            {/* Tooltip */}
            <span className="absolute left-10 px-2 py-1 bg-panel border border-border rounded text-xs text-text-primary whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-50 transition-opacity">
              {label}
            </span>
          </button>
        )
      })}

      <div className="flex-1" />

      {/* Stats */}
      <div className="text-center pb-1">
        <div className="text-[9px] text-muted font-mono">{graphNodes.length}</div>
        <div className="text-[8px] text-muted/60">nodes</div>
      </div>
    </nav>
  )
}
