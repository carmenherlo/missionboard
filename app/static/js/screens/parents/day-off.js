// "Hoy no puede…" (dias-libres.html, section 3): a child let off a whole day or some of
// its missions, today, tomorrow or another day to come, with an optional sentence the
// voice says. Every change saves on the spot; "Listo" closes.
import { api } from "../../api.js";
import { layer } from "../../components/layer.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

const plusDays = (iso, n) => {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
};

// today: the app's day ("2026-11-19"); onClose: once closed, if something was saved (the board looks again).
export function askDayOff(child, today, { onClose = () => {} } = {}) {
  let day = today;
  let saved = false;
  let view = null;
  const body = h("div", { class: "stack stack--tight" });
  const error = h("p", { class: "form-error", role: "alert" });
  const url = () => `api/children/${child.id}/day-offs/${day}`;

  async function load() {
    view = await api("GET", url());
    draw();
  }

  async function save(change) {
    const off = view.missions.filter((m) => m.off).map((m) => m.id);
    const json = { whole: view.whole, missions: off, phrase: view.phrase, ...change };
    try {
      view = await api("PUT", url(), { json });
      error.textContent = "";
      saved = true;
    } catch {
      error.textContent = t.errors.generic;
    }
    draw();
  }

  const when = () => {
    const choices = [[today, t.dayOff.whenToday], [plusDays(today, 1), t.dayOff.whenTomorrow]];
    const other = !choices.some(([d]) => d === day);
    return h("div", { class: "tabs tabs--wrap" },
      choices.map(([d, text]) => h("button", {
        type: "button", class: `tab${day === d ? " tab--on" : ""}`, "aria-pressed": String(day === d),
        onclick: () => { day = d; load(); },
      }, day === d && icon("check"), text)),
      h("label", { class: `tab${other ? " tab--on" : ""}` }, t.dayOff.whenOther,
        h("input", {
          type: "date", class: "day-off__date", min: today, value: other ? day : "",
          onchange: (e) => { if (e.target.value >= today) { day = e.target.value; load(); } },
        })));
  };

  const toggle = (text, picture, on, onToggle) => h("label", { class: "toggle day-off__option" },
    h("input", { type: "checkbox", checked: on, onchange: (e) => onToggle(e.target.checked) }),
    picture, h("span", {}, text));

  function draw() {
    if (!view) return;
    const missions = view.missions;
    body.replaceChildren(
      when(),
      missions.length === 0
        ? h("p", { class: "hint" }, t.dayOff.nothingThatDay)
        : h("div", { class: "stack stack--tight" },
            toggle(t.dayOff.whole, icon("today"), view.whole, (on) => save({ whole: on })),
            !view.whole && h("p", { class: "setting__label" }, t.dayOff.some),
            !view.whole && missions.map((m) => toggle(m.name, imageThumb(m.image_url, { size: "sm", label: m.name }), m.off,
              (on) => save({ missions: missions.filter((x) => (x.id === m.id ? on : x.off)).map((x) => x.id) }))),
            (view.whole || missions.some((m) => m.off)) && h("label", {}, t.dayOff.phraseLabel(child.name),
              h("input", {
                type: "text", maxlength: 80, value: view.phrase, placeholder: t.dayOff.phrasePlaceholder,
                onchange: (e) => save({ phrase: e.target.value }),
              }))),
      error);
  }

  const { close } = layer(h("div", { class: "open-today__form panel day-off" },
    h("h2", { class: "panel__title" }, t.dayOff.dialogTitle(child.name)),
    body,
    h("div", { class: "form-actions" },
      h("button", { type: "button", class: "btn btn--primary", onclick: () => close() }, t.dayOff.close))),
  { onClose: () => saved && onClose() });
  load().catch(() => { error.textContent = t.errors.generic; body.replaceChildren(error); });
}
