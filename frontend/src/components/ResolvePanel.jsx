// ── ResolvePanel.jsx ────────────────────────────────────────────────────
// Only visible when incident status is "assigned".
// Shows the agent's root cause for reference, asks if it was correct,
// collects human resolution steps, and calls PATCH resolve API.
// ─────────────────────────────────────────────────────────────────────────
import { useState } from 'react'
import { resolveIncident } from '../api'

export default function ResolvePanel({ incident, onResolved }) {
  const [resolvedBy, setResolvedBy]           = useState('')
  const [agentWasCorrect, setAgentCorrect]    = useState(null)   // true / false / null
  const [humanRootCause, setHumanRootCause]   = useState('')
  const [humanResolution, setHumanResolution] = useState('')
  const [submitting, setSubmitting]           = useState(false)

  const canSubmit = resolvedBy && agentWasCorrect !== null && humanResolution

  const handleResolve = async () => {
    if (!canSubmit) return
    setSubmitting(true)
    try {
      await resolveIncident(incident.id, {
        resolved_by:       resolvedBy,
        agent_was_correct: agentWasCorrect,
        human_root_cause:  agentWasCorrect ? null : humanRootCause,
        human_resolution:  humanResolution,
      })
      onResolved()                 // tell parent to refresh incident
    } catch {
      console.error('Failed to resolve')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="rounded-xl border border-[#e5e3dc] bg-white p-4 mt-3 space-y-3">
      <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">
        Resolve Incident
      </p>

      {/* Agent's suggestion — shown for reference */}
      <div className="rounded-lg border-l-[3px] border-l-[#7F77DD] bg-[#f0eeff] p-3">
        <p className="text-[10px] font-semibold text-[#7F77DD] mb-1">
          Agent's root cause suggestion
        </p>
        <p className="text-[12px] text-gray-700">
          {incident.agent_root_cause || 'Not available'}
        </p>
        <p className="text-[10px] font-semibold text-[#7F77DD] mt-2 mb-1">
          Agent's suggested fix
        </p>
        <p className="text-[12px] text-gray-700">
          {incident.agent_resolution || 'Not available'}
        </p>
      </div>

      {/* Was the agent correct? */}
      <div>
        <p className="text-[12px] font-medium text-gray-700 mb-2">
          Was the agent's root cause correct?
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => { setAgentCorrect(true); setHumanRootCause('') }}
            className={`
              flex-1 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer
              ${agentWasCorrect === true
                ? 'border-2 border-[#1D9E75] bg-[#e6f7f1] text-[#0F6E56]'
                : 'border border-[#e5e3dc] bg-white text-gray-500 hover:border-[#1D9E75]'
              }
            `}
          >
            ✓ Yes — agent was right
          </button>
          <button
            onClick={() => setAgentCorrect(false)}
            className={`
              flex-1 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer
              ${agentWasCorrect === false
                ? 'border-2 border-[#c53030] bg-[#fde8e8] text-[#c53030]'
                : 'border border-[#e5e3dc] bg-white text-gray-500 hover:border-[#c53030]'
              }
            `}
          >
            ✗ No — actual cause was different
          </button>
        </div>
      </div>

      {/* Only show if agent was WRONG — collect actual root cause */}
      {agentWasCorrect === false && (
        <div>
          <label className="text-[12px] font-medium text-gray-700 block mb-1">
            Actual root cause
          </label>
          <textarea
            value={humanRootCause}
            onChange={e => setHumanRootCause(e.target.value)}
            placeholder="What actually caused this incident?"
            rows={2}
            className="w-full text-xs px-2.5 py-2 rounded-lg border border-[#e5e3dc] resize-none focus:outline-none focus:border-[#7F77DD] placeholder:text-gray-400"
          />
        </div>
      )}

      {/* Resolution steps — always required */}
      <div>
        <label className="text-[12px] font-medium text-gray-700 block mb-1">
          What steps did you take to fix it?
        </label>
        <textarea
          value={humanResolution}
          onChange={e => setHumanResolution(e.target.value)}
          placeholder={"1. Restarted the auth service\n2. Added the missing env var\n3. Verified logins working"}
          rows={4}
          className="w-full text-xs px-2.5 py-2 rounded-lg border border-[#e5e3dc] resize-none focus:outline-none focus:border-[#7F77DD] placeholder:text-gray-400"
        />
      </div>

      {/* Name input */}
      <div>
        <label className="text-[12px] font-medium text-gray-700 block mb-1">
          Your name
        </label>
        <input
          value={resolvedBy}
          onChange={e => setResolvedBy(e.target.value)}
          placeholder="e.g. Rahul"
          className="w-full text-xs px-2.5 py-2 rounded-lg border border-[#e5e3dc] focus:outline-none focus:border-[#7F77DD] placeholder:text-gray-400"
        />
      </div>

      {/* Submit button */}
      <button
        onClick={handleResolve}
        disabled={!canSubmit || submitting}
        className={`
          w-full py-2.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer
          ${canSubmit && !submitting
            ? 'bg-[#1D9E75] text-white hover:bg-[#178a65]'
            : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }
        `}
      >
        {submitting ? 'Saving…' : 'Mark Resolved & Save to History'}
      </button>
    </div>
  )
}
