// ── App.jsx ─────────────────────────────────────────────────────────────
// Root component for CrisisOps AI dashboard.
// Holds two main state values:
//   - incidents:          list of all incidents (for sidebar + navbar)
//   - selectedIncidentId: which incident is open in the detail view
// Layout: 3-column CSS grid — left (260px) | centre (1fr) | right (270px)
// ─────────────────────────────────────────────────────────────────────────
import { useState, useEffect, useCallback } from 'react'
import { fetchIncidents, fetchIncident } from './api'

// Components
import Navbar          from './components/Navbar'
import IncidentList    from './components/IncidentList'
import TriggerPanel    from './components/TriggerPanel'
import AgentStatusRow  from './components/AgentStatusRow'
import ResultTabs      from './components/ResultTabs'
import AssignPanel     from './components/AssignPanel'
import ResolvePanel    from './components/ResolvePanel'
import VectorPanel     from './components/VectorPanel'

// ── Mock data fallback (used when backend is not running) ───────────────
const MOCK_INCIDENTS = [
  {
    id: 'INC-A1B2C3D4',
    title: 'Production DB connection pool exhausted',
    description: 'All app servers throwing "too many connections" error. Response times > 30s.',
    severity: 'P0',
    status: 'agents_done',
    agent_root_cause: 'SQLAlchemy ORM pool_size=5 is too low under production load. Analytics background job held all connections, starving the web workers.',
    agent_resolution: '1. Set pool_size=20 and max_overflow=10 in SQLAlchemy config\n2. Kill stuck queries via pg_terminate_backend()\n3. Rolling restart of all app servers\n4. Add connection pool monitoring alert',
    agent_comms: '🔴 [P0] Production DB connection pool exhausted\n\nAll app servers are throwing connection errors. Investigation in progress.\n\nIncident ID: INC-A1B2C3D4\nSeverity: P0\nAssigned: Pending\n\n— CrisisOps AI',
    agent_postmortem: '# Post-Mortem: DB Connection Pool Exhaustion\n\n## Summary\nAll application servers began throwing "too many connections" errors at 14:32 UTC, causing a full production outage lasting approximately 45 minutes.\n\n## Root Cause\nThe SQLAlchemy connection pool was configured with a default pool_size of 5. A long-running analytics background job consumed all available connections, preventing web workers from serving requests.\n\n## Timeline\n- 14:32 — First alerts fired for elevated 5xx rates\n- 14:35 — Commander agent classified as P0\n- 14:36 — Triage identified connection pool exhaustion\n- 14:40 — Pool size increased, stuck queries killed\n- 14:50 — Rolling restart completed, service restored\n\n## Action Items\n1. Increase pool_size to 20 with max_overflow=10\n2. Isolate analytics jobs on separate connection pool\n3. Add connection pool utilization monitoring\n4. Set up PagerDuty alert at 80% pool capacity',
    assigned_to: null,
    assigned_at: null,
    human_validated: null,
    human_root_cause: null,
    human_resolution: null,
    resolved_by: null,
    resolved_at: null,
    created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
  },
  {
    id: 'INC-E5F6G7H8',
    title: 'Auth service 500s after deploy',
    description: 'Login broken for all users after latest deploy. JWT validation failing.',
    severity: 'P1',
    status: 'assigned',
    agent_root_cause: 'JWT_SECRET environment variable missing in new deployment environment.',
    agent_resolution: '1. Add JWT_SECRET to production secrets manager\n2. Redeploy auth service\n3. Verify login flow for test users',
    agent_comms: '🟡 [P1] Auth service 500s after deploy\n\nLogin broken for all users. Investigating JWT validation failure.\n\nIncident ID: INC-E5F6G7H8',
    agent_postmortem: '# Post-Mortem: Auth Service 500s\n\n## Summary\nAuth service began returning 500 errors for all login requests immediately after deployment.\n\n## Root Cause\nJWT_SECRET environment variable was not propagated to the new deployment environment.',
    assigned_to: 'Rahul',
    assigned_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    human_validated: null,
    human_root_cause: null,
    human_resolution: null,
    resolved_by: null,
    resolved_at: null,
    created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
  },
  {
    id: 'INC-I9J0K1L2',
    title: 'Stripe webhook timeouts',
    description: 'Payment processing failing, order queue backing up. Webhooks timing out after 30s.',
    severity: 'P1',
    status: 'resolved',
    agent_root_cause: 'Background job queue backed up, webhooks exceeded 30s timeout.',
    agent_resolution: '1. Scale job workers from 2 to 8\n2. Add DB index on orders.created_at\n3. Monitor queue depth',
    agent_comms: '🟡 [P1] Stripe webhook timeouts\n\nPayment processing failing. Order queue backing up.',
    agent_postmortem: '# Post-Mortem: Stripe Webhook Timeouts\n\n## Summary\nStripe webhooks began timing out, causing payment processing failures.',
    assigned_to: 'Priya',
    assigned_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    human_validated: true,
    human_root_cause: null,
    human_resolution: 'Scaled job workers from 2 to 8. Added DB index on orders.created_at.',
    resolved_by: 'Priya',
    resolved_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
  },
]


export default function App() {
  // ── State ───────────────────────────────────────────────────────────
  const [incidents, setIncidents]             = useState([])
  const [selectedId, setSelectedId]           = useState(null)
  const [selectedIncident, setSelectedIncident] = useState(null)
  const [useMock, setUseMock]                 = useState(false)

  // ── Load incident list (with fallback to mock) ────────────────────
  const loadIncidents = useCallback(async () => {
    try {
      const data = await fetchIncidents()
      setIncidents(data)
      setUseMock(false)
    } catch {
      // Backend not running — use mock data
      setIncidents(MOCK_INCIDENTS)
      setUseMock(true)
    }
  }, [])

  // Initial fetch + 10s polling for the list
  useEffect(() => {
    loadIncidents()
    const interval = setInterval(loadIncidents, 10000)
    return () => clearInterval(interval)
  }, [loadIncidents])

  // ── Load selected incident detail ─────────────────────────────────
  const loadSelectedIncident = useCallback(async () => {
    if (!selectedId) { setSelectedIncident(null); return }

    if (useMock) {
      // Find from mock array
      setSelectedIncident(MOCK_INCIDENTS.find(i => i.id === selectedId) || null)
      return
    }

    try {
      const data = await fetchIncident(selectedId)
      setSelectedIncident(data)
    } catch {
      // Fallback to mock
      setSelectedIncident(MOCK_INCIDENTS.find(i => i.id === selectedId) || null)
    }
  }, [selectedId, useMock])

  useEffect(() => {
    loadSelectedIncident()
    // Poll detail every 3s while agents are running
    if (selectedIncident?.status === 'processing') {
      const interval = setInterval(loadSelectedIncident, 3000)
      return () => clearInterval(interval)
    }
  }, [selectedId, loadSelectedIncident])

  // ── Event handlers ────────────────────────────────────────────────
  const handleSelect = (id) => setSelectedId(id)

  const handleTriggered = (newId) => {
    loadIncidents()         // refresh list
    setSelectedId(newId)    // auto-select the new incident
  }

  const handleRefresh = () => {
    loadIncidents()
    loadSelectedIncident()
  }

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#f5f4f0]">
      {/* Top navbar */}
      <Navbar incidents={incidents} />

      {/* Mock data banner */}
      {useMock && (
        <div className="mx-2.5 mt-2 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-700 text-center">
          Backend offline — showing mock data
        </div>
      )}

      {/* 3-column grid layout */}
      <div
        className="grid gap-2.5 p-2.5"
        style={{ gridTemplateColumns: '260px 1fr 270px' }}
      >
        {/* ── LEFT COLUMN ────────────────────────────────────── */}
        <aside className="flex flex-col">
          {/* Section label */}
          <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2 px-1">
            Incidents
          </p>
          <IncidentList
            incidents={incidents}
            selectedId={selectedId}
            onSelect={handleSelect}
          />
          <TriggerPanel onTriggered={handleTriggered} />
        </aside>

        {/* ── CENTRE COLUMN ──────────────────────────────────── */}
        <main>
          {selectedIncident ? (
            <div className="space-y-3">
              {/* Incident header */}
              <div className="rounded-xl border border-[#e5e3dc] bg-white p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`
                    text-[10px] font-semibold px-1.5 py-0.5 rounded
                    ${selectedIncident.severity === 'P0' ? 'bg-[#fde8e8] text-[#c53030]'
                      : selectedIncident.severity === 'P1' ? 'bg-[#fef3c7] text-[#92400e]'
                      : 'bg-[#e6f7f1] text-[#276749]'
                    }
                  `}>
                    {selectedIncident.severity}
                  </span>
                  <span className="text-[10px] text-gray-400 font-mono">
                    {selectedIncident.id}
                  </span>
                </div>
                <h1 className="text-[15px] font-semibold text-gray-800 mb-1">
                  {selectedIncident.title}
                </h1>
                <p className="text-[12px] text-gray-500">
                  {selectedIncident.description}
                </p>
                {selectedIncident.assigned_to && (
                  <p className="text-[11px] text-[#378ADD] mt-2">
                    Assigned to {selectedIncident.assigned_to}
                  </p>
                )}
              </div>

              {/* Agent status row */}
              <AgentStatusRow incidentStatus={selectedIncident.status} />

              {/* Result tabs (Feed / Triage / Comms / Post-mortem) */}
              <ResultTabs incident={selectedIncident} />

              {/* Action area — context-dependent */}
              {selectedIncident.status === 'agents_done' && (
                <AssignPanel
                  incidentId={selectedIncident.id}
                  onAssigned={handleRefresh}
                />
              )}
              {selectedIncident.status === 'assigned' && (
                <ResolvePanel
                  incident={selectedIncident}
                  onResolved={handleRefresh}
                />
              )}
              {selectedIncident.status === 'resolved' && (
                <div className="rounded-xl border border-[#1D9E75] bg-[#e6f7f1] p-3 text-center">
                  <p className="text-[12px] text-[#0F6E56] font-medium">
                    ✓ Resolved by {selectedIncident.resolved_by} · Saved to incident history
                  </p>
                </div>
              )}
            </div>
          ) : (
            /* Empty state */
            <div className="flex items-center justify-center h-full text-center">
              <div>
                <p className="text-3xl mb-3">🎯</p>
                <p className="text-sm font-medium text-gray-500">
                  Select an incident or trigger a new one
                </p>
                <p className="text-[11px] text-gray-400 mt-1">
                  The detail view will appear here
                </p>
              </div>
            </div>
          )}
        </main>

        {/* ── RIGHT COLUMN ───────────────────────────────────── */}
        <aside>
          <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2 px-1">
            Vector Intelligence
          </p>
          <VectorPanel />
        </aside>
      </div>
    </div>
  )
}
