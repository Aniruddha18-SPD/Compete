import { useEffect, useState, useCallback, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, Run, Summary, PivotRow, PairResult } from '../api'

const MT = 'var(--mindtrip)'
const WB = 'var(--wanderboat)'

const INTENTS = ['transactional', 'itinerary', 'personalized', 'live_data', 'edge_case']
const DOMAINS = ['easy', 'medium', 'hard']
const SEVERITIES = ['All Levels', 'Critical', 'Expected', 'Aspirational']

const OUTCOME_COLOR: Record<string, string> = {
  mindtrip_wins: 'var(--mindtrip)',
  wanderboat_wins: 'var(--wanderboat)',
  both_pass: 'var(--green)',
  tie: 'var(--tie)',
  both_fail: '#6b7280',
}
const OUTCOME_LABEL: Record<string, string> = {
  mindtrip_wins: 'Mindtrip wins',
  wanderboat_wins: 'Wanderboat wins',
  both_pass: 'Both pass',
  tie: 'Tie',
  both_fail: 'Both fail',
}

type Tab = 'summary' | 'winlose' | 'findings'
type PivotBy = 'intent' | 'domain'

export default function PairReportV2() {
  const { runId } = useParams<{ runId: string }>()

  const [run, setRun] = useState<Run | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [pivotRows, setPivotRows] = useState<PivotRow[]>([])
  const [pairs, setPairs] = useState<PairResult[]>([])
  const [loading, setLoading] = useState(true)

  const [tab, setTab] = useState<Tab>('summary')
  const [pivotBy, setPivotBy] = useState<PivotBy>('intent')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  const [domainFilter, setDomainFilter] = useState('All Domain')
  const [intentFilter, setIntentFilter] = useState('All Intent')
  const [severityFilter, setSeverityFilter] = useState('All Levels')
  const [search, setSearch] = useState('')

  const [drillPanel, setDrillPanel] = useState<string | null>(null)

  type Finding = { title: string; winner: 'mindtrip' | 'wanderboat' | 'neutral'; intent: string; summary: string; evidence: string }
  const [findings, setFindings] = useState<Finding[] | null>(null)
  const [findingsLoading, setFindingsLoading] = useState(false)

  const load = useCallback(async () => {
    if (!runId) return
    const [r, s, p] = await Promise.all([api.run(runId), api.summary(runId), api.pairs(runId)])
    setRun(r)
    setSummary(s)
    setPairs(p)
    const pv = await api.pivot(runId, pivotBy)
    setPivotRows(pv)
    setLoading(false)
  }, [runId, pivotBy])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!run || run.status === 'complete') return
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [run, load])

  const filteredPairs = pairs.filter(p => {
    if (domainFilter !== 'All Domain' && !p.domain.includes(domainFilter)) return false
    if (intentFilter !== 'All Intent' && p.intent !== intentFilter) return false
    if (search && !p.query_text.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const toggleRow = (val: string) => setExpandedRows(prev => {
    const next = new Set(prev)
    next.has(val) ? next.delete(val) : next.add(val)
    return next
  })

  const expandAll = () => setExpandedRows(new Set(pivotRows.map(r => r.pivot_val)))
  const collapseAll = () => setExpandedRows(new Set())

  const clearFilters = () => {
    setDomainFilter('All Domain')
    setIntentFilter('All Intent')
    setSeverityFilter('All Levels')
  }

  if (loading) return <div style={{ padding: 40, color: 'var(--muted)', fontSize: 13 }}>Loading…</div>
  if (!run || !summary) return null

  // Show live progress panel while run is not complete
  if (run.status !== 'complete') {
    return <LiveProgressPanel run={run} onComplete={load} />
  }

  const totalOutcomes = Object.values(summary.outcomes).reduce((s, v) => s + v, 0)

  const drillPairs = drillPanel ? filteredPairs.filter(p =>
    pivotBy === 'intent' ? p.intent === drillPanel : p.domain === drillPanel
  ) : []

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 48px)', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside style={{
        width: sidebarOpen ? 220 : 40,
        minWidth: sidebarOpen ? 220 : 40,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        transition: 'width 0.2s, min-width 0.2s',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
      }}>
        <button
          onClick={() => setSidebarOpen(o => !o)}
          style={{
            position: 'absolute', top: 12, right: sidebarOpen ? 10 : '50%',
            transform: sidebarOpen ? 'none' : 'translateX(50%)',
            zIndex: 10, color: 'var(--muted)', fontSize: 13,
            padding: '2px 6px', borderRadius: 4,
            background: 'var(--surface2)', border: '1px solid var(--border)',
            transition: 'right 0.2s, transform 0.2s',
          }}
        >
          {sidebarOpen ? '‹' : '›'}
        </button>

        {sidebarOpen && (
          <div style={{ padding: '14px 14px 20px', overflowY: 'auto', flex: 1, paddingTop: 44 }}>
            <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 14 }}>
              Controls
            </p>

            {/* Pivot By */}
            <SideLabel>Pivot By</SideLabel>
            <select value={pivotBy} onChange={e => setPivotBy(e.target.value as PivotBy)}
              style={{ width: '100%', marginBottom: 12 }}>
              <option value="intent">Intent</option>
              <option value="domain">Domain</option>
            </select>

            <SideLabel>Secondary Pivot</SideLabel>
            <select style={{ width: '100%', marginBottom: 12 }}>
              <option value="">None</option>
              <option value="domain">Domain</option>
            </select>

            <SideLabel>Tertiary Pivot</SideLabel>
            <select style={{ width: '100%', marginBottom: 18 }}>
              <option value="">None</option>
            </select>

            {/* Divider */}
            <div style={{ height: 1, background: 'var(--border)', marginBottom: 14 }} />

            {/* Filters */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--muted)', textTransform: 'uppercase' }}>
                Filters
              </p>
              <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
                <button onClick={expandAll} style={{ fontSize: 10, color: 'var(--mindtrip)', padding: '1px 5px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--surface2)' }}>
                  Expand all
                </button>
                <button onClick={collapseAll} style={{ fontSize: 10, color: 'var(--muted)', padding: '1px 5px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--surface2)' }}>
                  Collapse all
                </button>
              </div>
            </div>

            <FilterGroup label="Domain" value={domainFilter} options={['All Domain', ...DOMAINS]} onChange={setDomainFilter} />
            <FilterGroup label="Intent" value={intentFilter} options={['All Intent', ...INTENTS]} onChange={setIntentFilter} />
            <FilterGroup label="Assertion Severity Level" value={severityFilter} options={SEVERITIES} onChange={setSeverityFilter} />

            <button onClick={clearFilters} style={{ fontSize: 11, color: 'var(--mindtrip)', marginTop: 8 }}>
              Clear all filters
            </button>
          </div>
        )}
      </aside>

      {/* Main content */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        {/* Topbar breadcrumb */}
        <div style={{
          padding: '10px 20px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--surface)',
          display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
          position: 'sticky', top: 0, zIndex: 50,
        }}>
          <Link to="/v2" style={{ fontSize: 12, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
            ← All reports
          </Link>
          <span style={{ color: 'var(--border)' }}>|</span>
          <span style={{ fontSize: 12, fontWeight: 600 }}>Mindtrip vs. Wanderboat</span>
          <div style={{ display: 'flex', gap: 5 }}>
            <TopChip label="Published" color="var(--green)" />
            <TopChip label="V1 query set" color="var(--muted)" />
            <TopChip label="Latest" color="var(--mindtrip)" />
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            <span style={{
              fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 6,
              border: '1px solid var(--border)', color: 'var(--muted)', background: 'var(--surface2)',
            }}>
              {run.status === 'complete' ? '✓ Complete' : run.status === 'judging' ? '⟳ Judging…' : run.status}
            </span>
          </div>
        </div>

        {/* Report header */}
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 800, fontSize: 17, color: MT }}>Mindtrip</span>
            <span style={{ color: 'var(--muted)', fontSize: 14 }}>vs</span>
            <span style={{ fontWeight: 800, fontSize: 17, color: WB }}>Wanderboat</span>
            <span style={{ fontSize: 14, color: 'var(--muted)', fontWeight: 400 }}>
              SBS Compete Analysis {new Date(run.created_at).toISOString().split('T')[0]}
            </span>
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
              background: 'rgba(79,142,247,.15)', color: MT, border: '1px solid rgba(79,142,247,.3)',
              letterSpacing: '0.06em',
            }}>
              {pivotBy.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 0, padding: '0 24px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
          <TabButton active={tab === 'summary'} onClick={() => setTab('summary')} icon="☰">Summary</TabButton>
          <TabButton active={tab === 'winlose'} onClick={() => setTab('winlose')} icon="⊞">Win/Lose Table</TabButton>
          <TabButton active={tab === 'findings'} onClick={() => {
            setTab('findings')
            if (!findings && !findingsLoading && runId) {
              setFindingsLoading(true)
              api.findings(runId).then(r => setFindings(r.findings)).finally(() => setFindingsLoading(false))
            }
          }} icon="✦">Key Findings</TabButton>
        </div>

        {/* Content */}
        <div style={{ padding: '20px 24px', flex: 1 }}>
          {tab === 'findings' ? (
            <KeyFindingsView findings={findings} loading={findingsLoading} summary={summary} />
          ) : tab === 'summary' ? (
            <SummaryView
              summary={summary}
              totalOutcomes={totalOutcomes}
              pivotRows={pivotRows}
              pivotBy={pivotBy}
              pairs={pairs}
              expandedRows={expandedRows}
              onToggleRow={toggleRow}
              onDrillIn={setDrillPanel}
            />
          ) : (
            <WinLoseView
              pairs={filteredPairs}
              pivotRows={pivotRows}
              pivotBy={pivotBy}
              search={search}
              onSearch={setSearch}
              onDrillIn={setDrillPanel}
            />
          )}
        </div>
      </div>

      {/* Drill-in panel */}
      {drillPanel && (
        <DrillPanel
          label={drillPanel}
          pairs={drillPairs}
          runId={runId!}
          onClose={() => setDrillPanel(null)}
        />
      )}
    </div>
  )
}

/* ─── Live Progress Panel ─── */
function LiveProgressPanel({ run, onComplete }: { run: Run; onComplete: () => void }) {
  const [progress, setProgress] = useState<{
    status: string
    captured_queries: number
    by_product: Record<string, number>
    verdict_count: number
    total_verdicts_expected: number
  } | null>(null)

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const p = await api.progress(run.id)
        setProgress(p)
        if (p.status === 'complete') {
          if (intervalRef.current) clearInterval(intervalRef.current)
          onComplete()
        }
      } catch (_) { /* ignore polling errors */ }
    }
    poll()
    intervalRef.current = setInterval(poll, 3000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [run.id, onComplete])

  const isCapturing = !progress || progress.status === 'capturing'
  const isJudging = progress?.status === 'judging'
  const verdictPct = progress && progress.total_verdicts_expected > 0
    ? Math.round(progress.verdict_count / progress.total_verdicts_expected * 100)
    : 0

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: 'calc(100vh - 48px)',
      padding: '40px 24px',
    }}>
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 16, padding: '40px 48px', maxWidth: 520, width: '100%',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            border: '3px solid var(--mindtrip)',
            borderTopColor: 'transparent',
            animation: 'spin 0.9s linear infinite',
            flexShrink: 0,
          }} />
          <div>
            <p style={{ fontWeight: 700, fontSize: 16 }}>Running Live Eval</p>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>{run.run_name}</p>
          </div>
        </div>

        {/* Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 32 }}>
          <StepRow
            done={!!progress && (progress.captured_queries > 0 || isJudging || progress.status === 'complete')}
            active={isCapturing}
            label="Scraping responses"
            detail={progress
              ? `Wanderboat: ${progress.by_product['wanderboat'] ?? 0}  ·  Mindtrip: ${progress.by_product['mindtrip'] ?? 0}`
              : 'Starting scrapers…'}
          />
          <StepRow
            done={progress?.status === 'complete'}
            active={isJudging}
            label="Judging with Claude Haiku"
            detail={isJudging || progress?.status === 'complete'
              ? `${progress?.verdict_count ?? 0} / ${progress?.total_verdicts_expected ?? '?'} assertions scored`
              : 'Waiting for capture to finish…'}
          />
          <StepRow
            done={progress?.status === 'complete'}
            active={false}
            label="Building report"
            detail="Computing outcomes and pass rates"
          />
        </div>

        {/* Verdict progress bar */}
        {(isJudging || progress?.status === 'complete') && progress && progress.total_verdicts_expected > 0 && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>Assertions judged</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--mindtrip)' }}>{verdictPct}%</span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: 'var(--border)' }}>
              <div style={{
                height: '100%', borderRadius: 3, background: 'var(--mindtrip)',
                width: `${verdictPct}%`, transition: 'width 0.5s ease',
              }} />
            </div>
          </div>
        )}

        <p style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'center' }}>
          Polling every 3s · This page updates automatically when complete
        </p>
      </div>
    </div>
  )
}

function StepRow({ done, active, label, detail }: {
  done: boolean; active: boolean; label: string; detail: string
}) {
  const textColor = done ? 'var(--green)' : active ? 'var(--mindtrip)' : 'var(--muted)'
  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
      <div style={{
        width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
        background: done ? 'var(--green)' : active ? 'var(--mindtrip)' : 'var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, color: done || active ? '#fff' : 'var(--muted)', marginTop: 1,
      }}>
        {done ? '✓' : active ? (
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            border: '2px solid rgba(255,255,255,0.8)',
            borderTopColor: 'transparent',
            animation: 'spin 0.9s linear infinite',
          }} />
        ) : '·'}
      </div>
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: 13, fontWeight: active || done ? 600 : 400, color: textColor }}>{label}</p>
        <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2, lineHeight: 1.4 }}>{detail}</p>
      </div>
    </div>
  )
}

/* ─── Summary Tab ─── */
function SummaryView({
  summary, totalOutcomes, pivotRows, pivotBy, pairs, expandedRows, onToggleRow, onDrillIn,
}: {
  summary: Summary
  totalOutcomes: number
  pivotRows: PivotRow[]
  pivotBy: string
  pairs: PairResult[]
  expandedRows: Set<string>
  onToggleRow: (v: string) => void
  onDrillIn: (v: string) => void
}) {
  const pct = (k: string) => totalOutcomes ? Math.round((summary.outcomes[k] || 0) / totalOutcomes * 100) : 0
  const segments = [
    { key: 'mindtrip_wins', color: MT, label: 'MT wins' },
    { key: 'wanderboat_wins', color: WB, label: 'WB wins' },
    { key: 'both_pass', color: 'var(--green)', label: 'Both pass' },
    { key: 'tie', color: 'var(--tie)', label: 'Tie' },
    { key: 'both_fail', color: '#4b5563', label: 'Both fail' },
  ].filter(s => pct(s.key) > 0)

  const totalQueries = pivotRows.reduce((s, r) => s + r.query_count, 0)
  const totalAssertions = pairs.reduce((s) => s + 4, 0)

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20, alignItems: 'start' }}>
      {/* Left: distribution + pivot table */}
      <div>
        {/* Distribution bar */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px', marginBottom: 16 }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 12 }}>
            Overall Win / Lose / Tie / Fail Distribution
          </p>
          <div style={{ display: 'flex', height: 32, borderRadius: 6, overflow: 'hidden', marginBottom: 10 }}>
            {segments.map(s => {
              const p = pct(s.key)
              return p > 0 ? (
                <div key={s.key} style={{
                  flex: p, background: s.color, display: 'flex', alignItems: 'center',
                  justifyContent: 'center', minWidth: p > 5 ? 0 : 0,
                }}>
                  {p >= 6 && <span style={{ fontSize: 11, fontWeight: 700, color: '#fff' }}>{p}%</span>}
                </div>
              ) : null
            })}
          </div>
          {/* Legend */}
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            {segments.map(s => (
              <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: s.color, display: 'inline-block' }} />
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>{s.label}</span>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 10 }}>
            {totalQueries} queries · {totalAssertions} assertions ·{' '}
            <span style={{ color: 'var(--yellow)', fontWeight: 600 }}>⚡ Critical</span>
          </p>
        </div>

        {/* Pivot Table */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          {/* Header */}
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 120px 80px 160px 80px',
            gap: 0, padding: '10px 16px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--surface2)',
          }}>
            {['Intent', 'Win / Lose / Tie / Fail', '#Queries', 'Per-Query Pass Rate', 'Analysis'].map(h => (
              <span key={h} style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.07em', color: 'var(--muted)', textTransform: 'uppercase' }}>{h}</span>
            ))}
          </div>
          {pivotRows.map((row, i) => {
            const rowTotal = Object.values(row.outcomes).reduce((s, v) => s + v, 0)
            const isExpanded = expandedRows.has(row.pivot_val)

            return (
              <div key={row.pivot_val}>
                <button
                  onClick={() => onToggleRow(row.pivot_val)}
                  style={{
                    width: '100%', display: 'grid', gridTemplateColumns: '1fr 120px 80px 160px 80px',
                    gap: 0, padding: '11px 16px', textAlign: 'left',
                    borderBottom: i < pivotRows.length - 1 || isExpanded ? '1px solid var(--border)' : undefined,
                    background: isExpanded ? 'var(--surface2)' : 'var(--surface)',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => { if (!isExpanded) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)' }}
                  onMouseLeave={e => { if (!isExpanded) (e.currentTarget as HTMLElement).style.background = 'var(--surface)' }}
                >
                  {/* Label */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 10, color: 'var(--muted)' }}>{isExpanded ? '▼' : '▶'}</span>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{row.pivot_val}</span>
                  </div>

                  {/* Mini dist bar */}
                  <div style={{ display: 'flex', height: 14, borderRadius: 3, overflow: 'hidden', alignSelf: 'center', gap: 1 }}>
                    {[
                      { key: 'mindtrip_wins', color: MT },
                      { key: 'wanderboat_wins', color: WB },
                      { key: 'both_pass', color: 'var(--green)' },
                      { key: 'tie', color: 'var(--tie)' },
                      { key: 'both_fail', color: '#4b5563' },
                    ].map(s => {
                      const p = rowTotal ? Math.round((row.outcomes[s.key] || 0) / rowTotal * 100) : 0
                      return p > 0 ? <div key={s.key} style={{ flex: p, background: s.color, borderRadius: 2 }} /> : null
                    })}
                  </div>

                  {/* #Queries */}
                  <span style={{ fontSize: 12, color: 'var(--muted)' }}>{row.query_count}</span>

                  {/* Pass rates */}
                  <div style={{ display: 'flex', gap: 8 }}>
                    <span style={{ fontSize: 12, color: MT, fontWeight: 600 }}>{Math.round(row.mindtrip_pass_rate * 100)}%</span>
                    <span style={{ fontSize: 12, color: 'var(--muted)' }}>·</span>
                    <span style={{ fontSize: 12, color: WB, fontWeight: 600 }}>{Math.round(row.wanderboat_pass_rate * 100)}%</span>
                  </div>

                  {/* Analysis */}
                  <button
                    onClick={e => { e.stopPropagation(); onDrillIn(row.pivot_val) }}
                    style={{ fontSize: 10, color: 'var(--mindtrip)', textDecoration: 'underline', textAlign: 'left' }}
                  >
                    Drill in →
                  </button>
                </button>

                {/* Sub-rows placeholder */}
                {isExpanded && (
                  <div style={{ background: 'var(--bg)', borderBottom: '1px solid var(--border)', padding: '8px 16px 8px 36px' }}>
                    <p style={{ fontSize: 11, color: 'var(--muted)', fontStyle: 'italic' }}>
                      {row.query_count} quer{row.query_count === 1 ? 'y' : 'ies'} in {row.pivot_val} ·{' '}
                      MT avg {Math.round(row.mindtrip_pass_rate * 100)}% pass · WB avg {Math.round(row.wanderboat_pass_rate * 100)}% pass
                    </p>
                    <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {Object.entries(row.outcomes).filter(([, v]) => v > 0).map(([k, v]) => (
                        <span key={k} style={{
                          fontSize: 10, padding: '1px 8px', borderRadius: 20,
                          background: `${OUTCOME_COLOR[k] || 'var(--muted)'}18`,
                          color: OUTCOME_COLOR[k] || 'var(--muted)',
                          border: `1px solid ${OUTCOME_COLOR[k] || 'var(--muted)'}33`,
                        }}>
                          {OUTCOME_LABEL[k]}: {v}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Right: Quality Metrics */}
      <div>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px' }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 16 }}>
            Quality Metrics
          </p>

          <MetricBlock
            label="Per-Query Pass Rate"
            desc="For each query, the % of assertions that passed — then averaged across queries, so every query counts the same."
            mtVal={`${Math.round(summary.mindtrip_avg_pass_rate * 100)}%`}
            wbVal={`${Math.round(summary.wanderboat_avg_pass_rate * 100)}%`}
            mtDelta={`+${Math.round((summary.mindtrip_avg_pass_rate - summary.wanderboat_avg_pass_rate) * 100)}%`}
          />

          <div style={{ height: 1, background: 'var(--border)', margin: '16px 0' }} />

          <MetricBlock
            label="Grounding"
            sublabel="(Grounded)"
            desc="For each query, the % of response claims supported by reviewed sources — then averaged across queries. Higher is better."
            mtVal="N/A"
            wbVal="N/A"
            mtDelta="—"
          />
        </div>

        {/* Outcome summary pills */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 18px', marginTop: 12 }}>
          <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 12 }}>
            Outcome Breakdown
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              { key: 'mindtrip_wins', label: 'Mindtrip Wins', color: MT },
              { key: 'wanderboat_wins', label: 'Wanderboat Wins', color: WB },
              { key: 'both_pass', label: 'Both Pass', color: 'var(--green)' },
              { key: 'tie', label: 'Tie', color: 'var(--tie)' },
              { key: 'both_fail', label: 'Both Fail', color: '#6b7280' },
            ].map(({ key, label, color }) => {
              const count = summary.outcomes[key] || 0
              const p = totalOutcomes ? Math.round(count / totalOutcomes * 100) : 0
              return (
                <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: color, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: 'var(--muted)', flex: 1 }}>{label}</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color }}>{count}</span>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>{p}%</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ─── Win/Lose Table Tab ─── */
function WinLoseView({
  pairs, pivotRows, pivotBy, search, onSearch, onDrillIn,
}: {
  pairs: PairResult[]
  pivotRows: PivotRow[]
  pivotBy: string
  search: string
  onSearch: (s: string) => void
  onDrillIn: (v: string) => void
}) {
  const displayRows = pivotRows.map(row => {
    const rowPairs = pairs.filter(p =>
      pivotBy === 'intent' ? p.intent === row.pivot_val : p.domain === row.pivot_val
    )
    const mtWins = rowPairs.filter(p => p.outcome === 'mindtrip_wins').length
    const wbWins = rowPairs.filter(p => p.outcome === 'wanderboat_wins').length
    const total = rowPairs.length
    const winRatio = (mtWins + wbWins) > 0 ? Math.round(mtWins / (mtWins + wbWins) * 100) : null
    return { ...row, mtWins, wbWins, total, winRatio }
  })

  const exportCSV = () => {
    const header = `${pivotBy.toUpperCase()},QUERIES,MT WINS,WB WINS,WIN RATIO\n`
    const rows = displayRows.map(r => `${r.pivot_val},${r.total},${r.mtWins},${r.wbWins},${r.winRatio !== null ? r.winRatio + '%' : '—'}`).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `compete-winlose-${pivotBy}.csv`
    a.click()
  }

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: 320 }}>
          <span style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)', fontSize: 13 }}>⌕</span>
          <input type="text" placeholder="Search queries…" value={search} onChange={e => onSearch(e.target.value)}
            style={{ paddingLeft: 28, width: '100%' }} />
        </div>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>{displayRows.length} items</span>
        <button onClick={exportCSV} style={{
          fontSize: 11, fontWeight: 600, padding: '5px 12px', borderRadius: 6,
          border: '1px solid var(--border)', color: 'var(--muted)', background: 'var(--surface2)',
          marginLeft: 'auto',
        }}>
          Export as CSV
        </button>
      </div>

      {/* Table */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        {/* Header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 80px 110px 110px 100px',
          padding: '10px 16px', background: 'var(--surface2)',
          borderBottom: '1px solid var(--border)',
        }}>
          {[pivotBy === 'intent' ? 'Intent' : 'Domain', 'Queries', 'Mindtrip Wins', 'Wanderboat Wins', 'Win Ratio'].map(h => (
            <span key={h} style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.07em', color: 'var(--muted)', textTransform: 'uppercase' }}>{h}</span>
          ))}
        </div>

        {displayRows.map((row, i) => (
          <div key={row.pivot_val} style={{
            display: 'grid', gridTemplateColumns: '1fr 80px 110px 110px 100px',
            padding: '12px 16px', alignItems: 'center',
            borderBottom: i < displayRows.length - 1 ? '1px solid var(--border)' : undefined,
          }}>
            {/* Label */}
            <div>
              <button
                onClick={() => onDrillIn(row.pivot_val)}
                style={{ fontWeight: 600, fontSize: 13, textAlign: 'left', color: 'var(--text)' }}
                onMouseEnter={e => (e.currentTarget.style.color = MT)}
                onMouseLeave={e => (e.currentTarget.style.color = 'var(--text)')}
              >
                {row.pivot_val}
              </button>
            </div>

            {/* Query count */}
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{row.total}</span>

            {/* MT wins */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                fontSize: 15, fontWeight: 800, color: row.mtWins > 0 ? MT : 'var(--muted)',
              }}>{row.mtWins}</span>
            </div>

            {/* WB wins */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                fontSize: 15, fontWeight: 800, color: row.wbWins > 0 ? WB : 'var(--muted)',
              }}>{row.wbWins}</span>
            </div>

            {/* Win ratio */}
            <div>
              {row.winRatio !== null ? (
                <span style={{
                  fontSize: 13, fontWeight: 700,
                  color: row.winRatio > 50 ? MT : row.winRatio < 50 ? WB : 'var(--tie)',
                }}>
                  {row.winRatio}%
                </span>
              ) : (
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>—</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Individual query table */}
      {search && (
        <div style={{ marginTop: 20 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 10 }}>
            Matching Queries ({pairs.length})
          </p>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            {pairs.map((p, i) => (
              <div key={p.id} style={{
                padding: '10px 16px',
                borderBottom: i < pairs.length - 1 ? '1px solid var(--border)' : undefined,
                display: 'grid', gridTemplateColumns: '1fr auto auto',
                gap: 12, alignItems: 'center',
              }}>
                <div>
                  <p style={{ fontSize: 13, lineHeight: 1.4 }}>{p.query_text}</p>
                  <div style={{ display: 'flex', gap: 5, marginTop: 4 }}>
                    <MiniChip label={p.intent} />
                    <MiniChip label={p.domain} />
                  </div>
                </div>
                <OutcomeChip outcome={p.outcome} />
                <div style={{ display: 'flex', gap: 6 }}>
                  <span style={{ fontSize: 11, color: MT }}>{Math.round(p.mindtrip_pass_rate * 100)}%</span>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>·</span>
                  <span style={{ fontSize: 11, color: WB }}>{Math.round(p.wanderboat_pass_rate * 100)}%</span>
                </div>
              </div>
            ))}
            {pairs.length === 0 && <p style={{ padding: 24, color: 'var(--muted)', fontSize: 13, textAlign: 'center' }}>No matches.</p>}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Drill Panel ─── */
function DrillPanel({ label, pairs, runId, onClose }: {
  label: string; pairs: PairResult[]; runId: string; onClose: () => void
}) {
  const [filter, setFilter] = useState<'All' | 'mindtrip_wins' | 'wanderboat_wins' | 'both_pass' | 'both_fail'>('All')
  const filtered = filter === 'All' ? pairs : pairs.filter(p => p.outcome === filter)

  return (
    <div style={{
      width: 460, minWidth: 460, borderLeft: '1px solid var(--border)',
      background: 'var(--surface)', overflowY: 'auto',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Panel header */}
      <div style={{
        padding: '14px 18px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
        position: 'sticky', top: 0, background: 'var(--surface)', zIndex: 10,
      }}>
        <div style={{ flex: 1 }}>
          <p style={{ fontWeight: 700, fontSize: 14 }}>{label}</p>
          <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
            {pairs.length} quer{pairs.length === 1 ? 'y' : 'ies'}
          </p>
        </div>
        <button onClick={onClose} style={{ color: 'var(--muted)', fontSize: 18, lineHeight: 1 }}>✕</button>
      </div>

      {/* Filter tabs */}
      <div style={{ padding: '10px 18px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {(['All', 'mindtrip_wins', 'wanderboat_wins', 'both_pass', 'both_fail'] as const).map(f => {
          const count = f === 'All' ? pairs.length : pairs.filter(p => p.outcome === f).length
          if (count === 0 && f !== 'All') return null
          return (
            <button key={f} onClick={() => setFilter(f)} style={{
              fontSize: 11, fontWeight: filter === f ? 700 : 400,
              padding: '3px 10px', borderRadius: 20,
              background: filter === f ? `${OUTCOME_COLOR[f] || 'var(--mindtrip)'}22` : 'var(--surface2)',
              color: filter === f ? (OUTCOME_COLOR[f] || 'var(--mindtrip)') : 'var(--muted)',
              border: `1px solid ${filter === f ? (OUTCOME_COLOR[f] || 'var(--mindtrip)') + '55' : 'var(--border)'}`,
            }}>
              {f === 'All' ? 'All' : OUTCOME_LABEL[f]} ({count})
            </button>
          )
        })}
      </div>

      {/* Query cards */}
      <div style={{ padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {filtered.map(pair => (
          <div key={pair.id} style={{
            background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8,
            padding: '12px 14px',
          }}>
            {/* Chips row */}
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 8 }}>
              <MiniChip label={pair.intent} />
              <MiniChip label={pair.domain} />
              <OutcomeChip outcome={pair.outcome} />
            </div>

            {/* Query text */}
            <p style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 10 }}>{pair.query_text}</p>

            {/* Pass rates */}
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8 }}>
              <PassBar label="MT" rate={pair.mindtrip_pass_rate} color={MT} />
              <PassBar label="WB" rate={pair.wanderboat_pass_rate} color={WB} />
            </div>

            {/* Drill-in link */}
            <Link
              to={`/v2/runs/${runId}/queries/${pair.query_id}`}
              style={{ fontSize: 11, color: MT, fontWeight: 600 }}
            >
              Show details →
            </Link>
          </div>
        ))}
        {filtered.length === 0 && (
          <p style={{ color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: 24 }}>No queries match.</p>
        )}
      </div>
    </div>
  )
}

/* ─── Key Findings ─── */
type Finding = { title: string; winner: 'mindtrip' | 'wanderboat' | 'neutral'; intent: string; summary: string; evidence: string }

function KeyFindingsView({ findings, loading, summary }: {
  findings: Finding[] | null; loading: boolean; summary: Summary | null
}) {
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 24px', gap: 16 }}>
        <div style={{ fontSize: 28 }}>✦</div>
        <p style={{ color: 'var(--muted)', fontSize: 14 }}>Generating key findings with GPT-4o…</p>
        <p style={{ color: 'var(--muted)', fontSize: 12 }}>Analyzing verdict reasoning across all 20 queries</p>
      </div>
    )
  }

  if (!findings) {
    return (
      <div style={{ padding: '60px 24px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
        Click the tab to generate findings.
      </div>
    )
  }

  const total = findings.length
  const mtCount = findings.filter(f => f.winner === 'mindtrip').length
  const wbCount = findings.filter(f => f.winner === 'wanderboat').length

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      {/* Verdict banner */}
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12,
        padding: '20px 24px', marginBottom: 24,
        borderLeft: `4px solid ${mtCount >= wbCount ? MT : WB}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <span style={{ fontSize: 22 }}>✦</span>
          <div>
            <p style={{ fontSize: 15, fontWeight: 700 }}>
              {mtCount > wbCount
                ? <><span style={{ color: MT }}>Mindtrip</span> leads this evaluation</>
                : mtCount < wbCount
                ? <><span style={{ color: WB }}>Wanderboat</span> leads this evaluation</>
                : <>Products are <span style={{ color: 'var(--tie)' }}>closely matched</span></>
              }
            </p>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 3 }}>
              {summary && <>Mindtrip avg pass rate <strong style={{ color: MT }}>{Math.round(summary.mindtrip_avg_pass_rate * 100)}%</strong> · Wanderboat <strong style={{ color: WB }}>{Math.round(summary.wanderboat_avg_pass_rate * 100)}%</strong> · {total} key findings</>}
            </p>
          </div>
        </div>
      </div>

      {/* Finding cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {findings.map((f, i) => {
          const winColor = f.winner === 'mindtrip' ? MT : f.winner === 'wanderboat' ? WB : 'var(--tie)'
          const winLabel = f.winner === 'mindtrip' ? 'Mindtrip advantage' : f.winner === 'wanderboat' ? 'Wanderboat advantage' : 'Neutral'
          return (
            <div key={i} style={{
              background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10,
              overflow: 'hidden',
            }}>
              {/* Card header */}
              <div style={{
                padding: '14px 18px 12px',
                borderBottom: '1px solid var(--border)',
                display: 'flex', alignItems: 'flex-start', gap: 12,
              }}>
                {/* Finding number */}
                <span style={{
                  fontSize: 11, fontWeight: 800, color: winColor,
                  background: `${winColor}18`, border: `1px solid ${winColor}33`,
                  borderRadius: 6, padding: '2px 7px', flexShrink: 0, marginTop: 1,
                }}>#{i + 1}</span>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                    <span style={{ fontSize: 14, fontWeight: 700 }}>{f.title}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {/* Winner chip */}
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                      background: `${winColor}18`, color: winColor, border: `1px solid ${winColor}33`,
                    }}>{winLabel}</span>
                    {/* Intent chip */}
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 20,
                      background: 'var(--surface2)', color: 'var(--muted)', border: '1px solid var(--border)',
                    }}>{f.intent}</span>
                  </div>
                </div>
              </div>

              {/* Body */}
              <div style={{ padding: '14px 18px' }}>
                <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text)', marginBottom: 12 }}>
                  {f.summary}
                </p>
                {f.evidence && (
                  <div style={{
                    background: 'var(--bg)', border: '1px solid var(--border)',
                    borderLeft: `3px solid ${winColor}`, borderRadius: 6,
                    padding: '10px 14px',
                  }}>
                    <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
                      Evidence
                    </p>
                    <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6, fontStyle: 'italic' }}>
                      "{f.evidence}"
                    </p>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ─── Small helpers ─── */
function FilterGroup({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  const [open, setOpen] = useState(true)
  return (
    <div style={{ marginBottom: 12 }}>
      <button onClick={() => setOpen(o => !o)} style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: 6,
        fontSize: 11, fontWeight: 600, color: 'var(--text)', marginBottom: open ? 6 : 0,
      }}>
        <span style={{ color: 'var(--muted)', fontSize: 9 }}>{open ? '▼' : '▶'}</span>
        {label}
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--mindtrip)', fontWeight: value === options[0] ? 400 : 700 }}>
          {value === options[0] ? 'All' : value}
        </span>
      </button>
      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, paddingLeft: 14 }}>
          {options.map(opt => (
            <label key={opt} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12 }}>
              <input type="radio" name={label} value={opt} checked={value === opt} onChange={() => onChange(opt)}
                style={{ accentColor: 'var(--mindtrip)' }} />
              <span style={{ color: value === opt ? 'var(--text)' : 'var(--muted)' }}>{opt}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

function SideLabel({ children }: { children: React.ReactNode }) {
  return <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 5 }}>{children}</p>
}

function TabButton({ active, onClick, icon, children }: { active: boolean; onClick: () => void; icon: string; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      padding: '10px 16px', fontSize: 13, fontWeight: active ? 700 : 400,
      borderBottom: active ? `2px solid ${MT}` : '2px solid transparent',
      color: active ? 'var(--text)' : 'var(--muted)',
      display: 'flex', alignItems: 'center', gap: 5,
      transition: 'color 0.1s',
    }}>
      <span style={{ fontSize: 12 }}>{icon}</span>
      {children}
    </button>
  )
}

function TopChip({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 20,
      background: `${color}15`, color, border: `1px solid ${color}30`,
    }}>{label}</span>
  )
}

function MiniChip({ label }: { label: string }) {
  return (
    <span style={{
      fontSize: 10, padding: '1px 7px', borderRadius: 20,
      background: 'var(--surface)', color: 'var(--muted)', border: '1px solid var(--border)',
    }}>{label}</span>
  )
}

function OutcomeChip({ outcome }: { outcome: string }) {
  const color = OUTCOME_COLOR[outcome] || 'var(--muted)'
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
      background: `${color}18`, color, border: `1px solid ${color}33`,
      whiteSpace: 'nowrap',
    }}>
      {OUTCOME_LABEL[outcome] || outcome}
    </span>
  )
}

function PassBar({ label, rate, color }: { label: string; rate: number; color: string }) {
  return (
    <div style={{ flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontSize: 10, color, fontWeight: 700 }}>{label}</span>
        <span style={{ fontSize: 10, color: 'var(--muted)' }}>{Math.round(rate * 100)}%</span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: 'var(--border)' }}>
        <div style={{ height: '100%', borderRadius: 2, background: color, width: `${Math.round(rate * 100)}%` }} />
      </div>
    </div>
  )
}

function MetricBlock({ label, sublabel, desc, mtVal, wbVal, mtDelta }: {
  label: string; sublabel?: string; desc: string; mtVal: string; wbVal: string; mtDelta: string
}) {
  return (
    <div style={{ marginBottom: 4 }}>
      <p style={{ fontSize: 12, fontWeight: 700, marginBottom: 2 }}>
        {label} {sublabel && <span style={{ fontWeight: 400, color: 'var(--muted)' }}>{sublabel}</span>}
      </p>
      <p style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.5, marginBottom: 10 }}>{desc}</p>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 22, fontWeight: 800, color: MT }}>{mtVal}</span>
        <span style={{ fontSize: 13, color: 'var(--muted)' }}>+</span>
        <span style={{ fontSize: 22, fontWeight: 800, color: WB }}>{wbVal}</span>
      </div>
    </div>
  )
}
