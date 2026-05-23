import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, Run } from '../api'

const INTENTS = ['Transactional', 'Itinerary', 'Personalized', 'Live Data', 'Edge Cases']
const INTENT_COLOR: Record<string, string> = {
  Transactional: 'var(--mindtrip)', Itinerary: 'var(--green)',
  Personalized: 'var(--tie)', 'Live Data': 'var(--yellow)', 'Edge Cases': 'var(--wanderboat)',
}
const IN_PROGRESS = new Set(['capturing', 'judging', 'pending'])

export default function ReportsListV2() {
  const navigate = useNavigate()
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [prompt, setPrompt] = useState('')
  const [liveRunning, setLiveRunning] = useState(false)
  const [mockRunning, setMockRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = () => api.runs().then(setRuns).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  // Auto-poll every 8s while any run is still in progress
  useEffect(() => {
    const hasInProgress = runs.some(r => IN_PROGRESS.has(r.status))
    if (hasInProgress && !pollRef.current) {
      pollRef.current = setInterval(() => api.runs().then(setRuns), 8000)
    } else if (!hasInProgress && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null } }
  }, [runs])

  const handleLiveRun = async () => {
    if (!prompt.trim()) { setError('Enter a travel prompt first.'); return }
    setError(null)
    setLiveRunning(true)
    try {
      const { run_id } = await api.createLiveRun({ prompt: prompt.trim() })
      setPrompt('')
      await load()
      navigate(`/v2/runs/${run_id}`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start live eval. Is the backend running?')
    } finally {
      setLiveRunning(false)
    }
  }

  const handleMockRun = async () => {
    setError(null)
    setMockRunning(true)
    try {
      const { run_id } = await api.createMockRun()
      await load()
      navigate(`/v2/runs/${run_id}`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create mock run.')
    } finally {
      setMockRunning(false)
    }
  }

  const published = runs.filter((_, i) => i === 0)
  const previous = runs.filter((_, i) => i > 0)
  const hasInProgress = runs.some(r => IN_PROGRESS.has(r.status))

  return (
    <div style={{ maxWidth: 780, margin: '0 auto', padding: '36px 24px' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.4px' }}>Compete Reports</h1>
          <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 3 }}>
            Mindtrip vs Wanderboat · LLM-judged · live scraping
          </p>
        </div>
        <Link to="/studio" style={{
          marginLeft: 'auto', padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 600,
          border: '1px solid var(--border)', color: 'var(--muted)', background: 'var(--surface)',
          textDecoration: 'none',
        }}>Query Studio</Link>
      </div>

      {/* Prompt input — primary feature */}
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12, padding: '20px 24px', marginBottom: 28,
      }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>
          Run Live Eval
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            type="text"
            value={prompt}
            onChange={e => { setPrompt(e.target.value); setError(null) }}
            onKeyDown={e => e.key === 'Enter' && !liveRunning && handleLiveRun()}
            placeholder="Enter a travel prompt… e.g. Best 5-day itinerary for Kyoto"
            disabled={liveRunning}
            style={{
              flex: 1, background: 'var(--surface2)', border: `1px solid ${error ? 'var(--red)' : 'var(--border)'}`,
              borderRadius: 8, padding: '10px 14px', color: 'var(--text)', fontSize: 14,
              outline: 'none',
            }}
          />
          <button
            onClick={handleLiveRun}
            disabled={liveRunning || mockRunning}
            style={{
              padding: '10px 22px', borderRadius: 8, fontWeight: 700, fontSize: 14,
              background: liveRunning ? 'var(--surface2)' : 'var(--mindtrip)',
              color: liveRunning ? 'var(--muted)' : '#fff',
              border: liveRunning ? '1px solid var(--border)' : 'none',
              display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap',
              cursor: liveRunning || mockRunning ? 'not-allowed' : 'pointer',
              opacity: liveRunning || mockRunning ? 0.8 : 1,
            }}
          >
            {liveRunning
              ? <><Spinner /> Launching…</>
              : <><span style={{ fontSize: 13 }}>▶</span> Run Live Eval</>}
          </button>
        </div>
        {error && (
          <p style={{ marginTop: 10, fontSize: 12, color: 'var(--red)' }}>{error}</p>
        )}
        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
          <p style={{ fontSize: 11, color: 'var(--muted)' }}>
            Scrapes both sites live · judges with GPT-4o-mini · ~2 min
          </p>
          <span style={{ color: 'var(--border)' }}>·</span>
          <button
            onClick={handleMockRun}
            disabled={mockRunning || liveRunning}
            style={{
              fontSize: 11, color: 'var(--muted)', background: 'none', border: 'none',
              padding: 0, cursor: mockRunning || liveRunning ? 'not-allowed' : 'pointer',
              textDecoration: 'underline', opacity: mockRunning || liveRunning ? 0.5 : 1,
            }}
          >
            {mockRunning ? 'Creating mock…' : 'or run a mock test instead'}
          </button>
        </div>
      </div>

      {/* In-progress banner */}
      {hasInProgress && (
        <div style={{
          background: 'rgba(79,142,247,.08)', border: '1px solid rgba(79,142,247,.25)',
          borderRadius: 8, padding: '10px 16px', marginBottom: 20,
          display: 'flex', alignItems: 'center', gap: 10, fontSize: 13,
        }}>
          <Spinner color="var(--mindtrip)" />
          <span style={{ color: 'var(--mindtrip)', fontWeight: 600 }}>
            {runs.some(r => r.status === 'capturing') ? 'Scraping live responses…' : 'Judging responses…'}
          </span>
          <span style={{ color: 'var(--muted)' }}>Results update automatically.</span>
          <Link
            to={`/v2/runs/${runs.find(r => IN_PROGRESS.has(r.status))?.id}`}
            style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--mindtrip)', fontWeight: 600 }}
          >
            View run →
          </Link>
        </div>
      )}

      {/* Runs list */}
      {loading ? (
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>Loading…</p>
      ) : runs.length === 0 ? (
        <div style={{ border: '1px dashed var(--border)', borderRadius: 10, padding: '48px 32px', textAlign: 'center' }}>
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>No runs yet — enter a prompt above and click Run Live Eval.</p>
        </div>
      ) : (
        <>
          <Section label="PUBLISHED VERSION">
            {published.map(run => <RunCard key={run.id} run={run} isLatest />)}
          </Section>
          {previous.length > 0 && (
            <Section label="PREVIOUS VERSIONS" collapsible>
              {previous.map(run => <RunCard key={run.id} run={run} isLatest={false} />)}
            </Section>
          )}
        </>
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

function Section({ label, children, collapsible }: { label: string; children: React.ReactNode; collapsible?: boolean }) {
  const [open, setOpen] = useState(true)
  return (
    <div style={{ marginBottom: 28 }}>
      <button
        onClick={() => collapsible && setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
          cursor: collapsible ? 'pointer' : 'default', width: '100%',
          background: 'none', border: 'none', padding: 0,
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.07em', color: 'var(--muted)', textTransform: 'uppercase' }}>
          {label}
        </span>
        {collapsible && <span style={{ color: 'var(--muted)', fontSize: 12, marginLeft: 'auto' }}>{open ? '▲' : '▼'}</span>}
        <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      </button>
      {open && <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>{children}</div>}
    </div>
  )
}

function RunCard({ run, isLatest }: { run: Run; isLatest: boolean }) {
  const date = run.created_at ? new Date(run.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  }) : '—'
  const statusColor = run.status === 'complete' ? 'var(--green)' : run.status === 'failed' ? 'var(--red)' : 'var(--yellow)'
  const isLive = run.run_type === 'live'

  return (
    <Link to={`/v2/runs/${run.id}`} style={{
      display: 'block', background: 'var(--surface)',
      border: `1px solid ${isLive ? 'rgba(79,142,247,.35)' : 'var(--border)'}`,
      borderRadius: 10, padding: '16px 20px', transition: 'border-color 0.12s', textDecoration: 'none',
    }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--mindtrip)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = isLive ? 'rgba(79,142,247,.35)' : 'var(--border)')}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <span style={{ fontWeight: 700, color: 'var(--mindtrip)', fontSize: 15 }}>Mindtrip</span>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>vs</span>
        <span style={{ fontWeight: 700, color: 'var(--wanderboat)', fontSize: 15 }}>Wanderboat</span>
        <div style={{ display: 'flex', gap: 5, marginLeft: 4, flexWrap: 'wrap' }}>
          {isLive
            ? <Chip label="LIVE" color="var(--mindtrip)" bold />
            : <Chip label="Mock" color="var(--muted)" />}
          {isLatest && <Chip label="Latest" color="var(--green)" />}
          <Chip label={run.status} color={statusColor} />
        </div>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--muted)' }}>›</span>
      </div>

      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 10 }}>
        {INTENTS.map(b => (
          <span key={b} style={{
            fontSize: 10, padding: '1px 7px', borderRadius: 20,
            background: `${INTENT_COLOR[b]}15`, color: INTENT_COLOR[b],
            border: `1px solid ${INTENT_COLOR[b]}33`, fontWeight: 500,
          }}>{b}</span>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--muted)', fontSize: 11 }}>
        <span style={{ marginRight: 4 }}>🗓</span>
        <span>Updated {date}</span>
        {run.query_count > 0 && <>
          <span style={{ marginLeft: 16, color: 'var(--border)' }}>·</span>
          <span style={{ marginLeft: 16 }}>{run.query_count} {run.query_count === 1 ? 'query' : 'queries'}</span>
        </>}
        {run.result_count > 0 && <>
          <span style={{ marginLeft: 4, color: 'var(--border)' }}>·</span>
          <span style={{ marginLeft: 4 }}>{run.result_count} results</span>
        </>}
      </div>

      {IN_PROGRESS.has(run.status) && (
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--yellow)' }}>
          <Spinner color="var(--yellow)" />
          {run.status === 'capturing' ? 'Scraping live responses…' : 'Running judge…'}
        </div>
      )}
    </Link>
  )
}

function Chip({ label, color, bold }: { label: string; color: string; bold?: boolean }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: bold ? 800 : 600, padding: '2px 7px', borderRadius: 20,
      background: `${color}18`, color, border: `1px solid ${color}33`,
      letterSpacing: bold ? '0.04em' : undefined,
    }}>{label}</span>
  )
}
