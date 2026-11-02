// What the tablet needs to wake the family up: sound allowed and the screen on.
//  · Browsers keep sound blocked until the first tap after the page loads:
//    until then, a notice at the bottom asks for that tap (a routine ringing
//    at 6:30 after a night reload would otherwise be silent).
//  · While the app is open, it asks the browser to keep the screen on (Screen
//    Wake Lock). Only on https or localhost; elsewhere, the tablet's own
//    "screen always on" setting does it.
import { h } from "../dom.js";
import { t } from "../texts.js";
import { onSoundUnlocked, soundLocked } from "./sound.js";

let lock = null;

async function keepScreenOn() {
  if (!("wakeLock" in navigator) || document.visibilityState !== "visible" || lock) return;
  try {
    lock = await navigator.wakeLock.request("screen");
    lock.addEventListener("release", () => { lock = null; });
  } catch {
    // not allowed here (http, low battery…): the tablet's settings decide
  }
}

export function startKeepAwake() {
  if (soundLocked()) {
    const notice = h("p", { class: "sound-notice", role: "status" }, t.sound.tapToEnable);
    document.body.append(notice);
    onSoundUnlocked(() => notice.remove());
  }
  onSoundUnlocked(keepScreenOn); // the browser asks for a tap for this too
  document.addEventListener("visibilitychange", keepScreenOn); // it is released when the screen goes off
}
