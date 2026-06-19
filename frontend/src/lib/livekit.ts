/**
 * LiveKit integration: fetch a join token from the backend and manage the Room.
 *
 * Implemented directly on `livekit-client` (stable API) rather than the React component
 * library, so the connection, live captions, and speaking indicators are explicit and easy
 * to follow. Exposes a `useIntakeRoom()` hook the UI consumes.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ConnectionState,
  RemoteTrack,
  Room,
  RoomEvent,
  Track,
  type Participant,
  type RemoteTrackPublication,
  type TranscriptionSegment,
} from "livekit-client";
import { API_BASE } from "./api";
import { AudioPlayer } from "./audio";

export interface TokenResponse {
  token: string;
  url: string;
  room: string;
  identity: string;
  language: string;
}

export interface Caption {
  id: string;
  speaker: "patient" | "agent";
  text: string;
  final: boolean;
}

/** A captured intake field pushed live from the agent (matches FieldPanel's shape). */
export interface LiveField {
  id: string;
  label: string;
  value: string;
  confirmed: boolean;
}

export type Status = "idle" | "connecting" | "connected" | "error";

const DATA_TOPIC = "intake";

interface IntakeDataMessage {
  type?: string;
  id?: string;
  label?: string;
  value?: string;
  confirmed?: boolean;
  reason?: string;
  field_id?: string;
  variant?: string;
  url?: string;
  text?: string;
}

/** Request a LiveKit join token for the chosen language from the FastAPI backend. */
export async function fetchToken(language: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language }),
  });
  if (!res.ok) throw new Error(`Token request failed: ${res.status}`);
  return (await res.json()) as TokenResponse;
}

/**
 * Hook that owns a LiveKit Room: connect/disconnect, publish the mic, render the agent's
 * audio, collect live transcription captions, and track who is speaking.
 */
export function useIntakeRoom() {
  const roomRef = useRef<Room | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [fields, setFields] = useState<LiveField[]>([]);
  const [urgent, setUrgent] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [handoff, setHandoff] = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [patientSpeaking, setPatientSpeaking] = useState(false);
  const [micPublished, setMicPublished] = useState(false);
  const promptAudioRef = useRef<AudioPlayer | null>(null);
  const promptPlayingRef = useRef(false);
  if (promptAudioRef.current === null) promptAudioRef.current = new AudioPlayer();

  const stopPromptPlayback = useCallback(() => {
    if (!promptPlayingRef.current) return;
    promptAudioRef.current?.stop();
    promptPlayingRef.current = false;
    setAgentSpeaking(false);
  }, []);

  const connect = useCallback(async (language: string) => {
    setStatus("connecting");
    setError(null);
    setCaptions([]);
    setFields([]);
    setUrgent(null);
    setCompleted(false);
    setHandoff(false);
    setMicPublished(false);
    try {
      const { token, url } = await fetchToken(language);
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        audioCaptureDefaults: {
          noiseSuppression: true,
          echoCancellation: true,
          autoGainControl: true,
        },
      });
      roomRef.current = room;

      const localIdentity = () => room.localParticipant?.identity;

      room
        .on(
          RoomEvent.TrackSubscribed,
          (track: RemoteTrack, _pub: RemoteTrackPublication, participant?: Participant) => {
            if (track.kind === Track.Kind.Audio) {
              const el = track.attach();
              el.style.display = "none";
              document.body.appendChild(el);
              void el.play().catch((err) => console.warn("[livekit] agent audio play blocked", err));
              console.debug("[livekit] subscribed to agent audio from", participant?.identity);
            }
          },
        )
        .on(RoomEvent.TranscriptionReceived, (segments: TranscriptionSegment[], participant?: Participant) => {
          const speaker: Caption["speaker"] =
            participant && participant.identity === localIdentity() ? "patient" : "agent";
          setCaptions((prev) => {
            const next = [...prev];
            for (const seg of segments) {
              const idx = next.findIndex((c) => c.id === seg.id);
              const caption: Caption = { id: seg.id, speaker, text: seg.text, final: seg.final };
              if (idx >= 0) next[idx] = caption;
              else next.push(caption);
            }
            return next;
          });
        })
        .on(RoomEvent.ActiveSpeakersChanged, (speakers: Participant[]) => {
          const ids = new Set(speakers.map((s) => s.identity));
          const localId = localIdentity() ?? "";
          const patientActive = ids.has(localId);
          const agentActive = speakers.some((s) => s.identity !== localId);
          setPatientSpeaking(patientActive);
          setAgentSpeaking(agentActive);
          // Barge-in: stop prerecorded prompt clips when the patient starts speaking.
          if (patientActive) {
            stopPromptPlayback();
          }
        })
        .on(RoomEvent.DataReceived, (payload: Uint8Array, _p?: Participant, _k?: unknown, topic?: string) => {
          if (topic && topic !== DATA_TOPIC) return;
          let msg: IntakeDataMessage;
          try {
            msg = JSON.parse(new TextDecoder().decode(payload));
          } catch {
            return;
          }
          if (msg.type === "field_update" && msg.id) {
            const field: LiveField = {
              id: msg.id,
              label: msg.label ?? msg.id,
              value: msg.value ?? "",
              confirmed: Boolean(msg.confirmed),
            };
            setFields((prev) => {
              const next = [...prev];
              const idx = next.findIndex((f) => f.id === field.id);
              if (idx >= 0) next[idx] = field;
              else next.push(field);
              return next;
            });
          } else if (msg.type === "urgent") {
            setUrgent(msg.reason ?? "urgent");
          } else if (msg.type === "complete") {
            setCompleted(true);
          } else if (msg.type === "handoff") {
            setHandoff(true);
          } else if (msg.type === "prompt_audio" && msg.url) {
            const promptUrl = msg.url;
            const captionText = msg.text ?? "";
            if (captionText) {
              setCaptions((prev) => [
                ...prev,
                {
                  id: `prompt-${msg.field_id ?? "field"}-${msg.variant ?? "prompt"}-${Date.now()}`,
                  speaker: "agent",
                  text: captionText,
                  final: true,
                },
              ]);
            }

            const playPrompt = async () => {
              promptPlayingRef.current = true;
              setAgentSpeaking(true);
              try {
                await promptAudioRef.current?.play(promptUrl);
              } finally {
                promptPlayingRef.current = false;
                setAgentSpeaking(false);
              }
            };

            void playPrompt().catch((err) => {
              console.warn("[audio] prompt playback failed", err);
            });
          }
        })
        .on(RoomEvent.Disconnected, () => setStatus("idle"))
        .on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
          if (state === ConnectionState.Connected) setStatus("connected");
        });

      await room.connect(url, token);
      console.debug("[livekit] connected to room", room.name, "as", localIdentity());

      try {
        await room.localParticipant.setMicrophoneEnabled(true);
      } catch (micErr) {
        setError(
          "Microphone could not be started — allow mic access for this site in the browser, " +
            "then reconnect. (" +
            (micErr instanceof Error ? micErr.message : String(micErr)) +
            ")",
        );
      }
      const micOn = room.localParticipant.isMicrophoneEnabled;
      setMicPublished(micOn);
      if (!micOn) {
        setError((prev) => prev ?? "Microphone is not publishing — check the browser mic permission.");
      }

      try {
        await room.startAudio();
      } catch {
        /* ignored — agent audio elements also call play() */
      }

      setStatus("connected");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  }, [stopPromptPlayback]);

  const disconnect = useCallback(async () => {
    await roomRef.current?.disconnect();
    roomRef.current = null;
    setStatus("idle");
  }, []);

  useEffect(() => () => void roomRef.current?.disconnect(), []);

  return {
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
    connect,
    disconnect,
  };
}
