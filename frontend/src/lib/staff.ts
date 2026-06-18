/**
 * Staff API client — wraps the staff-gated endpoints (sessions list, report, per-session
 * summary, transcript). All calls send the shared `X-Staff-Secret` header.
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export interface SessionRow {
  session_id: string;
  language: string;
  pipeline: string;
  status: string;
  urgent_flag: boolean;
  created_at: string | null;
}

export interface TranscriptTurn {
  seq: number;
  role: string; // "patient" | "agent"
  text: string;
}

export interface ComponentUsage {
  model: string;
  cost_usd: number;
  audio_seconds?: number;
  characters?: number;
  minutes?: number;
  input_tokens?: number;
  output_tokens?: number;
  cached_tokens?: number;
}

export interface SessionSummary {
  session_id: string;
  pipeline: string;
  language: string;
  status: string;
  urgent_flag: boolean;
  urgent_reason: string | null;
  duration_seconds: number;
  duration_minutes: number;
  turns: number;
  median_e2e_latency_ms: number | null;
  completion_rate: number;
  total_cost_usd: number;
  components: {
    stt: ComponentUsage;
    llm: ComponentUsage;
    tts: ComponentUsage;
    livekit: ComponentUsage;
  };
  transcript: TranscriptTurn[];
}

async function staffGet(path: string, secret: string): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, { headers: { "X-Staff-Secret": secret } });
  if (res.status === 401) throw new Error("Invalid staff secret.");
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res;
}

export async function listSessions(secret: string): Promise<SessionRow[]> {
  return (await staffGet("/api/sessions", secret)).json();
}

export async function getReportMarkdown(id: string, secret: string): Promise<string> {
  return (await staffGet(`/api/sessions/${encodeURIComponent(id)}/report.md`, secret)).text();
}

export async function getSummary(id: string, secret: string): Promise<SessionSummary> {
  return (await staffGet(`/api/sessions/${encodeURIComponent(id)}/summary`, secret)).json();
}

export async function getTranscript(id: string, secret: string): Promise<TranscriptTurn[]> {
  return (await staffGet(`/api/sessions/${encodeURIComponent(id)}/transcript`, secret)).json();
}
