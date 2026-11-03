// A child's mission opened over whatever is on screen (their route, or the
// clock of a routine): the panel with its steps, checking and unchecking
// them, 🔊, and the celebration when the last one is checked.
import { api } from "../../api.js";
import { speak } from "../../components/speech.js";
import { h } from "../../dom.js";
import { showCelebration } from "./celebration.js";
import { missionSheet } from "./mission-sheet.js";

// day: the child's day (GET /api/children/<id>/today), or null to fetch it.
// onDay(day): the day changed (a step, the mission done). onClose(day): it is gone.
// Returns { close } to close it from outside (a routine's new part).
export async function openMission(container, childId, missionId, { day = null, onDay = () => {}, onClose = () => {} } = {}) {
  const base = `/api/children/${childId}/today`;
  day ??= await api("GET", base);
  let busy = false; // one step at a time
  let closed = false;
  let drawn = false;

  // The child's colour and its tones: the only styles passed from code (see tokens.css).
  const { color, soft, strong, on } = day.colors;
  const holder = h("div", {
    class: "child-colors",
    style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`,
  });
  container.append(holder);

  const note = (kind, step) => api("POST", `${base}/notes`,
    { json: { kind, mission_id: missionId, step_id: step?.id } }).catch(() => {});

  function draw() {
    const mission = day.missions.find((m) => m.id === missionId);
    if (!mission) return close();
    holder.replaceChildren(missionSheet(day, mission, { onToggle: toggle, onSpeak: listen, onClose: close, again: drawn }));
    drawn = true;
  }

  // The step changes as soon as it is tapped (03/11: waiting for the server, a tap
  // seemed lost and children tapped twice); the server's answer then redraws it.
  async function toggle(step, card) {
    if (busy) return;
    busy = true;
    card?.classList.toggle("step-card--done", !step.checked);
    try {
      const result = await api("PUT", `${base}/missions/${missionId}/steps/${step.id}`,
        { json: { checked: !step.checked } });
      day = result.today;
      onDay(day);
      if (result.completed) {
        holder.replaceChildren();
        showCelebration(holder, day, result.stars_earned, close);
      } else {
        draw();
      }
    } catch {
      // The mission closed meanwhile, or the connection failed: show how things are now.
      day = await api("GET", base).catch(() => day);
      onDay(day);
      draw();
    } finally {
      busy = false;
    }
  }

  function listen(step) {
    speak(step.text);
    note("step_spoken", step);
  }

  function close() {
    if (closed) return;
    closed = true;
    holder.remove();
    onClose(day);
  }

  note("mission_opened");
  draw();
  return { close };
}
