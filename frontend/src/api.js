// ── api.js ──────────────────────────────────────────────────────────────
// All backend API calls in one file using axios.
// Every component imports from here instead of writing fetch calls directly.
// ─────────────────────────────────────────────────────────────────────────
import axios from 'axios'

// Base URL for the Flask backend
const API = axios.create({
  baseURL: '',
  timeout: 10000,
})

// ── Health check ────────────────────────────────────────────────────────
export const healthCheck = () =>
  API.get('/api/health').then(res => res.data)

// ── Incidents ───────────────────────────────────────────────────────────
// Fetch the list of all incidents (latest 30)
export const fetchIncidents = () =>
  API.get('/api/incidents').then(res => res.data)

// Fetch a single incident by its ID
export const fetchIncident = (incidentId) =>
  API.get(`/api/incident/${incidentId}`).then(res => res.data)

// ── Logs ────────────────────────────────────────────────────────────────
// Fetch the activity log for a specific incident
export const fetchLogs = (incidentId) =>
  API.get(`/api/logs/${incidentId}`).then(res => res.data)

// ── Trigger ─────────────────────────────────────────────────────────────
// Trigger a new incident response — agents start running in the background
export const triggerIncident = (title, description) =>
  API.post('/api/incident/trigger', { title, description }).then(res => res.data)

// ── Assign ──────────────────────────────────────────────────────────────
// Assign a developer to an incident
export const assignIncident = (incidentId, developerName) =>
  API.patch(`/api/incident/${incidentId}/assign`, { developer_name: developerName })
    .then(res => res.data)

// ── Resolve ─────────────────────────────────────────────────────────────
// Mark an incident as resolved with human feedback
export const resolveIncident = (incidentId, payload) =>
    API.patch(`/api/incident/${incidentId}/resolve`, payload)
      .then(res => res.data)
  
  // ── Stats ──────────────────────────────────────────────────────────────
  export const fetchStats = () =>
    API.get(`/api/stats?_=${Date.now()}`).then(res => res.data)
  
  // ── Similarity ──────────────────────────────────────────────────────────
  export const fetchSimilarIncidents = (incidentId) =>
    API.get(`/api/incident/${incidentId}/similar`).then(res => res.data)
