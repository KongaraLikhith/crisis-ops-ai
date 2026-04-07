// ── IncidentList.jsx ────────────────────────────────────────────────────
// Left sidebar — shows one card per incident with severity badge,
// title, time-ago, and status badge. Selected card has purple left border.
// Refreshes the list every 10 seconds via parent polling.
// ─────────────────────────────────────────────────────────────────────────
import { useMemo } from 'react'

// Map severity level to badge colours
const sevStyle = {
  P0: 'bg-[#fde8e8] text-[#c53030]',
  P1: 'bg-[#fef3c7] text-[#92400e]',
  P2: 'bg-[#e6f7f1] text-[#276749]',
}

// Map status to badge colours
const statusStyle = {
  processing:  'bg-[#f0eeff] text-[#7F77DD]',
  in_triage:   'bg-[#f0eeff] text-[#7F77DD]',
  agents_done: 'bg-[#fef3c7] text-[#92400e]',
  in_progress: 'bg-blue-50 text-blue-700',
  escalated:   'bg-[#fde8e8] text-[#c53030]',
  assigned:    'bg-blue-50 text-blue-700',
  resolved:    'bg-[#e6f7f1] text-[#276749]',
}

// Nice labels for statuses
const statusLabel = {
  processing:  'Processing',
  in_triage:   'In Triage',
  agents_done: 'Agents Done',
  in_progress: 'In Progress',
  escalated:   'Escalated',
  assigned:    'Assigned',
  resolved:    'Resolved',
}

// Calculate "time ago" from a date string
function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function IncidentList({ incidents, selectedId, onSelect }) {
  // Memoize so we don't re-sort on every render
  const sorted = useMemo(
    () => [...incidents].sort((a, b) =>
      new Date(b.created_at) - new Date(a.created_at)
    ),
    [incidents]
  )

  return (
    <div className="flex flex-col gap-1.5 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 260px)' }}>
      {sorted.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-6">
          No incidents yet — trigger one below
        </p>
      )}

      {sorted.map(inc => {
        const isSelected = inc.id === selectedId
        return (
          <button
            key={inc.id}
            onClick={() => onSelect(inc.id)}
            className={`
              w-full text-left rounded-xl p-3 border transition-all
              ${isSelected
                ? 'border-l-[3px] border-l-[#7F77DD] border-[#7F77DD] bg-[#faf9ff]'
                : 'border-[#e5e3dc] bg-white hover:bg-gray-50'
              }
            `}
          >
            {/* Top row — severity badge + time ago */}
            <div className="flex items-center justify-between mb-1.5">
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${sevStyle[inc.severity] || 'bg-gray-100 text-gray-500'}`}>
                {inc.severity || '—'}
              </span>
              <span className="text-[10px] text-gray-400">
                {timeAgo(inc.created_at)}
              </span>
            </div>

            {/* Title */}
            <p className="text-[13px] font-medium text-gray-800 leading-snug mb-1.5 truncate">
              {inc.title}
            </p>

            {/* Bottom row — ID + status badge */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-400 font-mono">
                {inc.id}
              </span>
              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${statusStyle[inc.status] || 'bg-gray-100 text-gray-500'}`}>
                {statusLabel[inc.status] || inc.status}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
