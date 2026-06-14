/** Shows who is speaking: the agent (talking), the patient (listening), or idle. */

interface Props {
  agentSpeaking: boolean;
  patientSpeaking: boolean;
}

export function MicIndicator({ agentSpeaking, patientSpeaking }: Props) {
  const { label, cls } = agentSpeaking
    ? { label: "Assistant speaking…", cls: "dot agent" }
    : patientSpeaking
      ? { label: "Listening to you…", cls: "dot patient" }
      : { label: "Ready", cls: "dot idle" };

  return (
    <div className="mic-indicator">
      <span className={cls} />
      <span>{label}</span>
    </div>
  );
}
