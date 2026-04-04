import { useState, useEffect } from 'react'
import { getIncident } from './api'
import AssignPanel  from './components/AssignPanel'
import ResolvePanel from './components/ResolvePanel'

// Inside your detail view, below the tabs, add this:
function IncidentActions({ incident, onRefresh }) {
  if (incident.status === 'agents_done') {
    return <AssignPanel incidentId={incident.id} onAssigned={onRefresh} />
  }
  if (incident.status === 'assigned') {
    return <ResolvePanel incident={incident} onResolved={onRefresh} />
  }
  if (incident.status === 'resolved') {
    return (
      <div style={{padding:'12px',background:'#e6f7f1',borderRadius:'8px',
                   fontSize:'12px',color:'#0F6E56',margin:'12px 16px'}}>
        Resolved by {incident.resolved_by} · Saved to incident history
      </div>
    )
  }
  return null
}