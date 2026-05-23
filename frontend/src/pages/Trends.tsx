import { useEffect, useState } from 'react'
import { api, Run, PivotRow } from '../api'

const MT = '#4f8ef7'
const WB = '#f97316'
const INTENTS = ['transactional', 'itinerary', 'personalized', 'live_data', 'edge_case']
const INTENT_LABEL: Record<string, string> = {
  transactional: 'Transactional',
  itinerary: 'Itinerary',
  personalized: 'Personalized',
  live_data: 'Live Data',
  edge_case: 'Edge Cases',
}

interface RunPoint {
  label: string
  date: string
  mt: number
  wb: number
}

interface TrendData {
  overall: RunPoint[]
  byIntent: Record<string, RunPoint[]>
}

export default function Trends() {
  const [data, setData] = useState<TrendData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overall' | 'by-intent'>('overall')

  useEffect(() => {
    async function load() {
      const runs = await api.runs()
      const complete = runs.filter(r => r.status === 'complete')
        .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())

      const overall: RunPoint[] = []
      const byIntent: Record<string, RunPoint[]> = {}
      INTENTS.forEach(i => { byIntent[i] = [] })

      for (const run of complete) {
        const [summary, pivotRows] = await Promise.all([
          api.summary(run.id),
          api.pivot(run.id, 'intent'),
        ])

        const label = run.run_name.replace('Mock Run ', 'Run ')
        const date = new Date(run.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

        overall.push({
          label,
          date,
          mt: Math.round(summary.mindtrip_avg_pass_rate * 100),
          wb: Math.round(summary.wanderboat_avg_pass_rate * 100),
        })

        for (const intent of INTENTS) {
          const row = pivotRows.find((r: PivotRow) => r.pivot_val === intent)
          byIntent[intent].push({
            label,
            date,
            mt: row ? Math.round(row.mindtrip_pass_rate * 100) : 0,
            wb: row ? Math.round(row.wanderboat_pass_rate * 100) : 0,
          })
        }
      }

      setData({ overall, byIntent })
      setLoading(false)
    }
    load()
  }, [])

  if (loading) return <div style={{ padding: 40, color: 'var(--muted)', fontSize: 13 }}>Loading trend data…</div>
  if (!data) return null

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.4px' }}>Trends</h1>
        <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
          Pass rate over time — Mindtrip vs Wanderboat across all completed runs
        </p>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 28 }}>
        <TrendTab active={activeTab === 'overall'} onClick={() => setActiveTab('overall')}>
          Accuracy Metrics
        </TrendTab>
        <TrendTab active={activeTab === 'by-intent'} onClick={() => setActiveTab('by-intent')}>
          By Intent
        </TrendTab>
      </div>

      {activeTab === 'overall' ? (
        <div>
          <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)', textAlign: 'center', marginBottom: 20, letterSpacing: '0.04em' }}>
            Mindtrip vs Wanderboat — General Queryset
          </p>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '24px 28px' }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--mindtrip)', marginBottom: 20 }}>
              Accuracy – Overall Trend
            </p>
            <LineChart points={data.overall} height={340} />
          </div>
        </div>
      ) : (
        <div>
          <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)', textAlign: 'center', marginBottom: 20, letterSpacing: '0.04em' }}>
            Mindtrip vs Wanderboat — Intent-Based Queryset
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {INTENTS.map(intent => (
              <div key={intent} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '20px 22px' }}>
                <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--mindtrip)', marginBottom: 16 }}>
                  {INTENT_LABEL[intent] ?? intent} – Weekly Trend
                </p>
                <LineChart points={data.byIntent[intent]} height={220} compact />
              </div>
            ))}
            {/* 5th chart centered */}
          </div>
        </div>
      )}

      {/* Legend */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 28, marginTop: 28 }}>
        <LegendItem color={MT} label="Mindtrip" dashed={false} />
        <LegendItem color={WB} label="Wanderboat" dashed={false} />
        <div style={{ width: 1, background: 'var(--border)' }} />
        <LegendItem color="var(--text)" label="Pass Rate" dashed={false} dim />
      </div>
    </div>
  )
}

/* ─── Line Chart ─── */
function LineChart({ points, height, compact }: { points: RunPoint[]; height: number; compact?: boolean }) {
  const W = compact ? 380 : 820
  const H = height
  const PAD = { top: 24, right: 24, bottom: 52, left: compact ? 44 : 56 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom

  const yTicks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
  const yScale = (v: number) => PAD.top + chartH - (v / 100) * chartH
  const xScale = (i: number) => {
    if (points.length === 1) return PAD.left + chartW / 2
    return PAD.left + (i / (points.length - 1)) * chartW
  }

  const pathFor = (key: 'mt' | 'wb') =>
    points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p[key])}`).join(' ')

  const fontSize = compact ? 9 : 11

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block', minWidth: compact ? 300 : 500 }}>
        {/* Grid lines */}
        {yTicks.map(t => (
          <g key={t}>
            <line
              x1={PAD.left} x2={PAD.left + chartW}
              y1={yScale(t)} y2={yScale(t)}
              stroke="var(--border)" strokeWidth={t === 0 ? 1.5 : 0.5}
            />
            <text x={PAD.left - 6} y={yScale(t) + 3.5} textAnchor="end"
              fontSize={fontSize} fill="var(--muted)">
              {t}%
            </text>
          </g>
        ))}

        {/* Y axis label */}
        <text
          transform={`translate(${compact ? 10 : 14}, ${PAD.top + chartH / 2}) rotate(-90)`}
          textAnchor="middle" fontSize={compact ? 9 : 10} fill="var(--muted)"
        >
          Pass Rate (%)
        </text>

        {/* MT line */}
        {points.length > 1 && (
          <path d={pathFor('mt')} fill="none" stroke={MT} strokeWidth={2} strokeLinejoin="round" />
        )}
        {/* WB line */}
        {points.length > 1 && (
          <path d={pathFor('wb')} fill="none" stroke={WB} strokeWidth={2} strokeLinejoin="round" strokeDasharray="5,3" />
        )}

        {/* Data points + labels */}
        {points.map((p, i) => (
          <g key={i}>
            {/* MT dot */}
            <circle cx={xScale(i)} cy={yScale(p.mt)} r={compact ? 3.5 : 5} fill={MT} />
            {/* WB dot */}
            <circle cx={xScale(i)} cy={yScale(p.wb)} r={compact ? 3.5 : 5} fill={WB} />

            {/* Value labels on hover-ish — always show for small datasets */}
            {points.length <= 6 && (
              <>
                <text x={xScale(i)} y={yScale(p.mt) - 8} textAnchor="middle"
                  fontSize={compact ? 9 : 11} fill={MT} fontWeight="600">
                  {p.mt}%
                </text>
                <text x={xScale(i)} y={yScale(p.wb) + (p.wb < p.mt ? 16 : -8)} textAnchor="middle"
                  fontSize={compact ? 9 : 11} fill={WB} fontWeight="600">
                  {p.wb}%
                </text>
              </>
            )}

            {/* X tick labels */}
            <text
              x={xScale(i)} y={H - PAD.bottom + 16}
              textAnchor="middle" fontSize={compact ? 8 : 10} fill="var(--muted)"
            >
              {p.label}
            </text>
            <text
              x={xScale(i)} y={H - PAD.bottom + 28}
              textAnchor="middle" fontSize={compact ? 7 : 9} fill="var(--muted)"
            >
              {p.date}
            </text>
          </g>
        ))}

        {/* X axis label */}
        <text x={PAD.left + chartW / 2} y={H - 4} textAnchor="middle"
          fontSize={compact ? 9 : 11} fill="var(--muted)">
          Run
        </text>

        {/* Vertical reference lines */}
        {points.map((_, i) => (
          <line key={i}
            x1={xScale(i)} x2={xScale(i)}
            y1={PAD.top} y2={PAD.top + chartH}
            stroke="var(--border)" strokeWidth={0.5} strokeDasharray="3,4"
          />
        ))}

        {/* Per-chart mini legend */}
        <g transform={`translate(${PAD.left + 8}, ${PAD.top + 4})`}>
          <circle cx={0} cy={0} r={compact ? 3 : 4} fill={MT} />
          <text x={compact ? 6 : 8} y={compact ? 3 : 4} fontSize={compact ? 8 : 10} fill="var(--muted)">Mindtrip</text>
          <circle cx={compact ? 52 : 65} cy={0} r={compact ? 3 : 4} fill={WB} />
          <text x={compact ? 58 : 73} y={compact ? 3 : 4} fontSize={compact ? 8 : 10} fill="var(--muted)">Wanderboat</text>
        </g>
      </svg>
    </div>
  )
}

function TrendTab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      padding: '10px 18px', fontSize: 13, fontWeight: active ? 700 : 400,
      borderBottom: active ? '2px solid var(--mindtrip)' : '2px solid transparent',
      color: active ? 'var(--text)' : 'var(--muted)',
    }}>
      {children}
    </button>
  )
}

function LegendItem({ color, label, dashed, dim }: { color: string; label: string; dashed: boolean; dim?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
      <svg width={24} height={12}>
        <line x1={0} y1={6} x2={24} y2={6} stroke={color} strokeWidth={2}
          strokeDasharray={dashed ? '4,3' : undefined} opacity={dim ? 0.4 : 1} />
        <circle cx={12} cy={6} r={3.5} fill={color} opacity={dim ? 0.4 : 1} />
      </svg>
      <span style={{ fontSize: 12, color: dim ? 'var(--muted)' : 'var(--text)' }}>{label}</span>
    </div>
  )
}
