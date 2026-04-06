// ── Navbar.jsx ──────────────────────────────────────────────────────────
// Top bar with logo, pulsing red dot, and live count badges for
// P0 active, assigned, and resolved incidents.
// ─────────────────────────────────────────────────────────────────────────
export default function Navbar({ incidents }) {
  // Count badges from the incidents array
  const p0Active = incidents.filter(
    i => i.severity === 'P0' && i.status !== 'resolved'
  ).length

  const assignedCount = incidents.filter(
    i => i.status === 'assigned'
  ).length

  const resolvedCount = incidents.filter(
    i => i.status === 'resolved'
  ).length

  return (
    <nav className="flex items-center justify-between px-5 py-3 bg-white border-b border-[#e5e3dc]">
      {/* Left — logo with pulsing red dot */}
      <div className="flex items-center gap-2.5">
        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse-dot" />
        <span className="text-sm font-semibold tracking-tight text-gray-800">
          CrisisOps AI
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#f0eeff] text-[#7F77DD] font-medium">
          LIVE
        </span>
      </div>

      {/* Right — count badges */}
      <div className="flex items-center gap-3">
        {/* P0 active */}
        {p0Active > 0 && (
          <span className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full bg-[#fde8e8] text-[#c53030]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#c53030] animate-pulse-dot" />
            {p0Active} P0
          </span>
        )}

        {/* Assigned */}
        <span className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-blue-50 text-blue-700">
          {assignedCount} Assigned
        </span>

        {/* Resolved */}
        <span className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-[#e6f7f1] text-[#276749]">
          {resolvedCount} Resolved
        </span>
      </div>
    </nav>
  )
}
