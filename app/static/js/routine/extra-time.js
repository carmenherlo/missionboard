// «± Tiempo» (modo-carrera.html, screen 6): a routine started by hand going on, a parent
// adds minutes to a part, or takes them, only today. The code once; then each tap is
// saved at once and the routine goes on with it (on every device at its next check).
// The same list is in the parents' phone's panel (remote.js), where the code is known.
import { api } from "../api.js";
import { saveStatus } from "../components/save-status.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { askParentCode } from "./code-dialog.js";

const STEPS = [-5, -1, 1, 5];

export function extraTime(r) {
  function askExtra() {
    askParentCode(r, {
      title: t.routine.extraTitle,
      hint: t.routine.extraCodeHint,
      submit: t.routine.extraTime,
      send: async (parentCode) => {
        await api("POST", "api/parents/unlock", { json: { code: parentCode } });
        setTimeout(() => openPanel(parentCode)); // after the code's dialog closes
      },
    });
  }

  // Which parts can still change: in a race, those nobody finished yet (carrera-divertida.html);
  // by the clock, those not over.
  function over(index) {
    const { data } = r.showing;
    if (data.race) {
      const leg = r.legs().find((l) => l.part.id === data.parts[index].id);
      return !leg || leg.done.length === leg.having.length;
    }
    return r.parts()[index].to <= r.now();
  }

  // The parts with their minutes and −5 −1 +1 +5; `parentCode` null: the session's.
  function extraList(parentCode = null) {
    const status = saveStatus();
    const body = h("ul", { class: "rows extra-time__parts" });
    const hint = h("p", { class: "hint" });

    async function add(part, minutes) {
      await status.track(api("POST", `api/routines/${r.showing.data.id}/extra`, { parentCode, json: { part_id: part.id, minutes } }))
        .catch(() => {});
      await r.check();
      draw();
    }

    function draw() {
      if (!r.showing) return;
      const { data } = r.showing;
      const goingOn = data.race ? r.legs()[r.showing.race.index]?.part.id : r.phaseAt(r.now()).part?.id;
      body.replaceChildren(...data.parts.map((part, index) => {
        const done = over(index);
        return h("li", { class: `row row--compact${done ? " extra-time__over" : ""}` },
          part.image_url ? h("img", { class: "extra-time__image", src: part.image_url, alt: "" }) : "",
          h("span", { class: "row__text" }, part.text,
            h("span", { class: "hint" }, done ? ` · ${t.routine.extraOver}` : part.id === goingOn ? ` · ${t.routine.extraNow}` : "")),
          done ? "" : h("span", { class: "extra-time__steps" },
            STEPS.filter((n) => n < 0).map((n) => button(part, n)),
            h("b", { class: "extra-time__minutes" }, t.routine.minutes(part.minutes)),
            STEPS.filter((n) => n > 0).map((n) => button(part, n))));
      }));
      hint.textContent = data.race ? t.routine.extraRaceHint(Math.round(data.race.minutes)) : t.routine.extraHint;
    }

    const button = (part, n) => h("button", {
      type: "button", class: "btn extra-time__step",
      "aria-label": n < 0 ? t.routine.extraMinus(-n) : t.routine.extraPlus(n), onclick: () => add(part, n),
    }, n < 0 ? `−${-n}` : `+${n}`);

    draw();
    return { status: status.element, body, hint, draw };
  }

  function openPanel(parentCode) {
    if (!r.showing) return;
    const list = extraList(parentCode);
    const close = () => r.showing?.view.finish.replaceChildren();
    r.showing.view.finish.replaceChildren(h("div", { class: "routine__code extra-time", role: "dialog", "aria-modal": "true" },
      h("h2", {}, t.routine.extraTitle, list.status), list.body, list.hint,
      h("div", { class: "form-actions" }, h("button", { type: "button", class: "btn btn--primary", onclick: close }, t.routine.extraDone))));
  }

  return { askExtra, extraList };
}
