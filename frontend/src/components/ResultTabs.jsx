// ── ResultTabs.jsx ──────────────────────────────────────────────────────
// Four tabs: Live Feed, Triage Result, Comms, Post-mortem.
// Renders the appropriate content panel based on the active tab.
// ─────────────────────────────────────────────────────────────────────────
import { useState } from 'react'
import AgentFeed from './AgentFeed'

const TABS = ['Live Feed', 'Triage', 'Comms', 'Post-mortem']

export default function ResultTabs({ incident }) {
  const [activeTab, setActiveTab] = useState('Live Feed')

  return (
    <div className="rounded-xl border border-[#e5e3dc] bg-white overflow-hidden">
      {/* Tab bar */}
      <div className="flex border-b border-[#e5e3dc]">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`
              flex-1 py-2.5 text-[12px] font-medium transition-colors cursor-pointer
              ${activeTab === tab
                ? 'text-[#7F77DD] border-b-2 border-[#7F77DD] bg-[#faf9ff]'
                : 'text-gray-500 hover:text-gray-700'
              }
            `}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-4">
        {activeTab === 'Live Feed' && (
          <AgentFeed
            incidentId={incident.id}
            incidentStatus={incident.status}
          />
        )}

        {activeTab === 'Triage' && (
          <TriageTab incident={incident} />
        )}

        {activeTab === 'Comms' && (
          <CommsTab incident={incident} />
        )}

        {activeTab === 'Post-mortem' && (
          <PostmortemTab incident={incident} />
        )}
      </div>
    </div>
  )
}


// ── Triage Tab ──────────────────────────────────────────────────────────
function TriageTab({ incident }) {
  const rootCause  = incident.agent_root_cause  || 'Waiting for Triage agent…'
  const resolution = incident.agent_resolution || 'Waiting for Triage agent…'

  return (
    <div className="space-y-4">
      {/* Root cause block */}
      <div className="rounded-lg border-l-[3px] border-l-[#1D9E75] bg-[#f0fdf8] p-3">
        <p className="text-[11px] font-semibold text-[#1D9E75] uppercase tracking-wide mb-1">
          Root Cause Analysis
        </p>
        <p className="text-[12px] text-gray-700 whitespace-pre-line leading-relaxed">
          {rootCause}
        </p>
      </div>

      {/* Resolution steps block */}
      <div className="rounded-lg border-l-[3px] border-l-[#7F77DD] bg-[#f0eeff] p-3">
        <p className="text-[11px] font-semibold text-[#7F77DD] uppercase tracking-wide mb-1">
          Recommended Resolution
        </p>
        <p className="text-[12px] text-gray-700 whitespace-pre-line leading-relaxed">
          {resolution}
        </p>
      </div>
    </div>
  )
}


// ── Comms Tab ───────────────────────────────────────────────────────────
function CommsTab({ incident }) {
  const comms = incident.agent_comms || 'Waiting for Comms agent…'

  return (
    <div className="space-y-3">
      {/* Slack-style message preview */}
      <div className="rounded-lg border-l-[3px] border-l-[#c53030] bg-[#fef8f8] p-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[#fde8e8] text-[#c53030]">
            #incidents
          </span>
          <span className="text-[10px] text-gray-400">Slack message</span>
        </div>
        <p className="text-[12px] text-gray-700 whitespace-pre-line leading-relaxed">
          {comms}
        </p>
      </div>

      {/* War room card — only for P0 */}
      {incident.severity === 'P0' && (
        <div className="rounded-lg border border-[#e5e3dc] bg-[#fafaf8] p-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm">📅</span>
            <span className="text-[11px] font-semibold text-gray-700">War Room</span>
          </div>
          <p className="text-[12px] text-gray-500">
            Google Meet link created for P0 incident coordination.
          </p>
          <p className="text-[11px] text-[#378ADD] mt-1 font-mono">
            meet.google.com/crisis-{incident.id?.toLowerCase().replace('inc-', '') || 'room'}
          </p>
        </div>
      )}
    </div>
  )
}


// ── Post-mortem Tab ─────────────────────────────────────────────────────
function PostmortemTab({ incident }) {
  const postmortem = incident.agent_postmortem || 'Waiting for Docs agent…'

  return (
    <div className="rounded-lg border border-[#e5e3dc] bg-[#fafaf8] p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm">📝</span>
        <span className="text-[11px] font-semibold text-gray-700 uppercase tracking-wide">
          Auto-Generated Post-Mortem
        </span>
      </div>
      <div className="text-[12px] text-gray-700 whitespace-pre-line leading-relaxed">
        {postmortem}
      </div>
    </div>
  )
}
