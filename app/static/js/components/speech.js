// Reads a text aloud with the tablet's own voice, in Spanish. If the tablet
// has no Spanish voice, canSpeak() is false and the screens hide the 🔊.

let voice = null;

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

export function speak(text) {
  if (!voice) return;
  speechSynthesis.cancel(); // a new tap starts again instead of queuing
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = voice;
  utterance.lang = voice.lang;
  speechSynthesis.speak(utterance);
}
