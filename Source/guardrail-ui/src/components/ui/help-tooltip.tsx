import { CircleHelp } from 'lucide-react'

interface HelpTooltipProps {
  text: string
}

export function HelpTooltip({ text }: HelpTooltipProps) {
  return (
    <span
      className="inline-flex cursor-help align-middle text-muted-foreground hover:text-foreground"
      title={text}
      aria-label={text}
    >
      <CircleHelp className="h-3.5 w-3.5" aria-hidden="true" />
    </span>
  )
}
