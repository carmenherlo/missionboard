import { api } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { stepper } from "../../components/stepper.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import * as script from "../../routine/script.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { routineError } from "./routine-edit.js";

const TEXT_SAVE_DELAY_MS = 600;
const WARNING_CHOICES = [1, 2, 3, 5];

// A task in its routine: only what is the routine's own (its minutes, how the voice
// says it, the warnings), saved on the spot. Its text and picture are the mission's.
export async function viewRoutinePartEdit(routineId, partId) {
  const url = `api/routines/${routineId}`;
  const routineHref = `#/parents/config/routines/${routineId}`;
  let routine = await api("GET", url);
  const part = () => routine.parts.find((p) => p.id === partId);
  if (!part()) {
    location.replace(routineHref);
    return;
  }
  const isFirst = () => routine.parts[0].id === partId;
  const partUrl = `${url}/parts/${partId}`;
  const status = saveStatus();

  function save(request) {
    return status.track(request).then((updated) => {
      routine = updated;
      refresh();
      return routine;
    }).catch((err) => {
      status.fail(routineError(err));
      refresh();
      throw err;
    });
  }
  const patch = (json) => save(api("PATCH", partUrl, { json })).catch(() => {});

  // ---------- how the voice says it ----------
  let timer = null;
  const spoken = h("input", { type: "text", maxlength: 60, value: part().spoken ?? part().name });
  const commit = () => {
    clearTimeout(timer);
    const value = spoken.value.trim();
    if (value !== (part().spoken ?? part().name)) patch({ spoken: value });
  };
  spoken.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(commit, TEXT_SAVE_DELAY_MS);
  });
  spoken.addEventListener("blur", commit);

  // ---------- how long ----------
  const when = h("div", { class: "part-length" });
  function renderWhen() {
    const hint = routine.manual ? (isFirst() ? t.routinePart.firstByHand : t.routinePart.byHand)
      : isFirst() && routine.anchor !== "end" ? t.routinePart.first
      : routine.anchor === "end" ? t.routinePart.chained
      : t.routinePart.followsOn;
    when.replaceChildren(
      h("span", { class: "field__label" }, t.routinePart.length),
      stepper({
        value: part().minutes, min: 1, max: 180, format: t.routine.minutes, label: t.routinePart.length,
        onChange: (minutes) => patch({ minutes }),
      }),
      h("span", { class: "hint" }, [!routine.manual && t.routinePart.starts(part().start, part().end), hint]
        .filter(Boolean).join(" ")));
  }

  // ---------- what it says: seen here, changed in "Lo que dice la voz" (rutinas-5) ----------
  const says = h("p", { class: "voice-preview" });
  const tooLong = h("p", { class: "notice" }, t.routinePart.tooLong);
  function renderSays() {
    const p = part();
    says.textContent = `«${script.partOpening(p)} ${script.partLength({ minutes: p.minutes, kids: routine.kids.length })}»`;
    tooLong.hidden = !script.doesNotFit(p, p.minutes);
  }

  // ---------- warnings ----------
  const warnings = h("div", { class: "chips" });
  function renderWarnings() {
    const chosen = part().warnings ?? [1]; // none chosen: the usual one minute
    warnings.replaceChildren(...WARNING_CHOICES.filter((n) => n < part().minutes).map((n) => {
      const on = chosen.includes(n);
      return h("button", {
        type: "button", class: `chip${on ? " chip--on" : ""}`, "aria-pressed": String(on),
        onclick: () => patch({ warnings: on ? chosen.filter((w) => w !== n) : [...chosen, n].sort((a, b) => b - a) }),
      }, t.routinePart.warningMinutes(n));
    }));
  }

  // ---------- "Sin prisa" (modo-carrera.html): in a race, a part that must not be rushed ----------
  const slow = h("div", { class: "field" });
  function renderSlow() {
    slow.hidden = !routine.race;
    if (!routine.race) return;
    const minutes = part().slow_minutes;
    const put = (value) => save(api("PUT", `${partUrl}/slow`, { json: { minutes: value } })).catch(() => {});
    slow.replaceChildren(
      h("label", { class: "toggle" },
        h("input", { type: "checkbox", checked: Boolean(minutes), onchange: (e) => put(e.target.checked ? part().minutes : null) }),
        t.race.slowOn),
      minutes ? h("div", { class: "part-length" }, h("span", { class: "field__label" }, t.race.slowMinimum),
        stepper({ value: minutes, min: 1, max: part().minutes, format: t.routine.minutes, label: t.race.slowMinimum, onChange: put })) : "",
      h("span", { class: "hint" }, t.race.slowHintOn));
  }

  function refresh() {
    if (!part()) return;
    renderWhen();
    renderSlow();
    renderSays();
    renderWarnings();
  }
  refresh();

  render(
    parentsHeader(h("span", { class: "title-line" }, part().text, status.element), { href: routineHref, label: t.routineEdit.title(routine.name) }),
    h("main", { class: "page" },
      h("div", { class: "columns columns--equal" },
        h("div", { class: "stack" },
          panel(t.routinePart.panelPart,
            h("div", { class: "mission-identity" },
              imageThumb(part().image_url, { size: "lg", label: part().text }),
              h("label", {}, t.routinePart.spoken, spoken)),
            h("span", { class: "hint" }, t.routinePart.spokenHint),
            h("a", { class: "btn", href: `#/parents/config/missions/${routine.mission_id}/tasks/${partId}` }, t.routinePart.changeInMission),
            when, slow)),
        h("div", { class: "stack" },
          panel(t.routinePart.panelSay,
            says,
            tooLong,
            h("a", { class: "btn", href: `${routineHref}/voice/${partId}` }, icon("speaker"), t.routinePart.changeSay),
            warningsField(routine, warnings)))),
      h("div", { class: "page-footer" },
        h("span", {}),
        h("div", { class: "form-actions" },
          h("button", {
            type: "button", class: "btn",
            onclick: () => tryRoutine(routineId, routine.parts.findIndex((p) => p.id === partId)),
          }, t.routinePart.tryFromHere),
          h("a", { class: "btn btn--primary", href: routineHref }, t.common.done)))));
}

// The warnings before it ends: in a race they are not used (it warns by itself), greyed with why.
function warningsField(routine, warnings) {
  const racing = routine.manual && Boolean(routine.race);
  const field = h("div", { class: `field${racing ? " panel--unused" : ""}` },
    racing && h("p", { class: "hint" }, t.race.noWarnings),
    h("span", { class: "field__label" }, t.routinePart.warnings), warnings,
    h("span", { class: "hint" }, t.routinePart.warningsHint));
  field.inert = racing;
  return field;
}
