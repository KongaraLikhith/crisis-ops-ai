import { useState } from 'react'
import axios from 'axios'

const BASE = 'http://localhost:8000'
const TEAM = ['Rahul', 'Priya', 'Arjun', 'Dev']   // your actual names

export default function AssignPanel({ incidentId, onAssigned }) {
  const [selected, setSelected] = useState('')

  const handleAssign = async () => {
    if (!selected) return
    await axios.patch(`${BASE}/api/incident/${incidentId}/assign`,
      { developer_name: selected })
    onAssigned(selected)
  }

  return (
    <div style={{padding:'12px',display:'flex',gap:'8px',alignItems:'center',
                 borderTop:'1px solid #eee'}}>
      <select value={selected} onChange={e => setSelected(e.target.value)}
        style={{flex:1,padding:'7px 8px',borderRadius:'8px',
                border:'1px solid #ddd',fontSize:'12px'}}>
        <option value="">Assign to...</option>
        {TEAM.map(name => <option key={name}>{name}</option>)}
      </select>
      <button onClick={handleAssign} disabled={!selected}
        style={{padding:'7px 14px',borderRadius:'8px',border:'none',
                background: selected ? '#EF9F27' : '#eee',
                color: selected ? 'white' : '#aaa',
                fontSize:'12px',fontWeight:'500',cursor:'pointer'}}>
        Assign
      </button>
    </div>
  )
}