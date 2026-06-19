/**
 * Patient intake view: pick a language, connect, and have a spoken conversation with the
 * agent. Shows live captions, a speaking/listening indicator, and the captured-fields panel.
 */
import { useState } from "react";
import { FieldPanel } from "../components/FieldPanel";
import { LanguagePicker } from "../components/LanguagePicker";
import { MicIndicator } from "../components/MicIndicator";
import { PushToTalkButton } from "../components/PushToTalkButton";
import { TranscriptView } from "../components/TranscriptView";
import { useIntakeRoom } from "../lib/livekit";

export function Intake() {
  const [language, setLanguage] = useState("en");
  const {
    status,
    error,
    captions,
    fields,
    urgent,
    completed,
    handoff,
    agentSpeaking,
    patientSpeaking,
    micPublished,
    recording,
    connect,
    disconnect,
    pttDown,
    pttUp,
  } = useIntakeRoom();

  const connected = status === "connected";
  const pttDisabled = completed || handoff || Boolean(urgent) || agentSpeaking;

  return (
    <div className="intake">
      <header>
        <h1>OPD Intake Assistant</h1>
        <p className="disclaimer">
          Automated assistant — not a doctor. This conversation is recorded and transcribed for
          your care team. It does not provide diagnosis or treatment.
        </p>
      </header>

      {!connected ? (
        <div className="prejoin">
          <LanguagePicker value={language} onChange={setLanguage} disabled={status === "connecting"} />
          <button onClick={() => connect(language)} disabled={status === "connecting"}>
            {status === "connecting" ? "Connecting…" : "Start conversation"}
          </button>
          {error && <p className="error">Error: {error}</p>}
        </div>
      ) : (
        <div className="session">
          <div className="main">
            {urgent && (
              <div className="urgent-banner">
                ⚠️ Urgent concern noted ({urgent}). Please alert hospital staff right away.
              </div>
            )}
            {completed && (
              <div className="complete-banner">
                ✓ Intake complete. The doctor will review your summary.
              </div>
            )}
            {handoff && (
              <div className="complete-banner">
                A member of the hospital staff will assist you shortly.
              </div>
            )}
            <MicIndicator
              agentSpeaking={agentSpeaking}
              patientSpeaking={patientSpeaking}
              micPublished={micPublished}
            />
            {!completed && !handoff && (
              <PushToTalkButton
                recording={recording}
                disabled={pttDisabled}
                onDown={pttDown}
                onUp={pttUp}
              />
            )}
            {error && <p className="error">{error}</p>}
            <TranscriptView captions={captions} />
            <button className="end" onClick={disconnect}>
              End conversation
            </button>
          </div>
          <FieldPanel fields={fields} />
        </div>
      )}
    </div>
  );
}
