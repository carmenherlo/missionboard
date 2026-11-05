import { api, apiFile, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const LATEST = 20;

// Look only: download the whole log, and see the latest events to check it works.
export async function viewEventLog() {
  const [log, children] = await Promise.all([
    api("GET", `api/events?limit=${LATEST}`),
    api("GET", "api/children"),
    loadAvatars(),
  ]);
  const childrenById = new Map(children.map((child) => [child.id, child]));

  render(
    parentsHeader(t.eventLog.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("p", { class: "hint" }, t.eventLog.intro),
        downloadPanel(log),
        log.latest.length > 0 && panel(t.eventLog.latest,
          h("ul", { class: "rows" }, log.latest.map((event) => eventRow(event, childrenById))),
          log.count > LATEST && h("p", { class: "hint" }, t.eventLog.latestHint(LATEST))))));
}

function downloadPanel(log) {
  const error = h("p", { class: "form-error", role: "alert" });
  const button = h("button", {
    type: "button", class: "btn btn--primary", disabled: log.count === 0,
    onclick: async () => {
      error.textContent = "";
      try {
        const { blob, filename } = await apiFile("api/events/export.csv");
        const url = URL.createObjectURL(blob);
        h("a", { href: url, download: filename }).click();
        URL.revokeObjectURL(url);
      } catch (err) {
        error.textContent = errorMessage(err);
      }
    },
  }, icon("download"), t.eventLog.downloadButton(log.count));
  return panel(t.eventLog.download,
    h("p", {}, t.eventLog.downloadText),
    h("div", { class: "form-actions form-actions--start" }, button),
    error,
    h("p", { class: "hint" }, log.first_day ? t.eventLog.since(dayText(log.first_day)) : t.eventLog.empty));
}

function eventRow(event, childrenById) {
  return h("li", { class: "row row--compact" },
    h("span", { class: "row__time" }, timeText(event.at)),
    who(event, childrenById),
    h("span", { class: "row__text" }, event.description));
}

// Parents, a child (as they look now; their initial if deleted), or nobody in particular (home).
function who(event, childrenById) {
  if (event.zone === "parents") {
    return h("span", { class: "row__icon row__icon--sm", "aria-label": t.eventLog.parents }, icon("parentCode"));
  }
  if (!event.child_id) return h("span", { class: "row__icon row__icon--sm" }, icon("home"));
  return avatar(childrenById.get(event.child_id) ?? { name: event.child_name }, { size: "sm" });
}

// "2026-11-03" → "03/11/2026"
function dayText(isoDay) {
  return isoDay.split("-").reverse().join("/");
}

// "Hoy 19:42", "Ayer 18:05" or "03/11 17:12"
function timeText(iso) {
  const at = new Date(iso);
  const time = at.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
  const day = (date) => date.toDateString();
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  if (day(at) === day(new Date())) return `${t.eventLog.today} ${time}`;
  if (day(at) === day(yesterday)) return `${t.eventLog.yesterday} ${time}`;
  return `${at.toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" })} ${time}`;
}
