import { useEffect, useState } from 'react'
import { api } from '../api'

type Query = { id: string; query_text: string; intent: string; domain: string; assertion_count: number }

const BUCKETS = ['transactional', 'itinerary', 'personalized', 'live_data', 'edge_case']
const BUCKET_LABEL: Record<string, string> = {
  transactional: 'Transactional', itinerary: 'Itinerary',
  personalized: 'Personalized', live_data: 'Live Data', edge_case: 'Edge Cases',
}
const BUCKET_COLOR: Record<string, string> = {
  transactional: 'var(--mindtrip)', itinerary: 'var(--green)',
  personalized: 'var(--tie)', live_data: 'var(--yellow)', edge_case: 'var(--wanderboat)',
}

export default function QueryStudio() {
  const [queries, setQueries] = useState<Query[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => { api.queries().then(qs => setQueries(qs as Query[])).finally(() => setLoading(false)) }, [])

  const filtered = queries.filter(q => {
    if (filter && q.intent !== filter) return false
    if (search && !q.query_text.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const counts = BUCKETS.reduce((acc, b) => { acc[b] = queries.filter(q => q.intent === b).length; return acc }, {} as Record<string, number>)

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px' }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.5px' }}>Query Set</h1>
        <p style={{ color: 'var(--muted)', marginTop: 4, fontSize: 13 }}>
          {queries.length} prompts · {queries.reduce((s, q) => s + (q.assertion_count || 0), 0)} assertions
        </p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {BUCKETS.map(b => {
          const c = BUCKET_COLOR[b]
          const active = filter === b
          return (
            <button key={b} onClick={() => setFilter(filter === b ? '' : b)} style={{
              padding: '5px 14px', borderRadius: 20, fontSize: 12,
              background: active ? `${c}22` : 'var(--surface)',
              color: active ? c : 'var(--muted)',
              border: `1px solid ${active ? c + '66' : 'var(--border)'}`,
              fontWeight: active ? 700 : 400,
            }}>
              {BUCKET_LABEL[b] ?? b} <span style={{ fontWeight: 700, marginLeft: 3 }}>{counts[b] || 0}</span>
            </button>
          )
        })}
      </div>

      <input type="text" placeholder="Search…" value={search} onChange={e => setSearch(e.target.value)}
        style={{ width: '100%', marginBottom: 16 }} />

      {loading ? <p style={{ color: 'var(--muted)' }}>Loading…</p> : (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
          {filtered.map((q, i) => {
            const c = BUCKET_COLOR[q.intent] ?? 'var(--muted)'
            return (
              <div key={q.id} style={{ padding: '12px 16px', borderBottom: i < filtered.length - 1 ? '1px solid var(--border)' : undefined, display: 'grid', gridTemplateColumns: '40px 1fr auto auto auto', gap: 12, alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)' }}>{q.id}</span>
                <span style={{ fontSize: 13, lineHeight: 1.4 }}>{q.query_text}</span>
                <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20, background: `${c}18`, color: c, border: `1px solid ${c}33`, whiteSpace: 'nowrap' }}>
                  {q.intent}
                </span>
                <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{q.domain}</span>
                <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{q.assertion_count} assertions</span>
              </div>
            )
          })}
          {filtered.length === 0 && <p style={{ padding: 32, textAlign: 'center', color: 'var(--muted)' }}>No queries match.</p>}
        </div>
      )}

      <div style={{ marginTop: 28, padding: '16px 18px', background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
        <p style={{ fontWeight: 600, marginBottom: 4, fontSize: 13 }}>Adding queries</p>
        <p style={{ color: 'var(--muted)', fontSize: 12, lineHeight: 1.6 }}>
          Edit <code style={{ background: 'var(--surface2)', padding: '1px 5px', borderRadius: 4, fontSize: 11 }}>backend/seed/queries.yaml</code> and restart the backend. The loader skips already-seeded queries.
        </p>
      </div>
    </div>
  )
}
