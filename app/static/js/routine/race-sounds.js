// What is heard of a race from the bathroom (carrera-divertida.html, 26/11), made by the
// browser like the app's other sounds: the alien's own call, always the same, so it is
// known without looking (more often and louder the closer it is), its giggle when it goes
// ahead, its "¡aaay!" when it trips, its snoring in a pit stop; the turbo; the tank full.
import { playEffect } from "../components/sound.js";

const note = (n, at, freq, length, type = "sine", volume = 0.3, to = null) =>
  n({ at, freq, to, length, type, volume });

export const raceSounds = {
  // "bip-bip-blup": two high bleeps and a wobbly one going down. loud: it is close.
  alien(loud = false) {
    const v = loud ? 0.35 : 0.15;
    playEffect((n, now) => {
      note(n, now, 1480, 0.08, "square", v * 0.6);
      note(n, now + 0.13, 1480, 0.08, "square", v * 0.6);
      note(n, now + 0.28, 900, 0.3, "sine", v, 300);
    });
  },

  // "ji-ji-ji": it went ahead.
  giggle() {
    playEffect((n, now) => {
      for (let i = 0; i < 4; i += 1) note(n, now + i * 0.12, 1200 - i * 60, 0.08, "triangle", 0.3, 1500 - i * 60);
    });
  },

  // "¡aaay!": a turbo or a cheer made it trip.
  ouch() {
    playEffect((n, now) => {
      note(n, now, 1100, 0.6, "sawtooth", 0.12, 260);
      note(n, now, 1650, 0.5, "sine", 0.1, 400);
    });
  },

  // "zzz": in a pit stop it stands still too, asleep.
  snore() {
    playEffect((n, now) => {
      note(n, now, 90, 1.1, "sawtooth", 0.08, 130);
      note(n, now + 1.4, 160, 0.7, "sine", 0.06, 90);
    });
  },

  // The rocket's turbo: a roar going up, and a spark.
  turbo() {
    playEffect((n, now) => {
      note(n, now, 120, 0.7, "sawtooth", 0.18, 900);
      note(n, now + 0.1, 600, 0.6, "triangle", 0.12, 2400);
      note(n, now + 0.65, 2093, 0.25, "sine", 0.2);
    });
  },

  // A task over: "¡fiuuu!", the rocket off to the next planet.
  whoosh() {
    playEffect((n, now) => {
      note(n, now, 300, 0.5, "sine", 0.3, 1400);
      note(n, now + 0.05, 450, 0.45, "triangle", 0.12, 2000);
    });
  },
};
