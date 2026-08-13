import { useEffect, useState } from 'react'
import { CheckCircle2, Loader2, AlertCircle, Save, RotateCcw } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import type { GuardrailsConfig } from '@/types/guardrails'
import { getRules, putRules, reloadRules, ApiError } from '@/lib/api'
import { L1Normaliser } from './layers/L1Normaliser'
import { L2Classifier } from './layers/L2Classifier'
import { L3PromptGuard } from './layers/L3PromptGuard'
import { L4RagSanitiser } from './layers/L4RagSanitiser'
import { L5OutputScanner } from './layers/L5OutputScanner'
import { L6SessionTracker } from './layers/L6SessionTracker'

const tabs = [
  {
    id: 'l1',
    label: 'L1 · Normaliser',
    phase: 'pre',
    tooltip: 'Pre-processes user input so obfuscated text is easier to inspect.',
  },
  {
    id: 'l2',
    label: 'L2 · Classifier',
    phase: 'pre',
    tooltip: 'Scores the user request for attack or safety categories before retrieval.',
  },
  {
    id: 'l3',
    label: 'L3 · Prompt Guard',
    phase: 'pre',
    tooltip: 'Controls the hidden system prompt and instructions sent with each request.',
  },
  {
    id: 'l4',
    label: 'L4 · RAG Sanitiser',
    phase: 'pre',
    tooltip: 'Checks retrieved database chunks before they are added to model context.',
  },
  {
    id: 'l5',
    label: 'L5 · Output Scanner',
    phase: 'post',
    tooltip: 'Scans the model response before it is returned to the user.',
  },
  {
    id: 'l6',
    label: 'L6 · Session Tracker',
    phase: 'post',
    tooltip: 'Tracks per-session usage and accumulated risk over time.',
  },
] as const

type LoadState = 'loading' | 'ready' | 'error'
type SaveStatus = 'idle' | 'saving' | 'saved'

export function RulesEditor() {
  const [config, setConfig] = useState<GuardrailsConfig | null>(null)
  const [saved, setSaved] = useState<GuardrailsConfig | null>(null)
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [status, setStatus] = useState<SaveStatus>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)
  const [reloading, setReloading] = useState(false)

  useEffect(() => {
    void load()
  }, [])

  async function load() {
    setLoadState('loading')
    setLoadError(null)
    try {
      const file = await getRules()
      setConfig(file.guardrails)
      setSaved(file.guardrails)
      setLoadState('ready')
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Failed to load rules.')
      setLoadState('error')
    }
  }

  const isDirty = config !== null && JSON.stringify(config) !== JSON.stringify(saved)

  async function handleSave() {
    if (!config) return
    setStatus('saving')
    setSaveError(null)
    try {
      const file = await putRules({ guardrails: config })
      setConfig(file.guardrails)
      setSaved(file.guardrails)
      setStatus('saved')
      setTimeout(() => setStatus('idle'), 2000)
    } catch (e) {
      setSaveError(e instanceof ApiError ? e.message : 'Save failed.')
      setStatus('idle')
    }
  }

  function discard() {
    setConfig(saved)
    setSaveError(null)
  }

  // Ask the backend to re-read guardrails.yaml from disk, then refresh the editor.
  async function handleReload() {
    if (isDirty && !window.confirm('Reload from disk? Unsaved changes will be discarded.')) return
    setReloading(true)
    setSaveError(null)
    try {
      await reloadRules()
      await load()
    } catch (e) {
      setSaveError(e instanceof ApiError ? e.message : 'Reload failed.')
    } finally {
      setReloading(false)
    }
  }

  // Update one section (input/output/session) of the config.
  function update<K extends keyof GuardrailsConfig>(section: K, value: GuardrailsConfig[K]) {
    setConfig((prev) => (prev ? { ...prev, [section]: value } : prev))
  }

  if (loadState === 'loading') {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading rules…
      </div>
    )
  }

  if (loadState === 'error' || !config) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center px-8">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <p className="text-sm text-muted-foreground max-w-sm">{loadError}</p>
        <Button variant="outline" size="sm" onClick={() => void load()}>
          <RotateCcw className="mr-2 h-3.5 w-3.5" /> Retry
        </Button>
      </div>
    )
  }

  const { input, output, session } = config

  return (
    <div className="flex flex-col h-full">
      <div className="h-14 flex items-center gap-3 px-8 border-b shrink-0">
        <h1 className="text-base font-semibold">Rules Editor</h1>
        <span className="text-sm text-muted-foreground">·</span>
        <span className="text-sm text-muted-foreground">6 layers</span>

        <div className="flex items-center gap-3 ml-auto">
          {saveError && (
            <span className="flex items-center gap-1.5 text-xs text-destructive max-w-md truncate">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" /> {saveError}
            </span>
          )}
          {status === 'saved' && (
            <span className="flex items-center gap-1.5 text-sm text-emerald-600">
              <CheckCircle2 className="h-4 w-4" /> Saved
            </span>
          )}
          {isDirty && status !== 'saving' && (
            <Button variant="ghost" size="sm" onClick={discard}>
              Discard
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleReload}
            disabled={reloading || status === 'saving'}
            title="Re-read guardrails.yaml from disk"
          >
            <RotateCcw className={`mr-2 h-3.5 w-3.5 ${reloading ? 'animate-spin' : ''}`} />
            {reloading ? 'Reloading…' : 'Reload'}
          </Button>
          <Button onClick={handleSave} disabled={!isDirty || status === 'saving'} size="sm">
            {status === 'saving' ? (
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="mr-2 h-3.5 w-3.5" />
            )}
            {status === 'saving' ? 'Saving…' : 'Save Changes'}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-8">
        <Tabs defaultValue="l1">
          <TabsList className="w-full mb-6 h-auto flex-wrap gap-0.5">
            {tabs.map((tab) => (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                className="flex items-center gap-1.5 text-xs"
                title={tab.tooltip}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    tab.phase === 'pre' ? 'bg-emerald-500' : 'bg-amber-500'
                  }`}
                />
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="l1">
            <L1Normaliser
              config={input.normaliser}
              onChange={(v) => update('input', { ...input, normaliser: v })}
            />
          </TabsContent>
          <TabsContent value="l2">
            <L2Classifier
              config={input.classifier}
              onChange={(v) => update('input', { ...input, classifier: v })}
            />
          </TabsContent>
          <TabsContent value="l3">
            <L3PromptGuard
              value={input.system_prompt_template}
              onChange={(v) => update('input', { ...input, system_prompt_template: v })}
            />
          </TabsContent>
          <TabsContent value="l4">
            <L4RagSanitiser
              config={input.rag_sanitiser}
              onChange={(v) => update('input', { ...input, rag_sanitiser: v })}
            />
          </TabsContent>
          <TabsContent value="l5">
            <L5OutputScanner config={output} onChange={(v) => update('output', v)} />
          </TabsContent>
          <TabsContent value="l6">
            <L6SessionTracker config={session} onChange={(v) => update('session', v)} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
