/**
 * Live captured-fields panel. In Phase C this renders an empty placeholder; Phase D wires it
 * to real-time field updates pushed from the agent (via the LiveKit data channel) as
 * `save_intake_field` runs.
 */

export interface CapturedField {
  id: string;
  label: string;
  value: string;
  confirmed: boolean;
}

interface Props {
  fields: CapturedField[];
}

export function FieldPanel({ fields }: Props) {
  return (
    <aside className="field-panel">
      <h3>Captured so far</h3>
      {fields.length === 0 ? (
        <p className="muted">Nothing captured yet.</p>
      ) : (
        <ul>
          {fields.map((f) => (
            <li key={f.id}>
              <span className="label">{f.label}</span>
              <span className="value">
                {f.value} {f.confirmed ? "✓" : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
