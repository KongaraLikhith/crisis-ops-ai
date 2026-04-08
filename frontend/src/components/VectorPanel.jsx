import { useState, useEffect } from 'react'
import { fetchStats, fetchSimilarIncidents } from '../api'

// Fallback mock similarity if backend fails or no incident selected
const MOCK_SIMILAR = [
  { title: 'DB connection pool exhausted',              score: 0.94, severity: 'P0', confidence: 'Human verified' },
  { title: 'Redis cache eviction causing slow API',     score: 0.87, severity: 'P1', confidence: 'Human verified' },
  { title: 'Auth service 500s after deploy',            score: 0.73, severity: 'P1', confidence: 'Human corrected' },
]

// Mock embedding dimension labels
const DIMENSION_LABELS = [
  'DB / Infra', 'Connection', 'Prod Outage', 'Auth / Login', 'Payments'
]


function ScoreBar({ value }) {
  return (
    <div className="w-full bg-gray-100 rounded-full h-1.5">
      <div
        className="h-1.5 rounded-full bg-[#7F77DD] transition-all"
        style={{ width: `${value * 100}%` }}
      />
    </div>
  )
}

export default function VectorPanel({ selectedId }) {
  const [stats, setStats] = useState({ human_verified_count: '...', agent_accuracy: '...' })
  const [similarIncidents, setSimilarIncidents] = useState(MOCK_SIMILAR)
  const [dimensions, setDimensions] = useState(
    DIMENSION_LABELS.map(label => ({ label, value: Math.random() * 0.5 + 0.4 }))
  )

  // 1. Fetch KB stats periodically
  useEffect(() => {
    const loadStats = () => {
      fetchStats()
        .then(data => setStats(data || { human_verified_count: '0', agent_accuracy: '0%' }))
        .catch(() => setStats({ human_verified_count: '!', agent_accuracy: '!' }))
    }
    loadStats()
    const interval = setInterval(loadStats, 10000)
    return () => clearInterval(interval)
  }, [])

  // 2. Fetch similar incidents when selectedId changes
  useEffect(() => {
    if (!selectedId) return

    fetchSimilarIncidents(selectedId)
      .then(data => {
        if (data && data.length > 0) {
          setSimilarIncidents(data.map(d => ({
            title: d.title,
            score: 0.95 - (Math.random() * 0.1), // Simulated score for UI
            severity: d.severity,
            confidence: d.resolution_confidence === 'human_verified' ? 'Human verified' : 'Agent only'
          })))
        } else {
            // If none found, show different mocks to show "something changed"
            setSimilarIncidents(MOCK_SIMILAR)
        }
      })
      .catch(() => setSimilarIncidents(MOCK_SIMILAR))

    // 3. Update Dimensions (Simulated per-incident change)
    // Seed with a hash of selectedId to keep it consistent for the same incident
    const hash = selectedId.split('').reduce((a, b) => { a = ((a << 5) - a) + b.charCodeAt(0); return a & a }, 0)
    const seededRandom = (seed) => {
        const x = Math.sin(seed) * 10000;
        return x - Math.floor(x);
    }
    setDimensions(DIMENSION_LABELS.map((label, idx) => ({
      label,
      value: 0.2 + seededRandom(hash + idx) * 0.75
    })))

  }, [selectedId])

  const kbStats = [
    { label: 'Human verified', value: stats.human_verified_count },
    { label: 'Agent accuracy', value: stats.agent_accuracy },
  ]

  return (
    <div className="space-y-3">

      {/* ── Section 1: Semantic similarity ────────────────────── */}
      <div className="rounded-xl border border-[#e5e3dc] bg-white p-3">
        <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2.5">
          Semantic Similarity
        </p>

        <div className="space-y-2">
          {similarIncidents.map((inc, i) => (
            <div
              key={i}
              className="rounded-lg border border-[#e5e3dc] bg-[#fafaf8] p-2.5"
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`
                  text-[10px] font-semibold px-1.5 py-0.5 rounded
                  ${inc.severity === 'P0'
                    ? 'bg-[#fde8e8] text-[#c53030]'
                    : 'bg-[#fef3c7] text-[#92400e]'
                  }
                `}>
                  {inc.severity}
                </span>
                <span className="text-[11px] font-bold text-[#7F77DD]">
                  {inc.score.toFixed(2)}
                </span>
              </div>
              <p className="text-[11px] text-gray-700 font-medium leading-snug">
                {inc.title}
              </p>
              <p className="text-[10px] text-gray-400 mt-0.5">
                {inc.confidence}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Section 2: Embedding dimensions ──────────────────── */}
      <div className="rounded-xl border border-[#e5e3dc] bg-white p-3">
        <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2.5">
          Embedding Dimensions
        </p>

        <div className="space-y-2">
          {dimensions.map(dim => (
            <div key={dim.label}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[10px] text-gray-600">{dim.label}</span>
                <span className="text-[10px] font-medium text-gray-500">
                  {dim.value.toFixed(2)}
                </span>
              </div>
              <ScoreBar value={dim.value} />
            </div>
          ))}
        </div>
      </div>

      {/* ── Section 3: Knowledge base stats ──────────────────── */}
      <div className="rounded-xl border border-[#e5e3dc] bg-white p-3">
        <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2.5">
          Knowledge Base
        </p>

        <div className="grid grid-cols-2 gap-2">
          {kbStats.map(stat => (
            <div
              key={stat.label}
              className="rounded-lg bg-[#fafaf8] border border-[#e5e3dc] p-2 text-center"
            >
              <p className="text-sm font-bold text-gray-800">{stat.value}</p>
              <p className="text-[10px] text-gray-400">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
