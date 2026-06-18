import { API_BASE } from "./api";

export function audioUrl(url?: string): string | undefined {
  if (!url) return undefined;
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

export class AudioPlayer {
  private el: HTMLAudioElement;

  constructor() {
    this.el = new Audio();
    this.el.preload = "auto";
  }

  async play(url?: string): Promise<void> {
    const resolved = audioUrl(url);
    if (!resolved) return;

    const el = this.el;
    el.pause();
    el.src = resolved;

    await new Promise<void>((resolve) => {
      let settled = false;
      const finish = () => {
        if (settled) return;
        settled = true;
        el.removeEventListener("canplaythrough", finish);
        el.removeEventListener("error", finish);
        window.clearTimeout(timer);
        resolve();
      };
      const timer = window.setTimeout(finish, 2500);
      el.addEventListener("canplaythrough", finish);
      el.addEventListener("error", finish);
      el.load();
    });

    try {
      el.currentTime = 0;
      await el.play();
    } catch {
      return;
    }

    await new Promise<void>((resolve) => {
      const done = () => {
        el.removeEventListener("ended", done);
        el.removeEventListener("error", done);
        resolve();
      };
      el.addEventListener("ended", done);
      el.addEventListener("error", done);
    });
  }

  stop(): void {
    this.el.pause();
    this.el.currentTime = 0;
  }
}
