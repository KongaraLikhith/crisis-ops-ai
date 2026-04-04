import { useState } from 'react'
import axios from 'axios'

const BASE = 'http://localhost:8000'

export default function ResolvePanel({ incident, onResolved }) {
  const [resolvedBy, setResolvedBy]         = useState('')
  const [agentWasCorrect, setAgentCorrect]  = useState(null)   // true / false / null
  const [humanRootCause, setHumanRootCause] = useState('')
  const [humanResolution, setHumanResolution] = useState('')
  const [submitting, setSubmitting]         = useState(false)

  const handleResolve = async () => {
    if (!resolvedBy || agentWasCorrect === null || !humanResolution) return
    setSubmitting(true)
    await axios.patch(`${BASE}/api/incident/${incident.id}/resolve`, {
      resolved_by:      resolvedBy,
      agent_was_correct: agentWasCorrect,
      human_root_cause: agentWasCorrect ? null : humanRootCause,
      human_resolution: humanResolution,
    })
    setSubmitting(false)
    onResolved()
  }

  return (
    <div style={{padding:'14px',display:'flex',flexDirection:'column',gap:'12px'}}>

      {/* Agent's suggestion — shown for reference */}
      <div style={{padding:'10px',background:'#f0eeff',borderRadius:'8px',
                   borderLeft:'3px solid #7F77DD'}}>
        <div style={{fontSize:'11px',fontWeight:'500',color:'#534AB7',marginBottom:'4px'}}>
          Agent's root cause suggestion
        </div>
        <div style={{fontSize:'12px',color:'#333'}}>
          {incident.agent_root_cause || 'Not available'}
        </div>
        <div style={{fontSize:'11px',fontWeight:'500',color:'#534AB7',
                     marginTop:'8px',marginBottom:'4px'}}>
          Agent's suggested fix
        </div>
        <div style={{fontSize:'12px',color:'#333'}}>
          {incident.agent_resolution || 'Not available'}
        </div>
      </div>

      {/* Was the agent correct? */}
      <div>
        <div style={{fontSize:'12px',fontWeight:'500',marginBottom:'8px'}}>
          Was the agent's root cause correct?
        </div>
        <div style={{display:'flex',gap:'8px'}}>
          <button
            onClick={() => { setAgentCorrect(true); setHumanRootCause('') }}
            style={{
              flex:1, padding:'8px', borderRadius:'8px', cursor:'pointer',
              border: agentWasCorrect === true
                ? '2px solid #1D9E75' : '1px solid #ddd',
              background: agentWasCorrect === true ? '#e6f7f1' : 'white',
              color: agentWasCorrect === true ? '#0F6E56' : '#555',
              fontSize:'12px', fontWeight:'500'
            }}>
            Yes — agent was right
          </button>
          <button
            onClick={() => setAgentCorrect(false)}
            style={{
              flex:1, padding:'8px', borderRadius:'8px', cursor:'pointer',
              border: agentWasCorrect === false
                ? '2px solid #e53e3e' : '1px solid #ddd',
              background: agentWasCorrect === false ? '#fde8e8' : 'white',
              color: agentWasCorrect === false ? '#c53030' : '#555',
              fontSize:'12px', fontWeight:'500'
            }}>
            No — actual cause was different
          </button>
        </div>
      </div>

      {/* Only show if agent was WRONG */}
      {agentWasCorrect === false && (
        <div>
          <label style={{fontSize:'12px',fontWeight:'500',
                         display:'block',marginBottom:'4px'}}>
            Actual root cause
          </label>
          <textarea
            value={humanRootCause}
            onChange={e => setHumanRootCause(e.target.value)}
            placeholder="What actually caused this incident?"
            rows={2}
            style={{width:'100%',padding:'8px',borderRadius:'8px',
                    border:'1px solid #ddd',fontSize:'12px',resize:'vertical'}}
          />
        </div>
      )}

      {/* Always required — what steps did they actually take */}
      <div>
        <label style={{fontSize:'12px',fontWeight:'500',
                       display:'block',marginBottom:'4px'}}>
          What steps did you take to fix it?
        </label>
        <textarea
          value={humanResolution}
          onChange={e => setHumanResolution(e.target.value)}
          placeholder="1. Restarted the auth service&#10;2. Added the missing env var&#10;3. Verified logins working"
          rows={4}
          style={{width:'100%',padding:'8px',borderRadius:'8px',
                  border:'1px solid #ddd',fontSize:'12px',resize:'vertical'}}
        />
      </div>

      <div>
        <label style={{fontSize:'12px',fontWeight:'500',
                       display:'block',marginBottom:'4px'}}>
          Your name
        </label>
        <input
          value={resolvedBy}
          onChange={e => setResolvedBy(e.target.value)}
          placeholder="e.g. Rahul"
          style={{width:'100%',padding:'8px',borderRadius:'8px',
                  border:'1px solid #ddd',fontSize:'12px'}}
        />
      </div>

      <button
        onClick={handleResolve}
        disabled={submitting || !resolvedBy || agentWasCorrect === null || !humanResolution}
        style={{
          padding:'10px', borderRadius:'8px', border:'none',
          background: submitting ? '#ccc' : '#1D9E75',
          color:'white', fontSize:'13px', fontWeight:'500',
          cursor: submitting ? 'default' : 'pointer'
        }}>
        {submitting ? 'Saving...' : 'Mark as Resolved & Save to History'}
      </button>
    </div>
  )
}