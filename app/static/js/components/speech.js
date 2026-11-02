// Says things aloud with the tablet's own voice, in Spanish. Everything the
// app says goes through here, so changing the voice (to Piper, the natural
// woman's voice of the old app, before going to production) is changing
// only this file. If the tablet has no Spanish voice, canSpeak() is false and
// the screens hide the 🔊. Its volume is the "voice" channel of sound.js.
import { isOff, volume } from "./sound.js";

let voice = null;
let saying = 0; // which say() is the latest: an older one stops

function pickVoice() {
  const voices = globalThis.speechSynthesis?.getVoices() ?? [];
  voice = voices.find((v) => v.lang.toLowerCase().startsWith("es-es"))
    ?? voices.find((v) => v.lang.toLowerCase().startsWith("es"))
    ?? null;
}

if (globalThis.speechSynthesis) {
  pickVoice();
  speechSynthesis.addEventListener("voiceschanged", pickVoice);
}

export function canSpeak() {
  return voice !== null;
}

// A text, or a list of sentences said one after the other. Whatever was being
// said stops. Emojis are left out (some voices would read their names).
export function say(text) {
  quiet();
  const parts = [text].flat()
    .map((part) => part.replace(/\p{Extended_Pictographic}|️/gu, "").replace(/\s+/g, " ").trim())
    .filter(Boolean);
  if (!voice || !parts.length || isOff("voice")) return;
  const turn = saying;
  for (const part of parts) {
    const utterance = new SpeechSynthesisUtterance(part);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.volume = Math.min(1, volume("voice"));
    if (turn === saying) speechSynthesis.speak(utterance);
  }
}

export function quiet() {
  saying += 1;
  globalThis.speechSynthesis?.cancel();
}

// Kept for the steps of a mission (🔊): the same voice.
export const speak = say;
