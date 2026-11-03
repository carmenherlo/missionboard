// Sound effects made by the browser itself (Web Audio): no files, no licences,
// works offline. Ported from the old app (an earlier version, sounds.js),
// where they were tested at home with the morning routine.
//
// Four channels, voice, effects, the ticking second hand and the songs, each with its level and an on/off switch,
// remembered on this device (the sound panel changes them). Browsers only
// allow sound after a tap: the first tap anywhere starts the audio engine.

const KEY = "missionboard.sound";
const USUAL_LEVEL = 0.8;
const LOUDNESS = { voice: 1, effects: 0.75, ticking: 0.4, music: 0.8 };
const USUAL_TICKING = 0.5; // like a real clock's: there, barely heard

let audio = null;
let settings = read();
const listeners = new Set();

function read() {
  const fresh = {
    voice: { level: USUAL_LEVEL, off: false },
    effects: { level: USUAL_LEVEL, off: false },
    ticking: { level: USUAL_TICKING, off: false },
    music: { level: USUAL_LEVEL, off: false },
  };
  try {
    return { ...fresh, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") };
  } catch {
    return fresh;
  }
}

function changed() {
  try {
    localStorage.setItem(KEY, JSON.stringify(settings));
  } catch {
    // storage blocked: the levels last until the page reloads
  }
  for (const listener of listeners) listener();
}

export function level(channel) {
  return settings[channel].level;
}

export function isOff(channel) {
  return settings[channel].off || settings[channel].level === 0;
}

// How loud to play that channel: 0 when it is off.
export function volume(channel) {
  return isOff(channel) ? 0 : settings[channel].level * LOUDNESS[channel];
}

export function setLevel(channel, value) {
  settings = { ...settings, [channel]: { level: value, off: false } };
  changed();
}

export function setOff(channel, off) {
  settings = { ...settings, [channel]: { ...settings[channel], off, level: settings[channel].level || USUAL_LEVEL } };
  changed();
}

export function onSoundChange(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// The first tap anywhere starts the audio engine (and the voice), so that a
// routine ringing later, with nobody touching the tablet, can be heard.
// Until then soundLocked() is true and the screens ask for that tap.
const unlockListeners = new Set();
addEventListener("pointerdown", () => {
  context();
  for (const listener of unlockListeners) listener();
  unlockListeners.clear();
}, { once: true, capture: true });

export function soundLocked() {
  return !audio || audio.state !== "running";
}

export function onSoundUnlocked(listener) {
  unlockListeners.add(listener);
}

export const sounds = {
  // The alarm: an old phone's "rrring rrring", three times.
  alarm() {
    play((ctx, out, now) => {
      for (let ring = 0; ring < 3; ring += 1) {
        for (const burst of [0, 0.55]) {
          for (let i = 0; i < 10; i += 1) {
            const at = now + ring * 1.7 + burst + i * 0.04;
            blip(ctx, out, { at, freq: i % 2 ? 1318 : 1046, length: 0.045, type: "square", volume: 0.45 });
          }
        }
      }
    });
  },

  // Something new to listen to: a short "ding".
  ding() {
    play((ctx, out, now) => {
      blip(ctx, out, { at: now, freq: 1047, length: 0.4, type: "sine", volume: 0.6 });
      blip(ctx, out, { at: now, freq: 1568, length: 0.3, type: "sine", volume: 0.25 });
    });
  },

  // The countdown, like an old film's: a short "pip" each second; at zero, a higher, longer one.
  countdown(zero = false) {
    play((ctx, out, now) => {
      blip(ctx, out, zero
        ? { at: now, freq: 2093, length: 0.6, type: "sine", volume: 0.6 }
        : { at: now, freq: 1047, length: 0.15, type: "sine", volume: 0.5 });
    });
  },

  // The second hand, heard: a faint "tic" (or "tac", lower), `delay` seconds from now,
  // like a real clock's: it is there, and only now and then reminds you of the time.
  tick(delay, tac = false) {
    play((ctx, out, now) => {
      blip(ctx, out, { at: now + delay, freq: tac ? 2000 : 2600, length: 0.02, type: "triangle", volume: 0.3 });
    }, "ticking");
  },

  // Well done: a fanfare.
  win() {
    play((ctx, out, now) => {
      const notes = [[523, 0, 0.14], [523, 0.15, 0.14], [523, 0.3, 0.14], [659, 0.45, 0.3],
        [587, 0.78, 0.14], [659, 0.93, 0.14], [784, 1.08, 0.7]];
      for (const [freq, at, length] of notes) {
        blip(ctx, out, { at: now + at, freq, length, type: "square", volume: 0.35 });
        blip(ctx, out, { at: now + at, freq: freq / 2, length, type: "triangle", volume: 0.5 });
      }
    });
  },
};

// ---------- building blocks ----------

function play(draw, channel = "effects") {
  if (isOff(channel)) return;
  const ctx = context();
  if (!ctx) return; // no Web Audio: silent
  const output = ctx.createGain();
  output.gain.value = volume(channel);
  output.connect(ctx.destination);
  draw(ctx, output, ctx.currentTime + 0.01);
}

function context() {
  if (!audio) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return null;
    audio = new AudioContext();
  }
  if (audio.state === "suspended") audio.resume();
  return audio;
}

// One short note, optionally sliding to another pitch (`to`).
function blip(ctx, out, { at, freq, to = null, length, type, volume: loud }) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, at);
  if (to) osc.frequency.exponentialRampToValueAtTime(to, at + length);
  gain.gain.setValueAtTime(0.0001, at); // quick fade in and out, so notes never click
  gain.gain.exponentialRampToValueAtTime(loud, at + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
  osc.connect(gain).connect(out);
  osc.start(at);
  osc.stop(at + length + 0.05);
}
