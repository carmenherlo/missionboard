// Sound effects made by the browser itself (Web Audio): no files, no licences,
// works offline. Ported from an earlier version of the app,
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

// A sound file played by the audio engine (the voice, 06/11): once a tap has started the
// engine it may sound at any time, also in a page inside another one (a Home Assistant
// panel), where the browser refuses <audio> without a tap at that very moment.
export async function decodeClip(file) {
  return context().decodeAudioData(file);
}

// { done: a promise for when it ends, pause(): stop it }
export function playClip(clip, level) {
  const ctx = context();
  const gain = ctx.createGain();
  gain.gain.value = level;
  gain.connect(ctx.destination);
  const source = ctx.createBufferSource();
  source.buffer = clip;
  source.connect(gain);
  const done = new Promise((resolve) => { source.onended = resolve; });
  source.start();
  return { done, pause: () => source.stop() };
}

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
  // loud: a part's last ten seconds (04/11: the second hand then at its loudest).
  tick(delay, tac = false, loud = false) {
    play((ctx, out, now) => {
      blip(ctx, out, { at: now + delay, freq: tac ? 2000 : 2600, length: 0.02, type: "triangle", volume: loud ? 0.6 : 0.3 });
    }, "ticking", { full: loud });
  },

  // A footprint (or a dot) taking its colour on the route (12/11): a soft "pat", lower
  // for one foot and a little higher for the other, `delay` seconds from now.
  step(delay, other = false, loud = false) {
    play((ctx, out, now) => {
      blip(ctx, out, { at: now + delay, freq: other ? 260 : 220, to: other ? 150 : 120, length: 0.09, type: "sine", volume: loud ? 0.9 : 0.6 });
    }, "ticking", { full: loud });
  },

  // The prize wheel (12/11). Before turning: a "whoosh" going up.
  whoosh() {
    play((ctx, out, now) => {
      blip(ctx, out, { at: now, freq: 220, to: 880, length: 0.45, type: "sine", volume: 0.35 });
      blip(ctx, out, { at: now + 0.05, freq: 330, to: 1320, length: 0.4, type: "triangle", volume: 0.15 });
    });
  },

  // A peg of the wheel passing the pointer: a dry "clac", softer when it goes fast.
  clack(soft = false) {
    play((ctx, out, now) => {
      blip(ctx, out, { at: now, freq: 1800, to: 900, length: 0.03, type: "triangle", volume: soft ? 0.25 : 0.55 });
      blip(ctx, out, { at: now, freq: 180, to: 90, length: 0.05, type: "sine", volume: soft ? 0.2 : 0.4 });
    });
  },

  // The wheel has stopped: a little bell, two notes up.
  chime() {
    play((ctx, out, now) => {
      for (const [freq, at] of [[1047, 0], [1568, 0.12], [2093, 0.24]]) {
        blip(ctx, out, { at: now + at, freq, length: 0.7, type: "sine", volume: 0.4 });
        blip(ctx, out, { at: now + at, freq: freq * 2, length: 0.3, type: "sine", volume: 0.08 });
      }
    });
  },

  // The shop (tienda-2.html). A star paid, `delay` seconds from now: a small coin.
  coin(delay = 0) {
    play((ctx, out, now) => {
      blip(ctx, out, { at: now + delay, freq: 1319, length: 0.07, type: "square", volume: 0.15 });
      blip(ctx, out, { at: now + delay + 0.07, freq: 1760, length: 0.25, type: "sine", volume: 0.3 });
    });
  },

  // The delivery truck: a low engine for a moment and two short honks.
  truck(delay = 0) {
    play((ctx, out, now) => {
      const at = now + delay;
      blip(ctx, out, { at, freq: 55, to: 90, length: 1.1, type: "sawtooth", volume: 0.12 });
      blip(ctx, out, { at: at + 0.9, freq: 415, length: 0.14, type: "square", volume: 0.25 });
      blip(ctx, out, { at: at + 1.1, freq: 415, length: 0.22, type: "square", volume: 0.25 });
    });
  },

  // At the door: "ding-dong".
  doorbell(delay = 0) {
    play((ctx, out, now) => {
      blip(ctx, out, { at: now + delay, freq: 659, length: 0.7, type: "sine", volume: 0.55 });
      blip(ctx, out, { at: now + delay + 0.45, freq: 523, length: 1.1, type: "sine", volume: 0.55 });
    });
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

// full: as loud as it goes, whatever its level (still silent if its channel is off).
function play(draw, channel = "effects", { full = false } = {}) {
  if (isOff(channel)) return;
  const ctx = context();
  if (!ctx) return; // no Web Audio: silent
  const output = ctx.createGain();
  output.gain.value = full ? 1 : volume(channel);
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
