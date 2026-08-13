// Mirrors guardrails.yaml exactly — the backend (ragqaapp) is the canonical
// source of truth. GET/PUT /rules round-trip a { guardrails: GuardrailsConfig }.

export interface NormaliserConfig {
  unicode_nfkc: boolean
  decode_base64: boolean
  max_tokens: number
}

export interface ClassifierThresholds {
  prompt_injection: number
  jailbreak_roleplay: number
  harmful_content: number
  pii_exfil: number
  dos: number
}

export interface ClassifierConfig {
  backend: string
  thresholds: ClassifierThresholds
}

export interface RagSanitiserConfig {
  enabled: boolean
  injection_threshold: number
  patterns: string[]
}

export interface InputConfig {
  normaliser: NormaliserConfig
  classifier: ClassifierConfig
  rag_sanitiser: RagSanitiserConfig
  system_prompt_template: string
}

export interface HarmfulContentConfig {
  enabled: boolean
  categories: string[]
}

export interface PiiScannerConfig {
  regex: boolean
  ner: boolean
}

export interface CanaryCheckConfig {
  enabled: boolean
}

export interface OutputConfig {
  harmful_content: HarmfulContentConfig
  pii_scanner: PiiScannerConfig
  canary_check: CanaryCheckConfig
}

export interface RateLimitConfig {
  rpm: number
  tpm: number
}

export interface SessionConfig {
  rate_limit: RateLimitConfig
  suspicion_decay_seconds: number
}

export interface GuardrailsConfig {
  input: InputConfig
  output: OutputConfig
  session: SessionConfig
}

/** Full guardrails.yaml document — the shape GET/PUT /rules accept. */
export interface RulesFile {
  guardrails: GuardrailsConfig
}
