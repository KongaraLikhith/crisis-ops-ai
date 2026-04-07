// ── AgentStatusRow.jsx ──────────────────────────────────────────────────
// Four cards in a row: Commander, Triage, Comms, Docs.
// Each shows the agent name and current status:
//   idle  → gray border    (before agents run)
//   running → amber pulsing border  (status = processing)
//   done  → green border + checkmark (status = agents_done or later)
// ─────────────────────────────────────────────────────────────────────────

// Agent definitions with their theme colours
const AGENTS = [
  { key: 'Commander', color: '#7F77DD', icon: '🎯' },
  { key: 'Triage',    color: '#1D9E75', icon: '🔍' },
  { key: 'Comms',     color: '#EF9F27', icon: '📢' },
  { key: 'Docs',      color: '#378ADD', icon: '📝' },
]

export default function AgentStatusRow({ incidentStatus }) {
  // Determine agent state from the incident lifecycle status
  const getState = () => {
    if (!incidentStatus || incidentStatus === 'idle') return 'idle'
    if (incidentStatus === 'processing' || incidentStatus === 'in_triage') return 'running'
    // agents_done, assigned, resolved → all agents finished
    return 'done'
  }
  const state = getState()

  return (
    <div className="grid grid-cols-4 gap-2 mb-3">
      {AGENTS.map(agent => (
        <div
          key={agent.key}
          className={`
            rounded-xl border-2 p-2.5 text-center transition-all
            ${state === 'running'
              ? 'animate-pulse-border bg-amber-50'
              : state === 'done'
                ? 'border-[#1D9E75] bg-[#f0fdf8]'
                : 'border-[#e5e3dc] bg-white'
            }
          `}
        >
          {/* Agent icon + name */}
          <div className="text-base mb-1">{agent.icon}</div>
          <p className="text-[11px] font-semibold text-gray-700">{agent.key}</p>

          {/* Status label */}
          <p className={`text-[10px] mt-1 font-medium ${
            state === 'running' ? 'text-amber-600'
              : state === 'done' ? 'text-[#1D9E75]'
              : 'text-gray-400'
          }`}>
            {state === 'running' ? 'Running…' : state === 'done' ? '✓ Done' : 'Idle'}
          </p>
        </div>
      ))}
    </div>
  )
}
