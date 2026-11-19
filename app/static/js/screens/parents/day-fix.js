// Arreglar un día (19/11): in Padres · Niño a tap on a day of the week asks what it was:
// «Lo hizo» (they forgot to sign), «No lo hizo» (they signed without doing it) or «Libre».
// A day still to come can only be let off: a tap lets it off, or takes it back, as before.
import { api } from "../../api.js";
import { layer } from "../../components/layer.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

const isoToday = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export async function askDay(child, tanks, tank, { onDone }) {
  const today = tanks.find((x) => x.state === "now")?.day ?? isoToday();
  const save = (choice) => api("PUT", `api/children/${child.id}/days/${tank.day}`, { json: { choice } });
  if (tank.day > today) {
    // Ahead: a day off or not, nothing else.
    await api("PUT", `api/children/${child.id}/free-days/${tank.day}`, { json: { free: tank.state !== "free" } });
    onDone();
    return;
  }
  const error = h("p", { class: "form-error", role: "alert" });
  const run = async (choice) => {
    try {
      await save(choice);
      close();
      onDone();
    } catch {
      error.textContent = t.dayFix.error;
    }
  };
  const now = t.overview.weekLegend[tank.state] ?? "";
  const { close } = layer(h("div", { class: "open-today__form panel" },
    h("h2", { class: "panel__title" }, t.dayFix.title(child.name, tank.day)),
    now && h("p", { class: "hint" }, t.dayFix.now(now)),
    error,
    h("div", { class: "hold-menu" }, ["done", "missed", "free"].map((choice) =>
      h("button", { type: "button", class: "btn hold-menu__choice", onclick: () => run(choice) },
        h("b", {}, t.dayFix[choice]), h("small", {}, t.dayFix[`${choice}Hint`])))),
    h("div", { class: "form-actions" },
      h("button", { type: "button", class: "btn", onclick: () => close() }, t.common.cancel))));
}
