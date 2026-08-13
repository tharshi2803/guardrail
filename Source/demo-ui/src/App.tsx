import { useState, useEffect, type ReactNode } from 'react'
import { runDemo, fetchHealth, type DemoTrace } from './api'

type Pill = { text: string; tone: 'green' | 'red' | 'amber' | 'blue' | 'gray' }

function inputPill(t: DemoTrace): Pill {
  if (t.input.blocked) return { text: `BLOCKED · ${t.input.layer ?? 'input'}`, tone: 'red' }
  if (t.input.normalized !== t.question) return { text: 'NORMALISED', tone: 'blue' }
  return { text: 'PASSED', tone: 'green' }
}

function llmPill(t: DemoTrace): Pill {
  return t.llm.reached ? { text: 'GENERATED', tone: 'blue' } : { text: 'SKIPPED', tone: 'gray' }
}

function outputPill(t: DemoTrace): Pill {
  if (!t.output.evaluated) return { text: 'SKIPPED', tone: 'gray' }
  if (t.output.blocked) return { text: `BLOCKED · ${t.output.reason_code ?? 'L5'}`, tone: 'red' }
  if (t.output.redacted) return { text: 'SANITISED', tone: 'amber' }
  return { text: 'ALLOWED', tone: 'green' }
}

const VERDICT: Record<DemoTrace['verdict'], Pill> = {
  answered: { text: 'Answered', tone: 'green' },
  blocked_input: { text: 'Blocked at input', tone: 'red' },
  blocked_output: { text: 'Blocked at output', tone: 'red' },
}

function Badge({ pill }: { pill: Pill }) {
  return <span className={`pill ${pill.tone}`}>{pill.text}</span>
}

function Stage({
  index,
  title,
  subtitle,
  pill,
  dim,
  children,
}: {
  index: number
  title: string
  subtitle: string
  pill: Pill
  dim?: boolean
  children: ReactNode
}) {
  return (
    <div className={`stage${dim ? ' dim' : ''}`}>
      <div className="stage-head">
        <span className="stage-num">{index}</span>
        <div className="stage-titles">
          <div className="stage-title">{title}</div>
          <div className="stage-sub">{subtitle}</div>
        </div>
        <Badge pill={pill} />
      </div>
      <div className="stage-body">{children}</div>
    </div>
  )
}

function Arrow({ dim }: { dim?: boolean }) {
  return <div className={`arrow${dim ? ' dim' : ''}`}>↓</div>
}

function Box({ text, mono = true }: { text: string; mono?: boolean }) {
  return <pre className={mono ? 'box mono' : 'box'}>{text}</pre>
}

export default function App() {
  const [question, setQuestion] = useState('What medication is used to treat Asthma?')
  const [trace, setTrace] = useState<DemoTrace | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  type DataStatus = 'checking' | 'empty' | 'ready' | 'error'
  const [dataStatus, setDataStatus] = useState<DataStatus>('checking')
  const [docCount, setDocCount] = useState(0)
  const [statusChecking, setStatusChecking] = useState(false)

  async function checkStatus() {
    setStatusChecking(true)
    try {
      const h = await fetchHealth()
      setDocCount(h.doc_count)
      setDataStatus(h.doc_count > 0 ? 'ready' : 'empty')
    } catch {
      setDataStatus('error')
    } finally {
      setStatusChecking(false)
    }
  }

  useEffect(() => { checkStatus() }, [])

  function clear() {
    setQuestion('')
    setTrace(null)
    setError(null)
  }

  async function run() {
    setLoading(true)
    setError(null)
    try {
      // Fresh session each run so rate-limit / suspicion state doesn't carry over.
      const sid = 'demo-' + Math.random().toString(36).slice(2, 8)
      setTrace(await runDemo(question, sid))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
      setTrace(null)
    } finally {
      setLoading(false)
    }
  }

  const scores = trace ? Object.entries(trace.input.scores) : []
  const inputSkipped = !!trace && trace.input.blocked

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>Guardrail Pipeline</h1>
          <p className="muted">Watch a question flow through the six-layer guardrail.</p>
        </div>
        <a className="link" href="http://localhost:8081" target="_blank" rel="noreferrer">
          Rules editor ↗
        </a>
      </header>

      <div className={`status-bar ${dataStatus}`}>
        <span>
          {dataStatus === 'checking' && 'Checking data status…'}
          {dataStatus === 'empty' && 'No data loaded yet — ingestion may still be running.'}
          {dataStatus === 'ready' && `Data ready — ${docCount.toLocaleString()} chunks loaded.`}
          {dataStatus === 'error' && 'Cannot reach API — is the backend running?'}
        </span>
        <button className="btn-ghost" onClick={checkStatus} disabled={statusChecking}>
          {statusChecking ? 'Checking…' : 'Refresh'}
        </button>
      </div>

      <div className="composer">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) run()
          }}
          rows={3}
          placeholder="Ask a question about the patient dataset…"
        />
        <div className="composer-row">
          <span className="muted small">⌘/Ctrl + Enter to run</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-ghost" onClick={clear} disabled={loading}>
              Clear
            </button>
            <button onClick={run} disabled={loading || !question.trim()}>
              {loading ? 'Running…' : 'Run'}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {trace && (
        <>
          <div className="verdict">
            <span className="muted small">Verdict</span>
            <Badge pill={VERDICT[trace.verdict]} />
          </div>

          <Stage
            index={1}
            title="Question"
            subtitle="raw user input"
            pill={{ text: 'INPUT', tone: 'gray' }}
          >
            <Box text={trace.question} />
          </Stage>

          <Arrow />

          <Stage
            index={2}
            title="Input Guardrails"
            subtitle="L6 rate · L1 normalise · L2 classify"
            pill={inputPill(trace)}
          >
            <div className="label">Normalised input</div>
            <Box text={trace.input.normalized} />
            {scores.length > 0 && (
              <div className="scores">
                {scores.map(([k, v]) => (
                  <span key={k} className="score">
                    {k} <b>{v.toFixed(2)}</b>
                  </span>
                ))}
              </div>
            )}
            {trace.input.blocked && (
              <div className="note red">
                Blocked by <b>{trace.input.layer}</b> — {trace.input.reason_code} (
                {trace.input.severity})
              </div>
            )}
          </Stage>

          <Arrow dim={inputSkipped} />

          <Stage
            index={3}
            title="LLM (Claude)"
            subtitle="answer generated from retrieved context"
            pill={llmPill(trace)}
            dim={!trace.llm.reached}
          >
            {trace.llm.reached ? (
              <Box text={trace.llm.raw_output ?? ''} />
            ) : (
              <div className="note muted">Skipped — request blocked before the LLM.</div>
            )}
          </Stage>

          <Arrow dim={!trace.output.evaluated} />

          <Stage
            index={4}
            title="Output Guardrails"
            subtitle="L5 canary · harmful content · PII scan"
            pill={outputPill(trace)}
            dim={!trace.output.evaluated}
          >
            {!trace.output.evaluated ? (
              <div className="note muted">Skipped — nothing to scan.</div>
            ) : trace.output.blocked ? (
              <div className="note red">
                Response blocked — {trace.output.reason_code}
              </div>
            ) : (
              <>
                {trace.output.redacted && (
                  <div className="note amber">PII detected and redacted before returning.</div>
                )}
                <div className="label">Final output</div>
                <Box text={trace.output.final_output ?? ''} />
              </>
            )}
          </Stage>
        </>
      )}
    </div>
  )
}
