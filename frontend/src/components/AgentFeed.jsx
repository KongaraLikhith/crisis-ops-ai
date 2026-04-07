// ── AgentFeed.jsx ───────────────────────────────────────────────────────
// Live activity log. Shows log entries as coloured cards — each agent
// has its own colour. Polls GET /api/logs/:id every 2 seconds while
// incident status is "processing" or "agents_done". Stops when resolved.
// ─────────────────────────────────────────────────────────────────────────
import { useState, useEffect, useRef } from 'react'
import { fetchLogs } from '../api'

// Colour mapping per agent name
const AGENT_COLORS = {
  Commander: { dot: '#7F77DD', bg: '#f0eeff' },
  Triage:    { dot: '#1D9E75', bg: '#edfdf6' },
  Comms:     { dot: '#EF9F27', bg: '#fef9ee' },
  Docs:      { dot: '#378ADD', bg: '#eef5ff' },
}

// Fallback mock logs when backend is not available
const MOCK_LOGS = [
  { id: 1, agent: 'Commander', action: 'Severity classified', detail: 'P0', created_at: new Date().toISOString() },
  { id: 2, agent: 'Triage', action: 'History searched', detail: 'Found 3 similar incidents', created_at: new Date().toISOString() },
  { id: 3, agent: 'Triage', action: 'Analysis complete', detail: 'Root cause: ORM pool exhausted under load', created_at: new Date().toISOString() },
  { id: 4, agent: 'Comms', action: 'Slack alert sent', detail: 'Message posted to #incidents', created_at: new Date().toISOString() },
  { id: 5, agent: 'Docs', action: 'Post-mortem drafted', detail: 'Document saved', created_at: new Date().toISOString() },
]

function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function AgentFeed({ incidentId, incidentStatus }) {
  const [logs, setLogs] = useState([])
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!incidentId) return

    // Initial fetch
    const loadLogs = async () => {
      try {
        const data = await fetchLogs(incidentId)
        setLogs(data)
      } catch {
        // Fallback to mock data if backend isn't running
        setLogs(MOCK_LOGS)
      }
    }
    loadLogs()

    // Poll every 2s while agents are still running
    const shouldPoll = incidentStatus === 'processing' || incidentStatus === 'in_triage' || incidentStatus === 'agents_done'
    if (!shouldPoll) return

    const interval = setInterval(loadLogs, 2000)
    return () => clearInterval(interval)
  }, [incidentId, incidentStatus])

  // Auto-scroll to the latest entry
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs.length])

  if (logs.length === 0) {
    return (
      <p className="text-xs text-gray-400 text-center py-6">
        Waiting for agent activity…
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-1.5 overflow-y-auto max-h-64 pr-1">
      {logs.map(log => {
        const palette = AGENT_COLORS[log.agent] || { dot: '#888', bg: '#f5f5f5' }
        return (
          <div
            key={log.id}
            className="flex items-start gap-2.5 rounded-lg px-3 py-2"
            style={{ backgroundColor: palette.bg }}
          >
            {/* Coloured dot */}
            <span
              className="w-2 h-2 rounded-full mt-1 shrink-0"
              style={{ backgroundColor: palette.dot }}
            />
            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold" style={{ color: palette.dot }}>
                  {log.agent}
                </span>
                <span className="text-[10px] text-gray-400">
                  {formatTime(log.created_at)}
                </span>
              </div>
              <p className="text-[12px] text-gray-700 font-medium">{log.action}</p>
              {log.detail && (
                <p className="text-[11px] text-gray-500 truncate">{log.detail}</p>
              )}
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
