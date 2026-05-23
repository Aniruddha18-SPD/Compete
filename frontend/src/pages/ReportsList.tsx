import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Run } from '../api'

const IN_PROGRESS = new Set(['capturing', 'judging', 'pending'])

export default function ReportsList() {
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [liveRunning, setLiveRunning] = useState(false)
  const [mockRunning, setMockRunning] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = () => api.runs().then(setRuns).finally(() => setLoading(false))

  useEffect(() => { load() }, [])

  useEffect(() => {
    const hasInProgress = runs.some(r => IN_PROGRESS.has(r.status))
    if (hasInProgress && !pollRef.current) {
      pollRef.current = setInterval(() => api.runs().then(setRuns), 8000)
    } else if (!hasInProgress && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    }
  }, [runs])

  const handleLiveRun = async () => {
    setLiveRunning(true)
    try { await api.createLiveRun(); await load() }
    finally { setLiveRunning(false) }
  }

  const handleMockRun = async () => {
    setMockRunning(true)
    try { await api.createMockRun(); await load() }
    finally { setMockRunning(false) }
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
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={handleMockRun} disabled={mockRunning || liveRunning} style={{
            padding: '6px 14px', borderRadius: 8, fontWeight: 600, fontSize: 12,
            border: '1px solid var(--border)', color: 'var(--muted)', background: 'var(--surface)',
            opacity: mockRunning || liveRunning ? 0.5 : 1,
            cursor: mockRunning || liveRunning ? 'not-allowed' : 'pointer',
          }}>
            {mockRunning ? 'Creating…' : 'Mock Run'}
          </button>
          <button onClick={handleLiveRun} disabled={liveRunning || mockRunning} style={{
            padding: '8px 20px', borderRadius: 8, fontWeight: 700, fontSize: 13,
            background: liveRunning ? 'var(--surface2)' : 'var(--mindtrip)',
            color: liveRunning ? 'var(--muted)' : '#fff',
            border: liveRunning ? '1px solid var(--border)' : 'none',
            display: 'flex', alignItems: 'center', gap: 7,
            opacity: liveRunning || mockRunning ? 0.8 : 1,
            cursor: liveRunning || mockRunning ? 'not-allowed' : 'pointer',
          }}>
            {liveRunning ? <><Spinner /> Starting live run…</> : <><span style={{ fontSize: 14 }}>▶</span> Run Live Eval</>}
          </button>
        </div>
      </div>

      {/* In-progress banner */}
      {runs.some(r => IN_PROGRESS.has(r.status)) && (
        <div style={{
          background: 'rgba(79,142,247,.08)', border: '1px solid rgba(79,142,247,.25)',
          borderRadius: 8, padding: '10px 16px', marginBottom: 20,
          display: 'flex', alignItems: 'center', gap: 10, fontSize: 13,
        }}>
          <Spinner color="var(--mindtrip)" />
          <span style={{ color: 'var(--mindtrip)', fontWeight: 600 }}>
            {runs.some(r => r.status === 'capturing') ? 'Scraping live responses…' : 'Judging responses…'}
          </span>
          <span style={{ color: 'var(--muted)' }}>Results update automatically every 8s.</span>
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--muted)' }}>Loading…</p>
      ) : runs.length === 0 ? (
        <Empty onLive={handleLiveRun} onMock={handleMockRun} liveRunning={liveRunning} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {runs.map((run, i) => <RunCard key={run.id} run={run} isLatest={i === 0} />)}
        </div>
      )}
    </div>
  )
}

function Spinner({ color = 'var(--muted)' }: { color?: string }) {
  return (
    <span style={{
      display: 'inline-block', width: 12, height: 12, borderRadius: '50%',
      border: `2px solid ${color}40`, borderTopColor: color,
      animation: 'spin 0.7s linear infinite', flexShrink: 0,
    }} />
  )
}

function RunCard({ run, isLatest }: { run: Run; isLatest: boolean }) {
  const date = run.created_at ? new Date(run.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  }) : '—'
  const statusColor = run.status === 'complete' ? 'var(--green)' : run.status === 'failed' ? 'var(--red)' : 'var(--yellow)'
  const isLive = run.run_type === 'live'

  return (
    <Link to={`/runs/${run.id}`} style={{
      display: 'block', background: 'var(--surface)',
      border: `1px solid ${isLive ? 'rgba(79,142,247,.35)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-lg)', padding: '16px 20px',
      transition: 'border-color 0.12s', textDecoration: 'none',
    }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--mindtrip)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = isLive ? 'rgba(79,142,247,.35)' : 'var(--border)')}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontWeight: 700, fontSize: 14 }}>{run.run_name || 'Untitled Run'}</span>
        {isLive && (
          <span style={{
            fontSize: 10, fontWeight: 800, padding: '2px 8px', borderRadius: 20,
            background: 'rgba(79,142,247,.2)', color: 'var(--mindtrip)', letterSpacing: '0.04em',
          }}>LIVE</span>
        )}
        {isLatest && (
          <span style={{
            fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 20,
            background: 'rgba(79,142,247,.15)', color: 'var(--mindtrip)',
          }}>LATEST</span>
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
      {IN_PROGRESS.has(run.status) && (
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--yellow)' }}>
          <Spinner color="var(--yellow)" />
          {run.status === 'capturing' ? 'Scraping live responses…' : 'Running judge…'}
        </div>
      )}
    </Link>
  )
}

function Empty({ onLive, onMock, liveRunning }: { onLive: () => void; onMock: () => void; liveRunning: boolean }) {
  return (
    <div style={{ border: '1px dashed var(--border)', borderRadius: 'var(--radius-lg)', padding: '60px 40px', textAlign: 'center' }}>
      <p style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>No runs yet</p>
      <p style={{ color: 'var(--muted)', marginBottom: 24, fontSize: 13 }}>
        Run a live eval to scrape real responses, or create a mock run to verify the pipeline.
      </p>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
        <button onClick={onLive} disabled={liveRunning} style={{
          background: 'var(--mindtrip)', color: '#fff', padding: '10px 26px',
          borderRadius: 8, fontWeight: 700, fontSize: 14,
          display: 'flex', alignItems: 'center', gap: 8,
          opacity: liveRunning ? 0.7 : 1,
        }}>
          {liveRunning ? <><Spinner color="#fff" /> Starting…</> : <><span>▶</span> Run Live Eval</>}
        </button>
        <button onClick={onMock} style={{
          background: 'var(--surface)', color: 'var(--muted)', padding: '10px 22px',
          borderRadius: 8, fontWeight: 600, fontSize: 13,
          border: '1px solid var(--border)',
        }}>Mock Run</button>
      </div>
    </div>
  )
}
