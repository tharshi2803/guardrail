export interface DemoTrace {
  question: string
  session_id: string
  input: {
    normalized: string
    blocked: boolean
    reason_code: string | null
    layer: string | null
    severity: string | null
    scores: Record<string, number>
    latency_ms: number | null
  }
  llm: { reached: boolean; raw_output: string | null }
  output: {
    evaluated: boolean
    final_output: string | null
    blocked: boolean
    action: string | null
    reason_code: string | null
    redacted: boolean
    latency_ms: number | null
  }
  verdict: 'answered' | 'blocked_input' | 'blocked_output'
}

export interface HealthStatus {
  doc_count: number
  guardrails_active: boolean
  status: string
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(`Health check failed (${res.status})`)
  return res.json()
}

export async function runDemo(question: string, sessionId: string): Promise<DemoTrace> {
  const res = await fetch('/api/demo/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // top_k intentionally omitted — the backend applies its single TOP_K config knob.
    body: JSON.stringify({ question, session_id: sessionId }),
  })
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const j = await res.json()
      if (j.detail) msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* keep generic message */
    }
    throw new Error(msg)
  }
  return res.json()
}
