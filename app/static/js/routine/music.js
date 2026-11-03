// The routine's songs (rutinas-4, section 3), like Scratch's "iniciar sonido": each
// one plays from a card to a card and the routine never waits for it. The voice
// goes over them: while it speaks, the song goes down, and back up after. One song
// at a time (one Música channel, sound.js).

import { volume } from "../components/sound.js";
import { speaking } from "../components/speech.js";

const UNDER_THE_VOICE = 0.3; // the song's level while the voice speaks
const FADE_S = 2; // a song cut at the end of its card goes down this long

// Where each song plays, in minutes of the day: [{ id, name, url, from, to, loop }].
// `music` as the server gives it (start/until: "alarm", a part's index or "goal").
export function musicWindows(music, { wake, parts, goalAt }) {
  const at = (card, end) => (card === "alarm" ? wake : card === "goal" ? (end ? goalAt : parts.at(-1).to)
    : end ? parts[card].to : parts[card].from);
  return music.map((m) => {
    const from = at(m.start, false);
    const loop = m.until !== null;
    return { id: m.id, name: m.name, url: m.url, from, to: loop ? at(m.until, true) : from + m.seconds / 60, loop };
  }).filter((w) => w.to > w.from);
}

export function musicPlayer() {
  let current = null; // { id, name, audio }

  function stop() {
    current?.audio.pause();
    current = null;
  }

  // At `time`, the window that should sound (if `on`), at its place; the volume follows
  // the Música channel, the voice and the end of its window.
  function update(windows, time, on) {
    const window = on ? windows.find((w) => w.from <= time && time < w.to) : null;
    if (!window) {
      stop();
      return;
    }
    if (current?.id !== window.id) {
      stop();
      const audio = new Audio(window.url);
      audio.loop = window.loop;
      audio.volume = 0;
      audio.addEventListener("loadedmetadata", () => {
        const offset = (time - window.from) * 60; // opened late: where it would be by now
        audio.currentTime = window.loop ? offset % audio.duration : Math.min(offset, audio.duration);
      }, { once: true });
      audio.play().catch(() => {}); // before the first tap the browser says no: the next tick tries again
      current = { id: window.id, name: window.name, audio };
    } else if (current.audio.paused && !current.audio.ended) {
      current.audio.play().catch(() => {});
    }
    const toEnd = window.loop ? (window.to - time) * 60 : Infinity;
    const fade = Math.min(1, toEnd / FADE_S);
    current.audio.volume = Math.min(1, volume("music") * (speaking() ? UNDER_THE_VOICE : 1) * fade);
  }

  return {
    update,
    stop,
    playing: () => (current && !current.audio.paused ? current : null),
  };
}
