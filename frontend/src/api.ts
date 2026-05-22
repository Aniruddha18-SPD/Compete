const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export interface Run {
  id: string
  run_name: string
  status: string
  query_set_version: string
  created_at: string
  completed_at?: string
  query_count: number
  result_count: number
}

export interface PairResult {
  id: string
  run_id: string
  query_id: string
  query_text: string
  intent: string
  domain: string
  query_attrs: Record<string, string>
  mindtrip_pass_rate: number
  wanderboat_pass_rate: number
  outcome: string
}

export interface Summary {
  outcomes: Record<string, number>
  mindtrip_avg_pass_rate: number
  wanderboat_avg_pass_rate: number
}

export interface PivotRow {
  pivot_val: string
  query_count: number
  outcomes: Record<string, number>
  mindtrip_pass_rate: number
  wanderboat_pass_rate: number
}

export interface QueryDetail {
  query: Record<string, unknown>
  assertions: Array<{ id: string; assertion_text: string; level: string; dimension: string }>
  responses: Record<string, { id: string; response_text: string; capture_method: string }>
  verdicts: Record<string, Array<{
    id: string; assertion_id: string; assertion_text: string;
    level: string; dimension: string; passed: number;
    judge_reasoning: string; judge_confidence: number
  }>>
  pair_result: PairResult | null
}

export const api = {
  runs: () => get<Run[]>('/runs'),
  createMockRun: () => post<{ run_id: string; status: string }>('/runs/mock'),
  run: (id: string) => get<Run>(`/runs/${id}`),
  summary: (runId: string) => get<Summary>(`/runs/${runId}/summary`),
  pivot: (runId: string, by: string) => get<PivotRow[]>(`/runs/${runId}/pivot?pivot_by=${by}`),
  pairs: (runId: string, params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : ''
    return get<PairResult[]>(`/runs/${runId}/pairs${qs}`)
  },
  queryDetail: (runId: string, queryId: string) =>
    get<QueryDetail>(`/runs/${runId}/queries/${queryId}`),
  queries: () => get<unknown[]>('/queries'),
  findings: (runId: string) => get<{
    findings: Array<{
      title: string; winner: 'mindtrip' | 'wanderboat' | 'neutral';
      intent: string; summary: string; evidence: string;
    }>;
    outcomes: Record<string, number>;
    avgs: { mt: number; wb: number };
  }>(`/runs/${runId}/findings`),
}
