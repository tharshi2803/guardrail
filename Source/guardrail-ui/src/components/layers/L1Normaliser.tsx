import type { NormaliserConfig } from '@/types/guardrails'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { HelpTooltip } from '@/components/ui/help-tooltip'

interface Props {
  config: NormaliserConfig
  onChange: (v: NormaliserConfig) => void
}

export function L1Normaliser({ config, onChange }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2 mb-1">
          <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold flex items-center justify-center">
            L1
          </span>
          <CardTitle>Normaliser · input</CardTitle>
        </div>
        <CardDescription>
          Unicode NFKC normalization and Base64 decoding to neutralise encoding-based bypass attacks
          before classification.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <ToggleRow
          id="l1-nfkc"
          label="Unicode NFKC Normalization"
          description="Normalise unicode homoglyphs and confusable characters (NFKC) before processing"
          tooltip="NFKC is a Unicode normalization form that turns visually similar or compatibility characters into a standard representation, reducing obfuscated prompt attacks."
          checked={config.unicode_nfkc}
          onCheckedChange={(v) => onChange({ ...config, unicode_nfkc: v })}
        />
        <div className="border-t" />
        <ToggleRow
          id="l1-base64"
          label="Base64 Decoding"
          description="Detect and decode Base64-encoded payloads before downstream processing"
          tooltip="Base64 is a text encoding attackers can use to hide instructions. Decoding it lets the guardrails inspect the real message."
          checked={config.decode_base64}
          onCheckedChange={(v) => onChange({ ...config, decode_base64: v })}
        />
        <div className="border-t" />
        <div className="space-y-1.5">
          <Label htmlFor="l1-max-tokens" className="inline-flex items-center gap-1.5">
            Max Tokens
            <HelpTooltip text="Maximum input size allowed into the guardrail pipeline. Longer text is truncated before checks run." />
          </Label>
          <p className="text-xs text-muted-foreground">
            Inputs longer than this token budget are truncated before processing
          </p>
          <div className="flex items-center gap-2">
            <Input
              id="l1-max-tokens"
              type="number"
              min={1}
              value={config.max_tokens}
              onChange={(e) => {
                const v = parseInt(e.target.value)
                if (!isNaN(v) && v > 0) onChange({ ...config, max_tokens: v })
              }}
              className="w-28 font-mono"
            />
            <span className="text-xs text-muted-foreground">tokens</span>
          </div>
        </div>
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
