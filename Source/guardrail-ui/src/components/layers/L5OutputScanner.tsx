import { useState } from 'react'
import { X, Plus } from 'lucide-react'
import type { OutputConfig } from '@/types/guardrails'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { HelpTooltip } from '@/components/ui/help-tooltip'

interface Props {
  config: OutputConfig
  onChange: (v: OutputConfig) => void
}

export function L5OutputScanner({ config, onChange }: Props) {
  const [newCategory, setNewCategory] = useState('')
  const { harmful_content, pii_scanner, canary_check } = config

  const addCategory = () => {
    const trimmed = newCategory.trim()
    if (!trimmed || harmful_content.categories.includes(trimmed)) return
    onChange({
      ...config,
      harmful_content: {
        ...harmful_content,
        categories: [...harmful_content.categories, trimmed],
      },
    })
    setNewCategory('')
  }

  const removeCategory = (i: number) => {
    onChange({
      ...config,
      harmful_content: {
        ...harmful_content,
        categories: harmful_content.categories.filter((_, j) => j !== i),
      },
    })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2 mb-1">
          <span className="h-5 w-5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center">
            L5
          </span>
          <CardTitle>Output Scanner · output</CardTitle>
        </div>
        <CardDescription>
          Post-inference scanning for harmful content, PII, and canary-token leaks before the
          response reaches the client.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Harmful content */}
        <div className="space-y-3">
          <ToggleRow
            id="l5-harmful"
            label="Harmful Content Scan"
            description="Scan the response for the harmful-content categories below"
            tooltip="Runs a safety check on the model response before it is shown to the user."
            checked={harmful_content.enabled}
            onCheckedChange={(v) =>
              onChange({ ...config, harmful_content: { ...harmful_content, enabled: v } })
            }
          />
          {harmful_content.enabled && (
            <div className="space-y-2 pl-4 border-l-2 border-muted">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide inline-flex items-center gap-1.5">
                Categories
                <HelpTooltip text="Short category names passed to the harmful-content scanner, such as cbrn, self_harm, or hate." />
              </Label>
              <div className="flex flex-wrap gap-1.5">
                {harmful_content.categories.map((cat, i) => (
                  <span
                    key={i}
                    className="flex items-center gap-1 text-xs bg-muted rounded px-2 py-1 font-mono"
                  >
                    {cat}
                    <button
                      onClick={() => removeCategory(i)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Add category…"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addCategory()}
                  className="text-sm font-mono w-56"
                />
                <Button variant="outline" size="sm" onClick={addCategory} disabled={!newCategory.trim()}>
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="border-t" />

        {/* PII scanner */}
        <div className="space-y-4">
          <Label className="text-sm font-medium inline-flex items-center gap-1.5">
            PII Scanner
            <HelpTooltip text="PII means personally identifiable information, such as emails, phone numbers, SSNs, names, or similar identifiers." />
          </Label>
          <ToggleRow
            id="l5-pii-regex"
            label="Regex Matching"
            description="Detect PII in the response using regex patterns"
            tooltip="Regex means regular expression: a pattern matcher for structured text like emails, SSNs, or phone numbers."
            checked={pii_scanner.regex}
            onCheckedChange={(v) =>
              onChange({ ...config, pii_scanner: { ...pii_scanner, regex: v } })
            }
          />
          <ToggleRow
            id="l5-pii-ner"
            label="NER Matching"
            description="Detect PII using named-entity recognition (slower, more thorough)"
            tooltip="NER means named-entity recognition: model-based detection of names, places, organizations, and similar entities."
            checked={pii_scanner.ner}
            onCheckedChange={(v) => onChange({ ...config, pii_scanner: { ...pii_scanner, ner: v } })}
          />
        </div>

        <div className="border-t" />

        {/* Canary check */}
        <ToggleRow
          id="l5-canary"
          label="Canary Check"
          description="Block the response if a system-prompt canary token appears in it (prompt extraction)"
          tooltip="A canary token is a secret marker placed in hidden instructions. If it appears in output, the model leaked protected prompt text."
          checked={canary_check.enabled}
          onCheckedChange={(v) => onChange({ ...config, canary_check: { enabled: v } })}
        />
      </CardContent>
    </Card>
  )
}

function ToggleRow({
  id,
  label,
  description,
  tooltip,
  checked,
  onCheckedChange,
}: {
  id: string
  label: string
  description: string
  tooltip?: string
  checked: boolean
  onCheckedChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="space-y-0.5">
        <Label htmlFor={id} className="text-sm font-medium cursor-pointer">
          {label}
          {tooltip && (
            <span className="ml-1.5">
              <HelpTooltip text={tooltip} />
            </span>
          )}
        </Label>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  )
}
