/**
 * Staff view: browse intake sessions and inspect each one's generated report, cost/performance
 * summary, and full transcript. All data comes from the staff-gated API (X-Staff-Secret).
 *
 * PHI: report + transcript are clinical content — this view is for authorized staff only.
 */
import { useCallback, useEffect, useState } from "react";
import {
  getReportMarkdown,
  getSummary,
  getTranscript,
  listSessions,
  type SessionRow,
  type SessionSummary,
  type TranscriptTurn,
} from "../lib/staff";

type Tab = "report" | "summary" | "transcript";

const SECRET_KEY = "opd_staff_secret";

export function Sessions() {
  const [secret, setSecret] = useState<string>(() => localStorage.getItem(SECRET_KEY) ?? "");
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("report");
  const [error, setError] = useState<string | null>(null);

  const [report, setReport] = useState<string>("");
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [transcript, setTranscript] = useState<TranscriptTurn[]>([]);
  const [loading, setLoading] = useState(false);

  const loadSessions = useCallback(async () => {
    setError(null);
    try {
      localStorage.setItem(SECRET_KEY, secret);
      setSessions(await listSessions(secret));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [secret]);

  // Load the data for the active tab whenever the selection or tab changes.
  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        if (tab === "report") setReport(await getReportMarkdown(selected, secret));
        else if (tab === "summary") setSummary(await getSummary(selected, secret));
        else setTranscript(await getTranscript(selected, secret));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, tab, secret]);

  return (
    <div className="staff">
      <div className="staff-auth">
        <label className="field">
          <span>Staff secret</span>
          <input
            type="password"
            value={secret}
            placeholder="STAFF_AUTH_SECRET"
            onChange={(e) => setSecret(e.target.value)}
          />
        </label>
        <button onClick={loadSessions} disabled={!secret}>
          Load sessions
        </button>
      </div>
      {error && <p className="error">{error}</p>}

      <div className="staff-body">
        <aside className="session-list">
          <h3>Sessions ({sessions.length})</h3>
          {sessions.length === 0 && <p className="muted">Enter the staff secret and load.</p>}
          <ul>
            {sessions.map((s) => (
              <li
                key={s.session_id}
                className={s.session_id === selected ? "active" : ""}
                onClick={() => setSelected(s.session_id)}
              >
                <span className="sid">{s.session_id}</span>
                <span className="meta">
                  {s.language} · {s.pipeline} · {s.status}
                  {s.urgent_flag ? " · 🚨" : ""}
                </span>
              </li>
            ))}
          </ul>
        </aside>

        <section className="session-detail">
          {!selected ? (
            <p className="muted">Select a session to view its report, summary, and transcript.</p>
          ) : (
            <>
              <div className="tabs">
                {(["report", "summary", "transcript"] as Tab[]).map((t) => (
                  <button
                    key={t}
                    className={t === tab ? "tab active" : "tab"}
                    onClick={() => setTab(t)}
                  >
                    {t === "report" ? "Report" : t === "summary" ? "Summary & cost" : "Transcript"}
                  </button>
                ))}
              </div>

              {loading && <p className="muted">Loading…</p>}

              {!loading && tab === "report" && <pre className="report-md">{report}</pre>}
              {!loading && tab === "summary" && summary && <SummaryView s={summary} />}
              {!loading && tab === "transcript" && <TranscriptList turns={transcript} />}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function money(v: number): string {
  return `$${v.toFixed(6)}`;
}

function SummaryView({ s }: { s: SessionSummary }) {
  const c = s.components;
  return (
    <div className="summary">
      <div className="metrics">
        <Metric label="Duration" value={`${s.duration_seconds}s (${s.duration_minutes} min)`} />
        <Metric label="Turns" value={String(s.turns)} />
        <Metric label="Completion" value={`${Math.round(s.completion_rate * 100)}%`} />
        <Metric
          label="Median latency"
          value={s.median_e2e_latency_ms != null ? `${s.median_e2e_latency_ms} ms` : "—"}
        />
        <Metric label="Total cost" value={money(s.total_cost_usd)} highlight />
        {s.urgent_flag && <Metric label="URGENT" value={s.urgent_reason ?? "yes"} urgent />}
      </div>

      <table className="cost-table">
        <thead>
          <tr>
            <th>Component</th>
            <th>Model</th>
            <th>Usage</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>STT</td>
            <td>{c.stt.model}</td>
            <td>{c.stt.audio_seconds} s</td>
            <td>{money(c.stt.cost_usd)}</td>
          </tr>
          <tr>
            <td>LLM</td>
            <td>{c.llm.model}</td>
            <td>
              in {c.llm.input_tokens} / out {c.llm.output_tokens} / cached {c.llm.cached_tokens} tok
            </td>
            <td>{money(c.llm.cost_usd)}</td>
          </tr>
          <tr>
            <td>TTS</td>
            <td>{c.tts.model}</td>
            <td>{c.tts.characters} chars</td>
            <td>{money(c.tts.cost_usd)}</td>
          </tr>
          <tr>
            <td>LiveKit</td>
            <td>livekit/cloud</td>
            <td>{c.livekit.minutes} min</td>
            <td>{money(c.livekit.cost_usd)}</td>
          </tr>
          <tr className="total">
            <td colSpan={3}>Total</td>
            <td>{money(s.total_cost_usd)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function Metric({
  label,
  value,
  highlight,
  urgent,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  urgent?: boolean;
}) {
  return (
    <div className={`metric${highlight ? " highlight" : ""}${urgent ? " urgent" : ""}`}>
      <span className="m-label">{label}</span>
      <span className="m-value">{value}</span>
    </div>
  );
}

function TranscriptList({ turns }: { turns: TranscriptTurn[] }) {
  if (turns.length === 0) return <p className="muted">No transcript captured.</p>;
  return (
    <div className="transcript">
      {turns.map((t) => (
        <div key={t.seq} className={`bubble ${t.role === "patient" ? "patient" : "agent"}`}>
          <span className="who">{t.role === "patient" ? "Patient" : "Dhara"}</span>
          <span className="text">{t.text}</span>
        </div>
      ))}
    </div>
  );
}
