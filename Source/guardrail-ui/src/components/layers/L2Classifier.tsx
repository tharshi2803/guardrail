import type { ClassifierConfig, ClassifierThresholds } from '@/types/guardrails'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { HelpTooltip } from '@/components/ui/help-tooltip'

interface Props {
  config: ClassifierConfig
  onChange: (v: ClassifierConfig) => void
}

const THRESHOLDS: { key: keyof ClassifierThresholds; label: string; tooltip: string }[] = [
  {
    key: 'prompt_injection',
    label: 'Prompt Injection',
    tooltip: 'Attempts to override, ignore, or rewrite the system/developer instructions.',
  },
  {
    key: 'jailbreak_roleplay',
    label: 'Jailbreak / Roleplay',
    tooltip: 'Requests that ask the model to adopt an unrestricted persona or bypass policy.',
  },
  {
    key: 'harmful_content',
    label: 'Harmful Content',
    tooltip: 'Requests for dangerous, illegal, abusive, or otherwise unsafe content.',
  },
  {
    key: 'pii_exfil',
    label: 'PII Exfiltration',
    tooltip: 'Attempts to extract personally identifiable information from records or context.',
  },
  {
    key: 'dos',
    label: 'Denial of Service',
    tooltip: 'Inputs designed to exhaust resources, such as huge or repetitive requests.',
  },
]

export function L2Classifier({ config, onChange }: Props) {
  const setThreshold = (key: keyof ClassifierThresholds, raw: string) => {
    const val = parseFloat(raw)
    if (!isNaN(val)) {
      onChange({
        ...config,
        thresholds: { ...config.thresholds, [key]: Math.min(1, Math.max(0, val)) },
      })
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2 mb-1">
          <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold flex items-center justify-center">
            L2
          </span>
          <CardTitle>Classifier · input</CardTitle>
        </div>
        <CardDescription>
          LLM-based classifier that scores each request and blocks it when a category score meets or
          exceeds its threshold, before the request reaches the RAG pipeline.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="l2-backend" className="inline-flex items-center gap-1.5">
            Classifier Backend
            <HelpTooltip text="The model family used to score safety categories. It is separate from the model that writes the final answer." />
          </Label>
          <p className="text-xs text-muted-foreground">
            Fast, cheap model used for classification — not the answer LLM
          </p>
          <Input
            id="l2-backend"
            value={config.backend}
            onChange={(e) => onChange({ ...config, backend: e.target.value })}
            className="w-56 font-mono"
            placeholder="e.g. claude-haiku"
          />
        </div>

        <div className="border-t" />

        <div>
          <Label className="text-sm font-medium mb-3 inline-flex items-center gap-1.5">
            Block Thresholds
            <HelpTooltip text="A category score from 0 to 1 must meet or exceed this value before the request is blocked." />
          </Label>
          <div className="grid grid-cols-3 gap-4">
            {THRESHOLDS.map(({ key, label, tooltip }) => (
              <ThresholdField
                key={key}
                id={`l2-${key}`}
                label={label}
                tooltip={tooltip}
                value={config.thresholds[key]}
                onChange={(v) => setThreshold(key, v)}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ThresholdField({
  id,
  label,
  tooltip,
  value,
  onChange,
}: {
  id: string
  label: string
  tooltip: string
  value: number
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-sm font-medium">
        {label}
        <span className="ml-1.5">
          <HelpTooltip text={tooltip} />
        </span>
      </Label>
      <p className="text-xs text-muted-foreground">Block if score ≥ threshold</p>
      <Input
        id={id}
        type="number"
        min={0}
        max={1}
        step={0.01}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full font-mono"
      />
    </div>
  )
}
