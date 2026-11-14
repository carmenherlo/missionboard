import { api } from "../api.js";
import { sounds } from "../components/sound.js";
import { say } from "../components/speech.js";

// Notices before a routine rings ("Es hora de despertar a los niños", 20 minutes
// before): each one said once, at its minute by the household's clock, without
// opening anything. Asked for every check; between checks, timed here.
export function startNotices(everyMs) {
  let notices = [];
  let serverNow = 0;
  let fetchedAt = 0;
  let day = "";
  const said = new Set();
  async function load() {
    try {
      const data = await api("GET", "api/routines/notices");
      if (data.day !== day) said.clear();
      ({ notices, now: serverNow, day } = data);
      fetchedAt = Date.now();
    } catch {
      // no connection now: next time
    }
  }
  function sayDue() {
    const now = serverNow + (Date.now() - fetchedAt) / 60_000;
    for (const notice of notices) {
      const key = `${notice.routine}|${notice.at}`;
      if (!said.has(key) && now >= notice.at && now < notice.at + 0.5) {
        said.add(key);
        sounds.ding();
        say(notice.say);
      }
    }
  }
  load();
  setInterval(load, everyMs);
  setInterval(sayDue, 2000);
}
