// A child's mission opened over whatever is on screen (their route, or the
// clock of a routine): the panel with its tasks (their steps only as reminders),
// marking and unmarking them, 🔊, and the celebration when the last one is marked.
import { api } from "../../api.js";
import { speak } from "../../components/speech.js";
import { h } from "../../dom.js";
import { showCelebration } from "./celebration.js";
import { missionSheet } from "./mission-sheet.js";

// What a child marks of a mission: its tasks (misiones-3: steps are reminders).
export function marksOf(mission) {
  return mission.tasks.map((task) => task.id);
}

// day: the child's day (GET /api/children/<id>/today), or null to fetch it.
// onDay(day): the day changed (a step, the mission done). onClose(day): it is gone.
// pretend: a routine's trial (rutinas-7): { checked: Set of ids, onChange(checked, ids) }.
// What they mark starts as `checked` says and nothing reaches the server: no stars, nothing logged.
// current: the id of the task of the routine's part going on.
// Returns { close } to close it from outside (a routine's new part).
export async function openMission(container, childId, missionId, { day = null, onDay = () => {}, onClose = () => {}, pretend = null, current = null } = {}) {
  const base = `api/children/${childId}/today`;
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
    let mission = day.missions.find((m) => m.id === missionId);
    if (!mission) return close();
    if (pretend) mission = pretended(mission);
    holder.replaceChildren(missionSheet(day, mission, { onMark: toggle, onSpeak: listen, onClose: close, again: drawn, current }));
    drawn = true;
  }

  // In a trial, marked as the trial says, whatever today's real state is.
  function pretended(mission) {
    const has = (id) => pretend.checked.has(id);
    const tasks = mission.tasks.map((task) => ({ ...task, checked: has(task.id) }));
    const done = marksOf(mission).filter(has).length;
    return { ...mission, state: "open", tasks, done };
  }

  // It changes as soon as it is tapped (03/11: waiting for the server, a tap seemed
  // lost and children tapped twice). Taps go in a queue, in order: tapping another one
  // while one is saving is not lost (04/11). The panel is drawn again from the server's
  // answer once nothing else is waiting.
  let queue = Promise.resolve();
  let waiting = 0;
  const wanted = new Map(); // id → checked, as last tapped
  let celebrated = false; // the last one came: what is still queued does not matter

  // element: the task's card.
  function toggle(item, element) {
    if (pretend) return toggleOnlyHere(item);
    const checked = !(wanted.get(item.id) ?? item.checked);
    wanted.set(item.id, checked);
    element?.classList.toggle("task-card--done", checked);
    element?.setAttribute("aria-pressed", String(checked));
    waiting += 1;
    queue = queue.then(() => send(item.id, checked)).finally(() => { waiting -= 1; });
  }

  async function send(itemId, checked) {
    if (closed || celebrated) return;
    try {
      const result = await api("PUT", `${base}/missions/${missionId}/marks/${itemId}`, { json: { checked } });
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

  // A trial: it changes here only; the last one, the celebration (no stars).
  function toggleOnlyHere(item) {
    if (celebrated) return;
    const checked = new Set(pretend.checked);
    if (checked.has(item.id)) checked.delete(item.id);
    else checked.add(item.id);
    pretend.checked = checked;
    const ids = marksOf(day.missions.find((m) => m.id === missionId));
    pretend.onChange(checked, ids);
    if (ids.every((id) => checked.has(id))) {
      celebrated = true;
      holder.replaceChildren();
      showCelebration(holder, day, 0, close);
      return;
    }
    draw();
  }

  // 🔊 on a card: the task and its steps.
  function listen(task) {
    speak([task.text, ...task.steps.map((st) => st.text)]);
    if (!pretend) note("step_spoken", task);
  }

  function close() {
    if (closed) return;
    closed = true;
    holder.remove();
    onClose(day);
  }

  if (!pretend) note("mission_opened");
  draw();
  return { close };
}
