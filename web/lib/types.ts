/** The shapes the CLI already writes to B2. The frontend is a renderer over
 *  these, not a second source of truth — no pipeline logic crosses into here. */

export type Attempt = {
  n: number;
  provider: string;
  model: string;
  status: string;
  asset_uri: string | null;
  sha256: string | null;
  cost_usd: number | null;
  parent_run_id: string | null;
  note: string | null;
};

export type Claim = { spoken: string; fact_id: string; evidence: string };

export type Block = {
  n: number;
  status: string;
  narration: string;
  fact_ids: string[];
  prompt: string | null;
  still_uri: string | null;
  clip_uri: string | null;
  voice_uri: string | null;
  voice_duration_s: number | null;
  attempts: Attempt[];
  policy_results: Record<string, unknown>[];
  claims: Claim[];
};

export type Event = {
  ts: string;
  kind: string;
  message: string;
  block: number | null;
  rule_id: string | null;
  provider: string | null;
  model: string | null;
  cost_usd: number | null;
};

export type Source = {
  kind: string;
  value: string;
  dataset: string | null;
  row_id: string | null;
  page: number | null;
};

export type Fact = { id: string; text: string; sources: Source[] };

export type RunState = {
  run_id: string;
  story: string;
  status: string;
  parent_run_id: string | null;
  created_at: string;
  facts: Fact[];
  art_direction: Record<string, unknown>;
  blocks: Block[];
  events: Event[];
  approval: { approver: string; ts: string } | null;
  final: Record<string, unknown> | null;
};
