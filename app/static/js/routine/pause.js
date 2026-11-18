// Pausing a routine started by hand (18/11): something came up. A parent, with the
// code, makes its time stand still (no voice, no tic-tac, no songs) on every device,
// and lets it go on where it was: the server moves its start that much later.
import { api } from "../api.js";
import { quiet } from "../components/speech.js";
import { t } from "../texts.js";
import { askParentCode } from "./code-dialog.js";

export function pause(r) {
  // ⏸ / ▶ in its top bar: the code, then paused or going on.
  function askPause() {
    const paused = Boolean(r.showing.data.paused);
    askParentCode(r, {
      title: paused ? t.routine.resumeTitle : t.routine.pauseTitle,
      hint: paused ? t.routine.resumeHint : t.routine.pauseHint,
      submit: paused ? t.routine.resume : t.routine.pause,
      send: async (parentCode) => {
        await api("PUT", `api/routines/${r.showing.data.id}/paused`, { parentCode, json: { paused: !paused } });
        await r.check(); // here at once; the other devices at their next check
      },
    });
  }

  // It stands still now: silent at once (its songs stop in playMusic).
  function paused() {
    r.stopRinging();
    quiet();
    r.showing.count = null;
  }

  return { askPause, paused };
}
