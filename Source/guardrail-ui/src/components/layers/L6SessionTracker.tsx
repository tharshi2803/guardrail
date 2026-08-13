import type { SessionConfig } from '@/types/guardrails'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { HelpTooltip } from '@/components/ui/help-tooltip'

interface Props {
  config: SessionConfig
  onChange: (v: SessionConfig) => void
}

export function L6SessionTracker({ config, onChange }: Props) {
  const setRate = (key: 'rpm' | 'tpm', raw: string) => {
    const val = parseInt(raw)
    if (!isNaN(val) && val > 0) {
      onChange({ ...config, rate_limit: { ...config.rate_limit, [key]: val } })
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2 mb-1">
          <span className="h-5 w-5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center">
            L6
          </span>
          <CardTitle>Session Tracker · session</CardTitle>
        </div>
        <CardDescription>
          Per-session rate limiting and suspicion decay. Requests beyond the limits are throttled;
          accumulated suspicion decays over the configured window.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <div>
          <Label className="text-sm font-medium mb-3 inline-flex items-center gap-1.5">
            Rate Limits
            <HelpTooltip text="Limits applied per session to slow repeated or high-volume requests before they stress the backend." />
          </Label>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label
                htmlFor="l6-rpm"
                className="text-xs text-muted-foreground font-normal inline-flex items-center gap-1.5"
              >
                Requests / Minute
                <HelpTooltip text="RPM: the maximum number of requests this session may send each minute." />
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="l6-rpm"
                  type="number"
                  min={1}
                  value={config.rate_limit.rpm}
                  onChange={(e) => setRate('rpm', e.target.value)}
                  className="w-28 font-mono"
                />
                <span className="text-xs text-muted-foreground">req/min</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label
                htmlFor="l6-tpm"
                className="text-xs text-muted-foreground font-normal inline-flex items-center gap-1.5"
              >
                Tokens / Minute
                <HelpTooltip text="TPM: the maximum amount of text, measured in model tokens, this session may process each minute." />
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="l6-tpm"
                  type="number"
                  min={1}
                  value={config.rate_limit.tpm}
                  onChange={(e) => setRate('tpm', e.target.value)}
                  className="w-32 font-mono"
                />
                <span className="text-xs text-muted-foreground">tok/min</span>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t" />

        <div className="space-y-1.5">
          <Label htmlFor="l6-decay" className="inline-flex items-center gap-1.5">
            Suspicion Decay
            <HelpTooltip text="How long it takes accumulated risk signals for a session to fade back toward zero." />
          </Label>
          <p className="text-xs text-muted-foreground">
            Seconds over which a session's accumulated suspicion score decays back to zero
          </p>
          <div className="flex items-center gap-2">
            <Input
              id="l6-decay"
              type="number"
              min={1}
              value={config.suspicion_decay_seconds}
              onChange={(e) => {
                const val = parseInt(e.target.value)
                if (!isNaN(val) && val > 0) onChange({ ...config, suspicion_decay_seconds: val })
              }}
              className="w-28 font-mono"
            />
            <span className="text-xs text-muted-foreground">seconds</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
