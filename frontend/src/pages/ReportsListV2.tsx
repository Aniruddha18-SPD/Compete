import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Run } from '../api'

const INTENTS = ['Transactional', 'Itinerary', 'Personalized', 'Live Data', 'Edge Cases']
const INTENT_COLOR: Record<string, string> = {
  Transactional: 'var(--mindtrip)', Itinerary: 'var(--green)',
  Personalized: 'var(--tie)', 'Live Data': 'var(--yellow)', 'Edge Cases': 'var(--wanderboat)',
}

export default function ReportsListV2() {
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

  const published = runs.filter((_, i) => i === 0)
  const previous = runs.filter((_, i) => i > 0)

  return (
    <div style={{ maxWidth: 780, margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.4px' }}>Compete Reports</h1>
          <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 3 }}>Select a report to open it.</p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <Link to="/studio" style={{
            padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 600,
            border: '1px solid var(--border)', color: 'var(--muted)', background: 'var(--surface)',
          }}>Query Studio</Link>
          <button onClick={handleCreate} disabled={creating} style={{
            padding: '6px 14px', borderRadius: 7, fontSize: 12, fontWeight: 600,
            background: 'var(--mindtrip)', color: '#fff', opacity: creating ? 0.6 : 1,
          }}>
            {creating ? 'Creating…' : '+ New Run'}
          </button>
        </div>
      </div>

      {loading ? (
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>Loading…</p>
      ) : runs.length === 0 ? (
        <EmptyState onCreate={handleCreate} />
      ) : (
        <>
          {/* Published version */}
          <Section label="PUBLISHED VERSION">
            {published.map(run => <RunCard key={run.id} run={run} isLatest />)}
          </Section>

          {/* Previous versions */}
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

function Section({ label, children, collapsible }: { label: string; children: React.ReactNode; collapsible?: boolean }) {
  const [open, setOpen] = useState(true)
  return (
    <div style={{ marginBottom: 28 }}>
      <button
        onClick={() => collapsible && setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
          cursor: collapsible ? 'pointer' : 'default', width: '100%',
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.07em', color: 'var(--muted)', textTransform: 'uppercase' }}>
          {label}
        </span>
        {collapsible && (
          <span style={{ color: 'var(--muted)', fontSize: 12, marginLeft: 'auto' }}>
            {open ? '▲' : '▼'}
          </span>
        )}
        <div style={{ flex: 1, height: 1, background: 'var(--border)', marginLeft: collapsible ? 0 : 0 }} />
      </button>
      {open && <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>{children}</div>}
    </div>
  )
}

function RunCard({ run, isLatest }: { run: Run; isLatest: boolean }) {
  const date = run.created_at ? new Date(run.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
  }) : '—'
  const statusColor = run.status === 'complete' ? 'var(--green)' : run.status === 'failed' ? 'var(--red)' : 'var(--yellow)'

  return (
    <Link to={`/v2/runs/${run.id}`} style={{
      display: 'block', background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '16px 20px', transition: 'border-color 0.12s',
    }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--mindtrip)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
    >
      {/* Title row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <span style={{ fontWeight: 700, color: 'var(--mindtrip)', fontSize: 15 }}>Mindtrip</span>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>vs</span>
        <span style={{ fontWeight: 700, color: 'var(--wanderboat)', fontSize: 15 }}>Wanderboat</span>
        <div style={{ display: 'flex', gap: 5, marginLeft: 4 }}>
          <Chip label="Published" color="var(--green)" />
          <Chip label={`v${run.query_set_version} query set`} color="var(--muted)" />
          {isLatest && <Chip label="Latest" color="var(--mindtrip)" />}
          <Chip label={run.status} color={statusColor} />
        </div>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--muted)' }}>›</span>
      </div>

      {/* Intent pills */}
      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 10 }}>
        {INTENTS.map(b => (
          <span key={b} style={{
            fontSize: 10, padding: '1px 7px', borderRadius: 20,
            background: `${INTENT_COLOR[b]}15`, color: INTENT_COLOR[b],
            border: `1px solid ${INTENT_COLOR[b]}33`, fontWeight: 500,
          }}>{b}</span>
        ))}
      </div>

      {/* Meta */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--muted)', fontSize: 11 }}>
        <span style={{ marginRight: 4 }}>🗓</span>
        <span>Updated {date}</span>
        <span style={{ marginLeft: 16, color: 'var(--border)' }}>·</span>
        <span style={{ marginLeft: 16 }}>{run.query_count} queries</span>
        {run.result_count > 0 && (
          <>
            <span style={{ marginLeft: 4, color: 'var(--border)' }}>·</span>
            <span style={{ marginLeft: 4 }}>{run.result_count} results</span>
          </>
        )}
      </div>

      <div style={{ marginTop: 10, borderTop: '1px solid var(--border)', paddingTop: 10 }}>
        <span style={{ fontSize: 11, color: 'var(--muted)', fontStyle: 'italic' }}>Release notes</span>
      </div>
    </Link>
  )
}

function Chip({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 20,
      background: `${color}18`, color, border: `1px solid ${color}33`,
    }}>{label}</span>
  )
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div style={{ border: '1px dashed var(--border)', borderRadius: 10, padding: 60, textAlign: 'center' }}>
      <p style={{ color: 'var(--muted)', marginBottom: 16, fontSize: 13 }}>No runs yet. Start with the mock dataset.</p>
      <button onClick={onCreate} style={{
        background: 'var(--mindtrip)', color: '#fff', padding: '8px 20px', borderRadius: 8, fontWeight: 600, fontSize: 13,
      }}>Create Mock Run</button>
    </div>
  )
}
