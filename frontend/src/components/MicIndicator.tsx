/** Shows who is speaking (agent / patient / idle) and whether the mic is publishing. */

interface Props {
  agentSpeaking: boolean;
  patientSpeaking: boolean;
  micPublished: boolean;
}

export function MicIndicator({ agentSpeaking, patientSpeaking, micPublished }: Props) {
  const { label, cls } = agentSpeaking
    ? { label: "Assistant speaking…", cls: "dot agent" }
    : patientSpeaking
      ? { label: "Listening to you…", cls: "dot patient" }
      : { label: "Ready", cls: "dot idle" };

  return (
    <div className="mic-indicator">
      <span className={cls} />
      <span>{label}</span>
      <span className={micPublished ? "mic-badge on" : "mic-badge off"}>
        {micPublished ? "🎤 mic on" : "🎤 mic off"}
      </span>
    </div>
  );
}
