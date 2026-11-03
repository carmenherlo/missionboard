// Says things aloud. Everything the app says goes through here (and onSay()
// hears it, even with the voice off).
//  · The natural voice (Piper, the woman's voice the family chose in the old
//    app) is made on the server (GET /api/voice) and played here.
//  · Without it (no model on the server, or a sentence that fails), the
//    tablet's own Spanish voice reads instead.
// If neither is there, canSpeak() is false and the screens hide the 🔊.
// Its volume is the "voice" channel of sound.js.
import { api } from "../api.js";
import { isOff, volume } from "./sound.js";

const PAUSE_MS = 350; // between the sentences of one say()

let tabletVoice = null;
let natural = false; // the server's voice is there
let saying = 0; // which say() is the latest: an older one stops
let playing = null; // the sentence being played by the natural voice
const listeners = new Set(); // who wants to know what is said ("Probar ahora": its transcript)

function pickTabletVoice() {
  const voices = globalThis.speechSynthesis?.getVoices() ?? [];
  tabletVoice = voices.find((v) => v.lang.toLowerCase().startsWith("es-es"))
    ?? voices.find((v) => v.lang.toLowerCase().startsWith("es"))
    ?? null;
}

if (globalThis.speechSynthesis) {
  pickTabletVoice();
  speechSynthesis.addEventListener("voiceschanged", pickTabletVoice);
}
api("GET", "/api/voice/status").then((status) => { natural = status.available; }).catch(() => {});

export function canSpeak() {
  return natural || tabletVoice !== null;
}

// A text, or a list of sentences said one after the other. Whatever was being
// said stops. Emojis are left out (some voices would read their names).
export function say(text) {
  quiet();
  const parts = [text].flat()
    .map((part) => part.replace(/\p{Extended_Pictographic}|️/gu, "").replace(/\s+/g, " ").trim())
    .filter(Boolean);
  if (parts.length) listeners.forEach((listener) => listener(parts));
  if (!parts.length || isOff("voice")) return;
  const turn = saying;
  if (natural) sayNaturally(parts, turn);
  else sayWithTablet(parts);
}

// Something being said right now (the songs go down under the voice).
let talking = null; // the turn whose sentences are still being played
export function speaking() {
  return talking === saying || Boolean(globalThis.speechSynthesis?.speaking);
}

async function sayNaturally(parts, turn) {
  talking = turn;
  try {
    await playEach(parts, turn);
  } finally {
    if (talking === turn) talking = null;
  }
}

async function playEach(parts, turn) {
  // All of them asked for at once: the next one is ready when the last ends.
  const sounds = parts.map((part) => new Audio(`/api/voice?text=${encodeURIComponent(part)}`));
  for (const [index, sound] of sounds.entries()) {
    if (turn !== saying) return;
    sound.volume = Math.min(1, volume("voice"));
    playing = sound;
    try {
      await new Promise((resolve, reject) => {
        sound.addEventListener("ended", resolve, { once: true });
        sound.addEventListener("error", reject, { once: true });
        sound.play().catch(reject);
      });
    } catch {
      if (turn === saying) sayWithTablet(parts.slice(index)); // the rest, with the tablet's voice
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, PAUSE_MS));
  }
}

function sayWithTablet(parts) {
  if (!tabletVoice) return;
  for (const part of parts) {
    const utterance = new SpeechSynthesisUtterance(part);
    utterance.voice = tabletVoice;
    utterance.lang = tabletVoice.lang;
    utterance.volume = Math.min(1, volume("voice"));
    speechSynthesis.speak(utterance);
  }
}

// listener(sentences) for everything said from now on; returns how to stop.
export function onSay(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function quiet() {
  saying += 1;
  playing?.pause();
  playing = null;
  globalThis.speechSynthesis?.cancel();
}

// Kept for the steps of a mission (🔊): the same voice.
export const speak = say;
