// The race's music (modo-carrera.html, question 9), made by the browser itself like the
// app's other sounds (no files, no licences): a game tune while they run, faster in a
// part's last minute and while late; a calm one in the "sin prisa" parts; a fanfare at
// the end. Notes are booked a little ahead on each tick, at the tempo of that moment.
import { playNotes } from "../components/sound.js";

const AHEAD_S = 0.6; // notes booked this far ahead
const hz = (midi) => 440 * 2 ** ((midi - 69) / 12);

// Each tune: a loop of steps; each step, its notes [midi, length in steps, wave, volume].
const TUNES = {
  game: {
    step: 0.2, // seconds per step at the usual tempo
    lead: [72, 76, 79, 76, 74, 77, 81, 77, 76, 79, 84, 79, 77, 74, 71, 74],
    bass: [48, null, 48, null, 53, null, 53, null, 55, null, 55, null, 43, null, 47, null],
    leadWave: "square", leadVolume: 0.12, bassVolume: 0.28,
  },
  calm: {
    step: 0.5,
    lead: [60, 64, 67, 72, 67, 64, 57, 60, 64, 69, 64, 60, 53, 57, 60, 65, 60, 57, 55, 59, 62, 67, 62, 59],
    bass: [48, null, null, null, null, null, 45, null, null, null, null, null, 41, null, null, null, null, null, 43],
    leadWave: "sine", leadVolume: 0.16, bassVolume: 0.2,
  },
};

// The end: a short fanfare, once. [midi, start, length] in seconds.
const FANFARE = [[67, 0, 0.14], [72, 0.15, 0.14], [76, 0.3, 0.14], [79, 0.45, 0.4], [76, 0.9, 0.14], [79, 1.05, 0.9],
  [55, 0.45, 0.4], [60, 1.05, 0.9]];

export function raceMusic() {
  let tune = null;
  let index = 0;
  let next = 0; // when the next step sounds, in the audio engine's time

  // Each tick: which tune (null: silence) and how fast (1: its usual tempo).
  function update(name, rate = 1) {
    if (name !== tune) {
      tune = name;
      index = 0;
      next = 0;
    }
    if (!tune) return;
    const { step, lead, bass, leadWave, leadVolume, bassVolume } = TUNES[tune];
    playNotes((note, now) => {
      if (next < now) next = now;
      while (next < now + AHEAD_S) {
        const length = step / rate;
        const i = index % lead.length;
        if (lead[i] != null) note({ at: next, freq: hz(lead[i]), length: length * 0.9, type: leadWave, volume: leadVolume });
        const b = bass[index % bass.length];
        if (b != null) note({ at: next, freq: hz(b), length: length * 1.8, type: "triangle", volume: bassVolume });
        index += 1;
        next += length;
      }
    });
  }

  function fanfare() {
    update(null);
    playNotes((note, now) => {
      for (const [midi, at, length] of FANFARE) {
        note({ at: now + at, freq: hz(midi), length, type: "triangle", volume: 0.35 });
        note({ at: now + at, freq: hz(midi + 12), length, type: "square", volume: 0.06 });
      }
    });
  }

  return { update, fanfare, stop: () => update(null) };
}
