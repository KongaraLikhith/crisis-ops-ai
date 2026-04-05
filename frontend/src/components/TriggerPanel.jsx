// ── TriggerPanel.jsx ────────────────────────────────────────────────────
// Below the incident list. Has 3 preset buttons (quick fill),
// a textarea for a custom description, and a "Trigger Incident Response"
// button that calls POST /api/incident/trigger.
// ─────────────────────────────────────────────────────────────────────────
import { useState } from 'react'
import { triggerIncident } from '../api'

// Preset scenarios for one-click triggering
const PRESETS = [
  { label: 'DB Pool Exhausted',   title: 'Production DB connection pool exhausted',   desc: 'All app servers throwing "too many connections" error. Response times > 30s.' },
  { label: 'Auth 500s',           title: 'Auth service 500s after deploy',            desc: 'Login broken for all users after latest deploy. JWT validation failing.' },
  { label: 'Payment Timeouts',    title: 'Stripe webhook timeouts',                  desc: 'Payment processing failing, order queue backing up. Webhooks timing out after 30s.' },
]

export default function TriggerPanel({ onTriggered }) {
  const [title, setTitle]       = useState('')
  const [desc, setDesc]         = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  // Fill the form from a preset
  const fillPreset = (preset) => {
    setTitle(preset.title)
    setDesc(preset.desc)
    setError('')
  }

  // Submit the incident to the backend
  const handleTrigger = async () => {
    if (!title.trim()) {
      setError('Title is required')
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await triggerIncident(title, desc)
      // Clear form and notify parent with the new incident ID
      setTitle('')
      setDesc('')
      onTriggered(data.incident_id)
    } catch (err) {
      setError('Failed to trigger — is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-3 rounded-xl border border-[#e5e3dc] bg-white p-3">
      {/* Section title */}
      <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2">
        Trigger Incident
      </p>

      {/* Preset buttons */}
      <div className="flex flex-wrap gap-1.5 mb-2.5">
        {PRESETS.map(p => (
          <button
            key={p.label}
            onClick={() => fillPreset(p)}
            className="text-[10px] font-medium px-2 py-1 rounded-lg border border-[#e5e3dc] bg-[#fafaf8] text-gray-600 hover:border-[#7F77DD] hover:text-[#7F77DD] transition-colors"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Title input */}
      <input
        type="text"
        placeholder="Incident title…"
        value={title}
        onChange={e => setTitle(e.target.value)}
        className="w-full text-xs px-2.5 py-2 rounded-lg border border-[#e5e3dc] mb-2 focus:outline-none focus:border-[#7F77DD] placeholder:text-gray-400"
      />

      {/* Description textarea */}
      <textarea
        placeholder="Optional description…"
        value={desc}
        onChange={e => setDesc(e.target.value)}
        rows={2}
        className="w-full text-xs px-2.5 py-2 rounded-lg border border-[#e5e3dc] mb-2.5 resize-none focus:outline-none focus:border-[#7F77DD] placeholder:text-gray-400"
      />

      {/* Error message */}
      {error && (
        <p className="text-[11px] text-[#c53030] mb-2">{error}</p>
      )}

      {/* Trigger button */}
      <button
        onClick={handleTrigger}
        disabled={loading}
        className={`
          w-full py-2 rounded-lg text-xs font-semibold transition-colors
          ${loading
            ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
            : 'bg-[#7F77DD] text-white hover:bg-[#6b63c7] cursor-pointer'
          }
        `}
      >
        {loading ? 'Triggering…' : 'Trigger Incident Response'}
      </button>
    </div>
  )
}
