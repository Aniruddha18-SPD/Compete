import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Run } from '../api'

export default function ReportsList() {
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  const load = () => api.runs().then(setRuns).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    setCreating(true)
    try { await api.createMockRun(); await load() }
    finally { setCreating(false) }
  }

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '36px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.5px' }}>Compete Reports</h1>
          <p style={{ color: 'var(--muted)', marginTop: 4, fontSize: 13 }}>
            Travel AI benchmark · Mindtrip vs Wanderboat · 20 prompts · 5 capability buckets
          </p>
        </div>
        <button onClick={handleCreate} disabled={creating} style={{
          marginLeft: 'auto', background: 'var(--mindtrip)', color: '#fff',
          padding: '7px 16px', borderRadius: 8, fontWeight: 600, fontSize: 13,
          opacity: creating ? 0.6 : 1,
        }}>
          {creating ? 'Creating…' : '+ New Run'}
        </button>
      </div>

      {loading ? (
        <p style={{ color: 'var(--muted)' }}>Loading…</p>
      ) : runs.length === 0 ? (
        <Empty onCreate={handleCreate} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {runs.map((run, i) => <RunCard key={run.id} run={run} isLatest={i === 0} />)}
        </div>
      )}
    </div>
  )
}

function RunCard({ run, isLatest }: { run: Run; isLatest: boolean }) {
  const date = run.created_at ? new Date(run.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
  }) : '—'

  const statusColor = run.status === 'complete' ? 'var(--green)' : run.status === 'failed' ? 'var(--red)' : 'var(--yellow)'

  return (
    <Link to={`/runs/${run.id}`} style={{
      display: 'block', background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: '16px 20px',
      transition: 'border-color 0.12s',
    }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--mindtrip)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontWeight: 700, fontSize: 14 }}>{run.run_name || 'Untitled Run'}</span>
        {isLatest && (
          <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 20, background: 'rgba(79,142,247,.2)', color: 'var(--mindtrip)', letterSpacing: '0.5px' }}>LATEST</span>
        )}
        <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20, background: `${statusColor}18`, color: statusColor }}>
          {run.status}
        </span>
        <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: 12 }}>{date}</span>
        <span style={{ color: 'var(--muted)', fontSize: 16 }}>›</span>
      </div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 6, display: 'flex', gap: 16 }}>
        <span>{run.query_count} prompts</span>
        <span>qs v{run.query_set_version}</span>
        {run.result_count > 0 && <span>{run.result_count} pair results</span>}
      </div>
    </Link>
  )
}

function Empty({ onCreate }: { onCreate: () => void }) {
  return (
    <div style={{ border: '1px dashed var(--border)', borderRadius: 'var(--radius-lg)', padding: '60px', textAlign: 'center' }}>
      <p style={{ color: 'var(--muted)', marginBottom: 16 }}>No runs yet. Start with the mock dataset.</p>
      <button onClick={onCreate} style={{ background: 'var(--mindtrip)', color: '#fff', padding: '8px 20px', borderRadius: 8, fontWeight: 600 }}>
        Create Mock Run
      </button>
    </div>
  )
}
