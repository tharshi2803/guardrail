import { useState } from 'react'
import { X, Plus } from 'lucide-react'
import type { RagSanitiserConfig } from '@/types/guardrails'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { HelpTooltip } from '@/components/ui/help-tooltip'

interface Props {
  config: RagSanitiserConfig
  onChange: (v: RagSanitiserConfig) => void
}

export function L4RagSanitiser({ config, onChange }: Props) {
  const [newPattern, setNewPattern] = useState('')

  const addPattern = () => {
    const trimmed = newPattern.trim()
    if (!trimmed || config.patterns.includes(trimmed)) return
    onChange({ ...config, patterns: [...config.patterns, trimmed] })
    setNewPattern('')
  }

  const removePattern = (i: number) => {
    onChange({ ...config, patterns: config.patterns.filter((_, j) => j !== i) })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold flex items-center justify-center">
                L4
              </span>
              <CardTitle className="inline-flex items-center gap-1.5">
                RAG Sanitiser · input
                <HelpTooltip text="RAG means Retrieval-Augmented Generation: the app retrieves database records and gives them to the model as context." />
              </CardTitle>
              <Badge variant={config.enabled ? 'success' : 'muted'}>
                {config.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>
            <CardDescription>
              Per-chunk injection scanning applied to every chunk retrieved from Chroma before
              context assembly. Matching chunks are rejected.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 pt-1">
            <Label htmlFor="l4-enabled" className="text-sm text-muted-foreground">
              Layer active
            </Label>
            <Switch
              id="l4-enabled"
              checked={config.enabled}
              onCheckedChange={(v) => onChange({ ...config, enabled: v })}
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="l4-threshold" className="inline-flex items-center gap-1.5">
            Injection Threshold
            <HelpTooltip text="The minimum risk score, from 0 to 1, required to reject a retrieved chunk as prompt-injection content." />
          </Label>
          <p className="text-xs text-muted-foreground">
            Reject a chunk if its injection score meets or exceeds this value (0–1)
          </p>
          <Input
            id="l4-threshold"
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={config.injection_threshold}
            onChange={(e) => {
              const val = parseFloat(e.target.value)
              if (!isNaN(val)) {
                onChange({ ...config, injection_threshold: Math.min(1, Math.max(0, val)) })
              }
            }}
            disabled={!config.enabled}
            className="w-28 font-mono"
          />
        </div>

        <div className="border-t" />

        <div className="space-y-2">
          <Label className="inline-flex items-center gap-1.5">
            Injection Patterns
            <HelpTooltip text="Literal phrases searched inside retrieved records. Matching chunks are removed before the model sees them." />
          </Label>
          <p className="text-xs text-muted-foreground">
            String patterns scanned in each RAG chunk; matching chunks are rejected
          </p>
          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {config.patterns.map((pattern, i) => (
              <div key={i} className="flex items-center gap-2">
                <code className="flex-1 text-xs bg-muted rounded px-3 py-1.5 font-mono truncate">
                  {pattern}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removePattern(i)}
                  disabled={!config.enabled}
                  className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Input
              placeholder="Add pattern…"
              value={newPattern}
              onChange={(e) => setNewPattern(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addPattern()}
              disabled={!config.enabled}
              className="text-sm font-mono"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={addPattern}
              disabled={!config.enabled || !newPattern.trim()}
            >
              <Plus className="h-3.5 w-3.5 mr-1" /> Add
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
