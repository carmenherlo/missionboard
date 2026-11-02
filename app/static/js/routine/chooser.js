// ⏰ on the home screen: start a routine by hand (rutinas-2), choosing who has
// come home. A panel over the home screen, like a mission's.
import { api, errorMessage } from "../api.js";
import { avatar, loadAvatars } from "../components/avatar.js";
import { h } from "../dom.js";
import { icon } from "../icons.js";
import { t } from "../texts.js";
import { refreshRoutines } from "./routine.js";

// The routines that can be started by hand today ([] when none).
export function routinesByHand() {
  return api("GET", "/api/routines/by-hand").catch(() => []);
}

export async function openChooser(routines) {
  await loadAvatars();
  const close = () => layer.remove();
  const layer = h("div", { class: "mission-layer chooser", onclick: (e) => { if (e.target === e.currentTarget) close(); } },
    h("section", { class: "mission-sheet", role: "dialog", "aria-modal": "true", "aria-label": t.routine.startByHand },
      h("header", { class: "mission-sheet__bar" },
        h("h2", { class: "mission-sheet__title" }, t.routine.startByHand),
        h("span", { class: "child-bar__spacer" }),
        h("button", { type: "button", class: "icon-button mission-sheet__close", "aria-label": t.child.close, onclick: close },
          icon("close"))),
      h("div", { class: "chooser__routines" }, routines.map((routine) => choice(routine, close)))));
  document.body.append(layer);
}

function choice(routine, close) {
  const chosen = new Set();
  const error = h("p", { class: "form-error", role: "alert" });
  const start = h("button", {
    type: "button", class: "btn btn--primary spin-button", disabled: true,
    onclick: async () => {
      start.disabled = true;
      try {
        await api("POST", `/api/routines/${routine.id}/start`, { json: { kids: [...chosen] } });
        close();
        refreshRoutines();
      } catch (err) {
        error.textContent = errorMessage(err);
        start.disabled = false;
      }
    },
  }, t.routine.start);
  const kids = routine.kids.map((kid) => {
    const { color, soft, strong, on } = kid.colors;
    const button = h("button", {
      type: "button", class: "routine-kid", "aria-pressed": "false",
      style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`,
      onclick: () => {
        if (chosen.has(kid.id)) chosen.delete(kid.id);
        else chosen.add(kid.id);
        button.classList.toggle("routine-kid--done", chosen.has(kid.id));
        button.setAttribute("aria-pressed", String(chosen.has(kid.id)));
        start.disabled = chosen.size === 0;
      },
    }, avatar(kid, { size: "md" }), h("span", { class: "routine-kid__name" }, kid.name));
    return h("li", {}, button);
  });
  return h("section", { class: "chooser__routine" },
    h("h3", { class: "chooser__name" }, routine.name, h("small", {}, ` · ${t.routine.minutes(routine.minutes)}`)),
    h("p", { class: "hint" }, t.routine.chooseKids),
    h("ul", { class: "chooser__kids" }, kids),
    error,
    start);
}
