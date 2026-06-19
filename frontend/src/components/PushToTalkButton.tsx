// Large hold-to-talk button. Publishes mic only while held (handled by the parent via
// onDown/onUp). Uses pointer events so it works for touch (tablet/kiosk) and mouse.

interface Props {
  disabled?: boolean;
  recording: boolean;
  onDown: () => void;
  onUp: () => void;
  label?: string;
}

export function PushToTalkButton({ disabled, recording, onDown, onUp, label }: Props) {
  return (
    <div className="ptt-wrap">
      <button
        className={`ptt${recording ? " recording" : ""}`}
        disabled={disabled}
        onPointerDown={(e) => {
          e.preventDefault();
          if (!disabled) onDown();
        }}
        onPointerUp={(e) => {
          e.preventDefault();
          onUp();
        }}
        onPointerLeave={() => {
          if (recording) onUp();
        }}
      >
        {recording ? "Listening…" : label ?? "Hold to talk"}
      </button>
      {recording ? (
        <span className="muted">
          <span className="recording-dot" /> Speak now, then release
        </span>
      ) : (
        <span className="muted">Press and hold while you answer</span>
      )}
    </div>
  );
}
