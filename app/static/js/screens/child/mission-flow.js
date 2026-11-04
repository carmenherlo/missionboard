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
  // seemed lost and children tapped twice). Taps go in a queue, in order: tapping
  // another step while one is saving is not lost (04/11). The panel is drawn again
  // from the server's answer once nothing else is waiting.
  let queue = Promise.resolve();
  let waiting = 0;
  const wanted = new Map(); // step id → checked, as last tapped
  let celebrated = false; // the last step came: what is still queued does not matter

  function toggle(step, card) {
    const checked = !(wanted.get(step.id) ?? step.checked);
    wanted.set(step.id, checked);
    card?.classList.toggle("step-card--done", checked);
    waiting += 1;
    queue = queue.then(() => send(step.id, checked)).finally(() => { waiting -= 1; });
  }

  async function send(stepId, checked) {
    if (closed || celebrated) return;
    try {
      const result = await api("PUT", `${base}/missions/${missionId}/steps/${stepId}`, { json: { checked } });
      day = result.today;
      onDay(day);
      if (result.completed) {
        celebrated = true;
        wanted.clear();
        holder.replaceChildren();
        showCelebration(holder, day, result.stars_earned, close);
        return;
      }
    } catch {
      // The mission closed meanwhile, or the connection failed: show how things are now.
      day = await api("GET", base).catch(() => day);
      onDay(day);
      wanted.clear();
    }
    if (waiting <= 1 && !closed) {
      wanted.clear();
      draw();
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
