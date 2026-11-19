// «¿No la ha hecho?» (dias-libres.html, section 6): a mission marked done by mistake is
// undone, and with it what hung from it. The window says first what goes: its star, the
// gift card of that day (a switch keeps it for them) and that day's tank.
import { api } from "../../api.js";
import { layer } from "../../components/layer.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

export async function askUndo(child, missionId, day, { onDone = () => {}, parentCode } = {}) {
  const url = `api/children/${child.id}/missions/${missionId}/days/${day}/undo`;
  const preview = await api("GET", url, { parentCode });
  let keepCard = false;
  const line = (iconName, text, extra = null) =>
    h("li", { class: "undo__line" }, h("span", { class: "row__icon" }, icon(iconName)), h("span", {}, text), extra);
  const unused = preview.cards.filter((c) => !c.used);
  const error = h("p", { class: "form-error", role: "alert" });

  const { close } = layer(h("div", { class: "open-today__form panel" },
    h("h2", { class: "panel__title" }, t.dayOff.undoTitle(preview.mission.name, child.name)),
    h("p", { class: "setting__label" }, t.dayOff.undoIntro),
    h("ul", { class: "undo" },
      line("missions", preview.reopens ? t.dayOff.undoReopens : t.dayOff.undoCloses),
      line("star", t.dayOff.undoStars(preview.stars)),
      ...unused.map((c) => line("prize", t.dayOff.undoCard(c.text))),
      ...preview.cards.filter((c) => c.used).map((c) => line("prize", t.dayOff.undoCardUsed(c.text))),
      preview.tank && line("rocket", t.dayOff.undoTank)),
    unused.length > 0 && h("label", { class: "toggle" },
      h("input", { type: "checkbox", onchange: (e) => { keepCard = e.target.checked; } }), t.dayOff.undoKeepCard),
    error,
    h("div", { class: "form-actions" },
      h("button", { type: "button", class: "btn", onclick: () => close() }, t.common.cancel),
      h("button", {
        type: "button", class: "btn btn--primary",
        onclick: async () => {
          try {
            const done = await api("POST", url, { json: { keep_card: keepCard }, parentCode });
            close();
            onDone(done);
          } catch {
            error.textContent = t.errors.generic;
          }
        },
      }, t.dayOff.undoDo))));
}
