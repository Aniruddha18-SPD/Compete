import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, Run, Summary, PivotRow, PairResult } from '../api'

const MT = 'var(--mindtrip)'
const WB = 'var(--wanderboat)'
const TIE = 'var(--tie)'
const GREEN = 'var(--green)'
const RED = 'var(--red)'

const OUTCOME_COLOR: Record<string, string> = {
  mindtrip_wins: MT, wanderboat_wins: WB, both_pass: GREEN, both_fail: RED, tie: TIE,
}
const OUTCOME_LABEL: Record<string, string> = {
  mindtrip_wins: 'Mindtrip', wanderboat_wins: 'Wanderboat', both_pass: 'Both Pass', both_fail: 'Both Fail', tie: 'Tie',
}

const BUCKETS = ['Transactional', 'Itinerary', 'Personalized', 'Live Data', 'Edge Cases']
const SEGMENT2 = ['Single', 'Multi-Step', 'Comparison', 'Open-Ended', 'With-Budget']

type PivotKey = 'intent' | 'domain'

export default function PairReport() {
  const { runId } = useParams<{ runId: string }>()
  const [run, setRun] = useState<Run | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [pairs, setPairs] = useState<PairResult[]>([])
  const [pivotData, setPivotData] = useState<PivotRow[]>([])
  const [pivotBy, setPivotBy] = useState<PivotKey>('intent')
  const [filterIntent, setFilterIntent] = useState('')
  const [filterOutcome, setFilterOutcome] = useState('')
  const [search, setSearch] = useState('')
  const [view, setView] = useState<'summary' | 'table'>('summary')

  const reload = async () => {
    if (!runId) return
    const [r, s, pa, pv] = await Promise.all([
      api.run(runId), api.summary(runId), api.pairs(runId), api.pivot(runId, pivotBy),
    ])
    setRun(r); setSummary(s); setPairs(pa); setPivotData(pv)
  }
  useEffect(() => { reload() }, [runId])
  useEffect(() => { if (runId) api.pivot(runId, pivotBy).then(setPivotData) }, [pivotBy, runId])
  useEffect(() => {
    if (!run || run.status === 'complete' || run.status === 'failed') return
    const t = setTimeout(reload, 3000)
    return () => clearTimeout(t)
  }, [run])

  const filtered = pairs.filter(p => {
    if (filterIntent && p.intent !== filterIntent) return false
    if (filterOutcome && p.outcome !== filterOutcome) return false
    if (search && !p.query_text.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const outcomes = summary?.outcomes || {}
  const total = pairs.length
  const mt = outcomes['mindtrip_wins'] || 0
  const wb = outcomes['wanderboat_wins'] || 0
  const tie = (outcomes['tie'] || 0) + (outcomes['both_pass'] || 0) + (outcomes['both_fail'] || 0)
  const decisive = mt + wb
  const battleScore = decisive > 0 ? mt / decisive : 0

  const date = run?.created_at ? new Date(run.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'

  if (!run) return <div style={{ padding: 40, color: 'var(--muted)' }}>Loading…</div>

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '28px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>
          <Link to="/">← Reports</Link>
        </div>
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.5px' }}>
          Compete Eval — <span style={{ color: MT }}>Mindtrip</span> vs <span style={{ color: WB }}>Wanderboat</span>
        </h1>
        <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
          {total} prompts · 5 capability buckets · LLM judge via OpenAI gpt-4o-mini · {date}
          {run.status !== 'complete' && (
            <span style={{ marginLeft: 12, color: 'var(--yellow)', fontWeight: 600 }}>
              ⏳ {run.status}…
            </span>
          )}
        </div>
      </div>

      {/* View toggle */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24 }}>
        {(['summary', 'table'] as const).map(v => (
          <button key={v} onClick={() => setView(v)} style={{
            padding: '5px 14px', borderRadius: 6, fontSize: 13,
            fontWeight: view === v ? 600 : 400,
            background: view === v ? 'var(--surface2)' : 'transparent',
            color: view === v ? 'var(--text)' : 'var(--muted)',
            border: `1px solid ${view === v ? 'var(--border)' : 'transparent'}`,
          }}>
            {v === 'summary' ? 'Summary' : 'Prompt Table'}
          </button>
        ))}
      </div>

      {view === 'summary' ? (
        <SummaryView
          total={total} mt={mt} wb={wb} tie={tie} battleScore={battleScore}
          outcomes={outcomes} summary={summary} pairs={pairs}
          pivotData={pivotData} pivotBy={pivotBy} setPivotBy={setPivotBy}
        />
      ) : (
        <TableView
          pairs={filtered} runId={runId!}
          filterIntent={filterIntent} setFilterIntent={setFilterIntent}
          filterOutcome={filterOutcome} setFilterOutcome={setFilterOutcome}
          search={search} setSearch={setSearch}
        />
      )}
    </div>
  )
}

function SummaryView({ total, mt, wb, tie, battleScore, outcomes, summary, pairs, pivotData, pivotBy, setPivotBy }: {
  total: number; mt: number; wb: number; tie: number; battleScore: number
  outcomes: Record<string, number>; summary: Summary | null
  pairs: PairResult[]; pivotData: PivotRow[]; pivotBy: string
  setPivotBy: (v: 'intent' | 'domain') => void
}) {
  // Bucket counts from pivot data (intent pivot)
  const bucketCounts: Record<string, Record<string, number>> = {}
  pivotData.forEach(r => {
    bucketCounts[r.pivot_val] = r.outcomes
  })

  const winner = mt > wb ? 'mindtrip' : wb > mt ? 'wanderboat' : 'tie'

  return (
    <>
      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
        <Card label="Battle Score" value={`${Math.round(battleScore * 100)}%`}
          sub={`${winner === 'mindtrip' ? 'Mindtrip' : winner === 'wanderboat' ? 'Wanderboat' : 'Tied'} advantage (${Math.max(mt, wb)}/${total} wins)`}
          color="var(--text)" />
        <Card label="Mindtrip Wins" value={String(mt)}
          sub={pairs.filter(p => p.outcome === 'mindtrip_wins').map(p => p.query_id).join(', ')}
          color={MT} />
        <Card label="Wanderboat Wins" value={String(wb)}
          sub={pairs.filter(p => p.outcome === 'wanderboat_wins').map(p => p.query_id).join(', ')}
          color={WB} />
        <Card label="Ties" value={String(tie)}
          sub={pairs.filter(p => p.outcome === 'tie' || p.outcome === 'both_pass').map(p => p.query_id).join(', ') || '—'}
          color={TIE} />
      </div>

      {/* Score bar */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '18px 20px', marginBottom: 20 }}>
        <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>Overall Distribution</h2>
        <div style={{ display: 'flex', height: 36, borderRadius: 8, overflow: 'hidden' }}>
          {total > 0 && <>
            <ScoreSegment width={(mt / total) * 100} color={MT} label={`Mindtrip ${Math.round((mt / total) * 100)}%`} />
            <ScoreSegment width={(wb / total) * 100} color={WB} label={`WB ${Math.round((wb / total) * 100)}%`} />
            <ScoreSegment width={(tie / total) * 100} color={TIE} label="Tie" />
            <ScoreSegment width={((outcomes['both_fail'] || 0) / total) * 100} color={RED} label="" />
          </>}
        </div>
        <div style={{ display: 'flex', gap: 20, marginTop: 10, fontSize: 12, color: 'var(--muted)', flexWrap: 'wrap' }}>
          <LegendDot color={MT} label={`Mindtrip wins (${mt})`} />
          <LegendDot color={WB} label={`Wanderboat wins (${wb})`} />
          <LegendDot color={TIE} label={`Ties (${tie})`} />
          {summary && (
            <span style={{ marginLeft: 'auto' }}>
              MT avg pass rate {pct(summary.mindtrip_avg_pass_rate)} · WB {pct(summary.wanderboat_avg_pass_rate)}
            </span>
          )}
        </div>
      </div>

      {/* Bucket breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 20 }}>
        {BUCKETS.map(bucket => {
          const oc = bucketCounts[bucket] || {}
          const bmt = oc['mindtrip_wins'] || 0
          const bwb = oc['wanderboat_wins'] || 0
          const btie = (oc['tie'] || 0) + (oc['both_pass'] || 0) + (oc['both_fail'] || 0)
          const bmax = Math.max(bmt, bwb, btie, 1)
          return (
            <div key={bucket} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 14px' }}>
              <h3 style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)', marginBottom: 12, fontWeight: 600 }}>
                {bucket}
              </h3>
              <BucketBar label="Mindtrip" value={bmt} max={bmax} color={MT} />
              <BucketBar label="Wanderboat" value={bwb} max={bmax} color={WB} />
              <BucketBar label="Tie" value={btie} max={bmax} color={TIE} />
            </div>
          )
        })}
      </div>

      {/* Thesis */}
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderLeft: `3px solid ${MT}`, borderRadius: 'var(--radius-lg)',
        padding: '16px 20px', marginBottom: 20,
      }}>
        <h2 style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Key Finding</h2>
        <p style={{ fontSize: 14 }}>
          <strong style={{ color: MT }}>Mindtrip</strong> leads on transactional and itinerary queries where specificity wins — flight details, hotel names, concrete day-by-day plans. <strong style={{ color: WB }}>Wanderboat</strong> performs better on personalized and edge-case queries where opinionated reasoning matters more than data density. Both products struggle on live-data queries where ground truth is hard to verify.
        </p>
      </div>

      {/* Per-prompt pivot table */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>By</span>
          <select value={pivotBy} onChange={e => setPivotBy(e.target.value as 'intent' | 'domain')}>
            <option value="intent">Bucket (Intent)</option>
            <option value="domain">Query Type (Domain)</option>
          </select>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--surface2)' }}>
              {['', 'Queries', 'MT Pass Rate', 'WB Pass Rate', 'Distribution'].map(h => (
                <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)', fontWeight: 600, borderBottom: '1px solid var(--border)' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pivotData.map(r => (
              <tr key={r.pivot_val} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '10px 16px', fontWeight: 700, fontSize: 13 }}>{r.pivot_val}</td>
                <td style={{ padding: '10px 16px', color: 'var(--muted)', fontSize: 13 }}>{r.query_count}</td>
                <td style={{ padding: '10px 16px' }}>
                  <span style={{ color: MT, fontWeight: 700 }}>{pct(r.mindtrip_pass_rate)}</span>
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <span style={{ color: WB, fontWeight: 700 }}>{pct(r.wanderboat_pass_rate)}</span>
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <MiniDistBar outcomes={r.outcomes} total={r.query_count} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

function TableView({ pairs, runId, filterIntent, setFilterIntent, filterOutcome, setFilterOutcome, search, setSearch }: {
  pairs: PairResult[]; runId: string
  filterIntent: string; setFilterIntent: (v: string) => void
  filterOutcome: string; setFilterOutcome: (v: string) => void
  search: string; setSearch: (v: string) => void
}) {
  const [expanded, setExpanded] = useState<string | null>(null)

  const exportCSV = () => {
    const rows = [['ID', 'Prompt', 'Bucket', 'Type', 'Outcome', 'MT Pass Rate', 'WB Pass Rate']]
    pairs.forEach(p => rows.push([p.query_id, p.query_text, p.intent, p.domain, p.outcome,
      pct(p.mindtrip_pass_rate), pct(p.wanderboat_pass_rate)]))
    const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = 'compete-results.csv'; a.click()
  }

  return (
    <>
      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
        <input type="text" placeholder="Search prompts…" value={search} onChange={e => setSearch(e.target.value)} style={{ flex: 1 }} />
        <select value={filterIntent} onChange={e => setFilterIntent(e.target.value)}>
          <option value="">All buckets</option>
          {BUCKETS.map(b => <option key={b} value={b}>{b}</option>)}
        </select>
        <select value={filterOutcome} onChange={e => setFilterOutcome(e.target.value)}>
          <option value="">All outcomes</option>
          {Object.entries(OUTCOME_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        {(filterIntent || filterOutcome || search) && (
          <button onClick={() => { setFilterIntent(''); setFilterOutcome(''); setSearch('') }}
            style={{ color: 'var(--muted)', fontSize: 12 }}>Clear</button>
        )}
        <button onClick={exportCSV} style={{ padding: '6px 12px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12, color: 'var(--muted)' }}>
          Export CSV
        </button>
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--surface2)' }}>
              {['ID', 'Prompt', 'Bucket', 'Difficulty', 'Verdict', 'Pass Rates', 'Match'].map(h => (
                <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)', fontWeight: 600, borderBottom: '1px solid var(--border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pairs.map(p => (
              <>
                <tr key={p.id}
                  onClick={() => setExpanded(expanded === p.id ? null : p.id)}
                  style={{ borderBottom: expanded === p.id ? 'none' : '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.12s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface2)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '12px 14px', fontWeight: 700, fontSize: 13, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{p.query_id}</td>
                  <td style={{ padding: '12px 14px', maxWidth: 260, fontSize: 13 }}>
                    <div style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {p.query_text}
                    </div>
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20, background: 'var(--surface2)', color: 'var(--muted)', border: '1px solid var(--border)', whiteSpace: 'nowrap' }}>
                      {p.intent}
                    </span>
                  </td>
                  <td style={{ padding: '12px 14px', fontSize: 12, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{p.domain}</td>
                  <td style={{ padding: '12px 14px' }}>
                    <OutcomeTag outcome={p.outcome} />
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 140 }}>
                      <MiniScoreRow label="Mindtrip" value={p.mindtrip_pass_rate} color={MT} />
                      <MiniScoreRow label="Wanderboat" value={p.wanderboat_pass_rate} color={WB} />
                    </div>
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <Link to={`/runs/${runId}/queries/${p.query_id}`} onClick={e => e.stopPropagation()}
                      style={{ fontSize: 11, color: MT }}>
                      Drill in →
                    </Link>
                  </td>
                </tr>
                {expanded === p.id && (
                  <tr key={`${p.id}-exp`} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td colSpan={7} style={{ padding: '0 14px 14px 14px' }}>
                      <div style={{ background: 'var(--surface2)', borderRadius: 8, padding: '12px 16px', borderLeft: `3px solid ${OUTCOME_COLOR[p.outcome] || 'var(--border)'}` }}>
                        <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6, fontWeight: 600 }}>
                          Outcome: {OUTCOME_LABEL[p.outcome]} · MT {pct(p.mindtrip_pass_rate)} · WB {pct(p.wanderboat_pass_rate)}
                        </div>
                        <p style={{ fontSize: 13 }}>{p.query_text}</p>
                        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
                          <Link to={`/runs/${runId}/queries/${p.query_id}`} style={{ color: MT }}>
                            View full responses and verdicts →
                          </Link>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
        {pairs.length === 0 && (
          <p style={{ padding: 32, textAlign: 'center', color: 'var(--muted)' }}>No results match filters.</p>
        )}
      </div>
    </>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────

function Card({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '18px 20px' }}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-1px', color }}>{value}</div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4, lineHeight: 1.4 }}>{sub}</div>
    </div>
  )
}

function ScoreSegment({ width, color, label }: { width: number; color: string; label: string }) {
  if (width < 1) return null
  return (
    <div style={{ width: `${width}%`, background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12, color: '#fff', transition: 'width 0.3s' }}>
      {width > 8 ? label : ''}
    </div>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block' }} />
      {label}
    </span>
  )
}

function BucketBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 }}>
      <span style={{ width: 70, color: 'var(--muted)', fontSize: 11 }}>{label}</span>
      <div style={{ flex: 1, background: 'var(--surface2)', borderRadius: 4, height: 8 }}>
        <div style={{ width: `${(value / max) * 100}%`, height: 8, borderRadius: 4, background: color }} />
      </div>
      <span style={{ width: 16, textAlign: 'right', fontWeight: 700, fontSize: 11, color }}>{value}</span>
    </div>
  )
}

function MiniDistBar({ outcomes, total }: { outcomes: Record<string, number>; total: number }) {
  const order = ['mindtrip_wins', 'wanderboat_wins', 'both_pass', 'both_fail', 'tie']
  return (
    <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', gap: 1, width: 120 }}>
      {order.map(k => {
        const v = outcomes[k] || 0
        if (!v) return null
        return <div key={k} style={{ flex: v, background: OUTCOME_COLOR[k] }} />
      })}
    </div>
  )
}

function MiniScoreRow({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
      <span style={{ color: 'var(--muted)', width: 68 }}>{label}</span>
      <div style={{ flex: 1, background: 'var(--surface2)', borderRadius: 3, height: 5 }}>
        <div style={{ width: `${value * 100}%`, height: 5, borderRadius: 3, background: color }} />
      </div>
      <span style={{ color, fontWeight: 600, width: 28, textAlign: 'right' }}>{pct(value)}</span>
    </div>
  )
}

function OutcomeTag({ outcome }: { outcome: string }) {
  const color = OUTCOME_COLOR[outcome] || 'var(--muted)'
  return (
    <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20, background: `${color}22`, color, border: `1px solid ${color}44`, whiteSpace: 'nowrap' }}>
      {OUTCOME_LABEL[outcome] || outcome}
    </span>
  )
}

function pct(v: number) { return `${Math.round(v * 100)}%` }
