import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, QueryDetail } from '../api'

const MT = 'var(--mindtrip)'
const WB = 'var(--wanderboat)'

export default function QueryDrillIn() {
  const { runId, queryId } = useParams<{ runId: string; queryId: string }>()
  const [detail, setDetail] = useState<QueryDetail | null>(null)

  useEffect(() => {
    if (runId && queryId) api.queryDetail(runId, queryId).then(setDetail)
  }, [runId, queryId])

  if (!detail) return <div style={{ padding: 40, color: 'var(--muted)' }}>Loading…</div>

  const { query, assertions, responses, verdicts, pair_result } = detail
  const mtVerdicts = verdicts['mindtrip'] || []
  const wbVerdicts = verdicts['wanderboat'] || []

  const sorted = [...assertions].sort((a, b) => {
    const o = { critical: 0, expected: 1, aspirational: 2 }
    return (o[a.level as keyof typeof o] ?? 3) - (o[b.level as keyof typeof o] ?? 3)
  })

  const LEVEL_COLOR: Record<string, string> = { critical: 'var(--red)', expected: MT, aspirational: 'var(--muted)' }
  const OUTCOME_COLOR: Record<string, string> = {
    mindtrip_wins: MT, wanderboat_wins: WB, both_pass: 'var(--green)', both_fail: 'var(--red)', tie: 'var(--tie)',
  }
  const OUTCOME_LABEL: Record<string, string> = {
    mindtrip_wins: 'Mindtrip wins', wanderboat_wins: 'Wanderboat wins', both_pass: 'Both pass', both_fail: 'Both fail', tie: 'Tie',
  }

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: '28px 24px' }}>
      {/* Breadcrumb */}
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 20, display: 'flex', gap: 6 }}>
        <Link to="/">Reports</Link> <span>›</span>
        <Link to={`/runs/${runId}`}>Run</Link> <span>›</span>
        <span>{queryId}</span>
      </div>

      {/* Query card */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '18px 22px', marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 20, background: 'var(--surface2)', color: 'var(--muted)', border: '1px solid var(--border)' }}>
            {query.intent as string}
          </span>
          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20, background: 'var(--surface2)', color: 'var(--muted)', border: '1px solid var(--border)' }}>
            {query.domain as string}
          </span>
          {pair_result && (
            <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 9px', borderRadius: 20, background: `${OUTCOME_COLOR[pair_result.outcome] || 'var(--muted)'}22`, color: OUTCOME_COLOR[pair_result.outcome] || 'var(--muted)', border: `1px solid ${OUTCOME_COLOR[pair_result.outcome] || 'var(--muted)'}44` }}>
              {OUTCOME_LABEL[pair_result.outcome] || pair_result.outcome}
            </span>
          )}
        </div>
        <p style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.5 }}>{query.query_text as string}</p>
      </div>

      {/* Pass rate header */}
      {pair_result && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24 }}>
          {[
            { product: 'Mindtrip', rate: pair_result.mindtrip_pass_rate, color: MT },
            { product: 'Wanderboat', rate: pair_result.wanderboat_pass_rate, color: WB },
          ].map(({ product, rate, color }) => (
            <div key={product} style={{ background: 'var(--surface)', border: `1px solid ${color}33`, borderRadius: 'var(--radius-lg)', padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ width: 46, height: 46, borderRadius: '50%', background: `${color}18`, border: `2px solid ${color}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontWeight: 800, color, fontSize: 13 }}>{Math.round(rate * 100)}%</span>
              </div>
              <div>
                <p style={{ fontWeight: 700, color, fontSize: 14 }}>{product}</p>
                <p style={{ fontSize: 11, color: 'var(--muted)' }}>Critical assertions passed</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Side-by-side responses */}
      <h2 style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>Responses</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 28 }}>
        {[
          { product: 'mindtrip', label: 'Mindtrip', color: MT },
          { product: 'wanderboat', label: 'Wanderboat', color: WB },
        ].map(({ product, label, color }) => (
          <div key={product} style={{ background: 'var(--surface)', border: `1px solid ${color}33`, borderRadius: 'var(--radius-lg)', padding: '16px 18px' }}>
            <p style={{ fontSize: 11, fontWeight: 700, color, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</p>
            <div style={{ fontSize: 13, lineHeight: 1.75, whiteSpace: 'pre-wrap', maxHeight: 380, overflowY: 'auto', color: 'var(--text)' }}>
              {responses[product]?.response_text || 'No response captured.'}
            </div>
          </div>
        ))}
      </div>

      {/* Assertions */}
      <h2 style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
        Assertions ({sorted.length})
      </h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sorted.map(a => {
          const mtV = mtVerdicts.find(v => v.assertion_id === a.id)
          const wbV = wbVerdicts.find(v => v.assertion_id === a.id)
          return <AssertionRow key={a.id} assertion={a} mtV={mtV} wbV={wbV} levelColor={LEVEL_COLOR} />
        })}
      </div>
    </div>
  )
}

function AssertionRow({ assertion, mtV, wbV, levelColor }: {
  assertion: { id: string; assertion_text: string; level: string; dimension: string }
  mtV?: { passed: number; judge_reasoning: string; judge_confidence: number }
  wbV?: { passed: number; judge_reasoning: string; judge_confidence: number }
  levelColor: Record<string, string>
}) {
  const [open, setOpen] = useState(false)
  const lc = levelColor[assertion.level] || 'var(--muted)'

  const pass = (v?: { passed: number }) => v != null && (v.passed === 1 || (v.passed as unknown) === true)
  const notJudged = !mtV && !wbV

  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        width: '100%', padding: '10px 14px', textAlign: 'left',
        display: 'grid', gridTemplateColumns: 'auto 1fr auto auto auto',
        gap: 10, alignItems: 'center',
      }}>
        <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 20, background: `${lc}18`, color: lc, border: `1px solid ${lc}33`, whiteSpace: 'nowrap' }}>
          {assertion.level}
        </span>
        <span style={{ fontSize: 13, textAlign: 'left', lineHeight: 1.4 }}>{assertion.assertion_text}</span>
        <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{assertion.dimension}</span>
        <VerdictDot v={mtV} color="var(--mindtrip)" label="MT" />
        <VerdictDot v={wbV} color="var(--wanderboat)" label="WB" />
      </button>
      {open && (
        <div style={{ borderTop: '1px solid var(--border)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0 }}>
          <VerdictDetail label="Mindtrip" color="var(--mindtrip)" v={mtV} />
          <VerdictDetail label="Wanderboat" color="var(--wanderboat)" v={wbV} isRight />
        </div>
      )}
    </div>
  )
}

function VerdictDot({ v, color, label }: { v?: { passed: number }; color: string; label: string }) {
  if (!v) return <span style={{ fontSize: 11, color: 'var(--muted)' }}>{label} —</span>
  const p = v.passed === 1 || (v.passed as unknown) === true
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: p ? 'var(--green)' : 'var(--red)', display: 'inline-block' }} />
      <span style={{ color }}>{label}</span>
    </span>
  )
}

function VerdictDetail({ label, color, v, isRight }: {
  label: string; color: string; isRight?: boolean
  v?: { passed: number; judge_reasoning: string; judge_confidence: number }
}) {
  const p = v && (v.passed === 1 || (v.passed as unknown) === true)
  return (
    <div style={{ padding: '12px 16px', borderLeft: isRight ? '1px solid var(--border)' : undefined }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontWeight: 700, fontSize: 12, color }}>{label}</span>
        {v && (
          <>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20, background: p ? '#1a3a2a' : '#3a1a1a', color: p ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
              {p ? 'Pass' : 'Fail'}
            </span>
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>{Math.round(v.judge_confidence * 100)}% conf.</span>
          </>
        )}
      </div>
      <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6 }}>
        {v ? v.judge_reasoning : 'Not judged yet.'}
      </p>
    </div>
  )
}
