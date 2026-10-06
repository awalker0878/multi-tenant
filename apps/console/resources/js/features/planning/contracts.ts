export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };
export interface Candidate { site_id: string; endpoint_id: string; generation_id: string }
export interface Finding { requirement: string; source: string; status: string; reason: string; remediation: string; mandatory: boolean }
export interface Result extends Candidate { platform: string; status: string; operationally_eligible: boolean; findings: Finding[]; expires_at: number; demand: Record<string,number> }
export interface Binding { plan_id: string; revision: number; digest: string; content_digest: string; valid_until: number; lane: string }
export interface Validity { current: boolean; holds: string[]; evaluated_at: number }
export interface PlanningRecord { id: string; candidates: Candidate[]; action?: string; method?: string; results?: Result[]; binding?: Binding; validity?: Validity; content?: { scope: {site_id:string}; action: string; lane: string; valid_until: number; input_fresh_until: number; holds: string[]; execution_ready: boolean; budgets: {downtime_seconds: number}; effects: {id: string; after: string[]; destructive: boolean; boundary: string; on_unknown: string}[]; recovery: Record<string,Json> } }
export interface Endpoint { endpoint_id: string; label: string; platform: string; generation_id: string | null; reason: string | null }
