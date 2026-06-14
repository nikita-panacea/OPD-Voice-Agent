/** Live transcript: renders patient + agent caption bubbles in order. */
import { useEffect, useRef } from "react";
import type { Caption } from "../lib/livekit";

interface Props {
  captions: Caption[];
}

export function TranscriptView({ captions }: Props) {
  const endRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to the newest caption.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [captions]);

  return (
    <div className="transcript">
      {captions.length === 0 && <p className="muted">Transcript will appear here as you talk.</p>}
      {captions.map((c) => (
        <div key={c.id} className={`bubble ${c.speaker}`}>
          <span className="who">{c.speaker === "patient" ? "You" : "Assistant"}</span>
          <span className={c.final ? "text" : "text interim"}>{c.text}</span>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
