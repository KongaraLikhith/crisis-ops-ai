// ── VectorPanel.jsx ─────────────────────────────────────────────────────
// Right sidebar. Three sections:
//   1. Semantic similarity — 3 cards with similar past incidents + scores
//   2. Embedding dimensions — 5 horizontal bars (visual demo)
//   3. Knowledge base stats — 4 stat cards (hardcoded for demo)
// ─────────────────────────────────────────────────────────────────────────

// Mock similar incidents for demo
const SIMILAR_INCIDENTS = [
  { title: 'DB connection pool exhausted',              score: 0.94, severity: 'P0', confidence: 'Human verified' },
  { title: 'Redis cache eviction causing slow API',     score: 0.87, severity: 'P1', confidence: 'Human verified' },
  { title: 'Auth service 500s after deploy',            score: 0.73, severity: 'P1', confidence: 'Human corrected' },
]

// Mock embedding dimensions
const DIMENSIONS = [
  { label: 'DB / Infra',   value: 0.92 },
  { label: 'Connection',   value: 0.85 },
  { label: 'Prod Outage',  value: 0.78 },
  { label: 'Auth / Login',  value: 0.31 },
  { label: 'Payments',     value: 0.18 },
]

// Mock KB stats
const KB_STATS = [
  { label: 'Incidents indexed', value: '147' },
  { label: 'Human verified',    value: '89' },
  { label: 'Agent accuracy',    value: '72%' },
  { label: 'Query time',        value: '12ms' },
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

export default function VectorPanel() {
  return (
    <div className="space-y-3">

      {/* ── Section 1: Semantic similarity ────────────────────── */}
      <div className="rounded-xl border border-[#e5e3dc] bg-white p-3">
        <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2.5">
          Semantic Similarity
        </p>

        <div className="space-y-2">
          {SIMILAR_INCIDENTS.map((inc, i) => (
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
          {DIMENSIONS.map(dim => (
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
          {KB_STATS.map(stat => (
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
