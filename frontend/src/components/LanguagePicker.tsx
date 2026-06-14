/** Language selector for the pre-join screen (POC: English + Hindi). */

export const LANGUAGES: { code: string; label: string }[] = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी (Hindi)" },
];

interface Props {
  value: string;
  onChange: (code: string) => void;
  disabled?: boolean;
}

export function LanguagePicker({ value, onChange, disabled }: Props) {
  return (
    <label className="field">
      <span>Language</span>
      <select value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    </label>
  );
}
