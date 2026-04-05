// ── AssignPanel.jsx ─────────────────────────────────────────────────────
// Only visible when incident status is "agents_done".
// Shows a dropdown with team names and an orange "Assign" button.
// Calls PATCH /api/incident/:id/assign on click.
// ─────────────────────────────────────────────────────────────────────────
import { useState } from 'react'
import { assignIncident } from '../api'

// Team members for the dropdown
const TEAM = ['Rahul', 'Priya', 'Arjun', 'Dev']

export default function AssignPanel({ incidentId, onAssigned }) {
  const [selected, setSelected] = useState('')
  const [loading, setLoading]   = useState(false)

  const handleAssign = async () => {
    if (!selected) return
    setLoading(true)
    try {
      await assignIncident(incidentId, selected)
      onAssigned()                // tell parent to refresh incident
    } catch {
      console.error('Failed to assign')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-[#e5e3dc] bg-white p-3 mt-3">
      <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2">
        Assign Developer
      </p>

      <div className="flex gap-2">
        {/* Dropdown */}
        <select
          value={selected}
          onChange={e => setSelected(e.target.value)}
          className="flex-1 text-xs px-2.5 py-2 rounded-lg border border-[#e5e3dc] bg-white focus:outline-none focus:border-[#7F77DD] cursor-pointer"
        >
          <option value="">Select team member…</option>
          {TEAM.map(name => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>

        {/* Assign button */}
        <button
          onClick={handleAssign}
          disabled={!selected || loading}
          className={`
            px-4 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer
            ${selected && !loading
              ? 'bg-[#EF9F27] text-white hover:bg-[#d98e20]'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }
          `}
        >
          {loading ? 'Assigning…' : 'Assign'}
        </button>
      </div>
    </div>
  )
}
