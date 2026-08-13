import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { HelpTooltip } from '@/components/ui/help-tooltip'

interface Props {
  value: string
  onChange: (v: string) => void
}

export function L3PromptGuard({ value, onChange }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2 mb-1">
          <span className="h-5 w-5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold flex items-center justify-center">
            L3
          </span>
          <CardTitle>Prompt Guard · input</CardTitle>
        </div>
        <CardDescription>
          The hardened system prompt prepended before every request. Instruct the model to answer
          only from retrieved context and to treat override attempts as injection.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-1.5">
        <Label htmlFor="l3-template" className="inline-flex items-center gap-1.5">
          System Prompt Template
          <HelpTooltip text="The hidden instruction message sent before the user question. It sets the assistant's role and safety constraints." />
        </Label>
        <p className="text-xs text-muted-foreground">
          Sent as the system message on every query; supports multi-line text
        </p>
        <Textarea
          id="l3-template"
          rows={8}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="font-mono text-xs resize-y"
        />
      </CardContent>
    </Card>
  )
}
