// The routine's songs (rutinas-4, section 3), like Scratch's "iniciar sonido": each
// one plays from a card to a card and the routine never waits for it. The voice
// goes over them: while it speaks, the song goes down, and back up after. One song
// at a time (one Música channel, sound.js); each card's songs, one after the other.

import { volume } from "../components/sound.js";
import { speaking } from "../components/speech.js";

const UNDER_THE_VOICE = 0.3; // the song's level while the voice speaks
const FADE_S = 2; // a song cut at the end of its card goes down this long
const VOICE_STARTS_S = 6; // after the voice: wait this long first (it may begin a moment late: the ring, the zero)
const LOUD = 1; // "muy alta": the loudest it goes, whatever the Música level

// Where each card's songs play, in minutes of the day: [{ id, songs, total, from, to, loop }]
// (songs: [{ name, url, seconds }], one after the other; total: all of them, in seconds).
// `music` as the server gives it (start/until: "alarm", a part's index or "goal").
// goalFrom: when the goal comes (early, if everyone signed in the last part).
export function musicWindows(music, { wake, parts, goalAt, goalFrom = parts.at(-1).to }) {
  const at = (card, end) => (card === "alarm" ? wake : card === "goal" ? (end ? Math.max(goalAt, goalFrom) : goalFrom)
    : end ? parts[card].to : parts[card].from);
  return music.map((m) => {
    const from = at(m.start, false);
    const loop = m.until !== null;
    const total = m.songs.reduce((sum, song) => sum + song.seconds, 0);
    return {
      id: m.id, songs: m.songs, total, from, to: loop ? at(m.until, true) : from + total / 60, loop,
      afterVoice: Boolean(m.after_voice), loud: Boolean(m.loud),
    };
  }).filter((w) => w.to > w.from && w.total > 0);
}

// Which song of a window plays at `time`, and how far into it (in seconds).
function songAt(window, time) {
  let offset = (time - window.from) * 60;
  if (window.loop) offset %= window.total; // up to its card: the list again from the start
  for (const [index, song] of window.songs.entries()) {
    if (offset < song.seconds) return { index, song, offset };
    offset -= song.seconds;
  }
  const index = window.songs.length - 1;
  return { index, song: window.songs[index], offset: window.songs[index].seconds };
}

export function musicPlayer() {
  let current = null; // { key, id, name, audio }: the window, and which of its songs
  // "After the voice": how late each window really started (minutes), once the voice was quiet.
  const late = new Map();
  const moved = (w) => {
    const by = late.get(w.id) ?? 0;
    return { ...w, from: w.from + by, to: w.loop ? w.to : w.to + by };
  };

  function stop() {
    current?.audio.pause();
    current = null;
  }

  // At `time`, the window that should sound (if `on`), at its place; the volume follows
  // the Música channel, the voice and the end of its window.
  function update(windows, time, on) {
    // A song still going ("una vez", longer than its card) gives way to the next one.
    let window = on ? windows.map(moved).filter((w) => w.from <= time && time < w.to)
      .sort((a, b) => b.from - a.from)[0] ?? null : null;
    if (window?.afterVoice && !late.has(window.id)) {
      // Not yet: it starts, from its beginning, once the voice has had time to start and finish.
      if ((time - window.from) * 60 < VOICE_STARTS_S || speaking()) {
        stop();
        return;
      }
      late.set(window.id, time - window.from);
      window = moved(windows.find((w) => w.id === window.id));
    }
    if (!window) {
      stop();
      return;
    }
    const { index, song, offset } = songAt(window, time);
    const key = `${window.id}:${index}`;
    if (current?.key !== key) {
      stop();
      const audio = new Audio(song.url);
      audio.volume = 0;
      audio.addEventListener("loadedmetadata", () => {
        audio.currentTime = Math.min(offset, audio.duration); // opened late: where it would be by now
      }, { once: true });
      audio.play().catch(() => {}); // before the first tap the browser says no: the next tick tries again
      current = { key, id: window.id, name: song.name, audio };
    } else if (current.audio.ended && window.loop && offset < 1) {
      current.audio.currentTime = 0; // a single song up to its card: again
      current.audio.play().catch(() => {});
    } else if (current.audio.paused && !current.audio.ended) {
      current.audio.play().catch(() => {});
    }
    const toEnd = window.loop ? (window.to - time) * 60 : Infinity;
    const fade = Math.min(1, toEnd / FADE_S);
    const level = window.loud ? LOUD : volume("music");
    current.audio.volume = Math.min(1, level * (speaking() ? UNDER_THE_VOICE : 1) * fade);
  }

  return {
    update,
    stop,
    playing: () => (current && !current.audio.paused ? current : null),
  };
}
