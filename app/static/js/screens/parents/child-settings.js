// Niños → Bea → Ajustes de Bea (ficha-nino.html, 2b): all of a child's settings together,
// out of their card: name and avatar, their missions (how many they have on) and, at
// the bottom, deleting them (asks first; their history stays).
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const link = (href, lead, name, detail = null) => h("a", { class: "row row--link", href },
  lead, h("span", { class: "row__text" }, name, detail && h("span", { class: "row__detail" }, detail)),
  h("span", { class: "row__chevron" }, icon("next")));

function deleteBox(child) {
  const box = h("div", {});
  const ask = () => box.replaceChildren(confirmBar({
    message: t.children.confirmDelete(child.name), detail: t.children.historyNote, confirmLabel: t.children.confirmYes,
    onCancel: draw,
    onConfirm: async () => {
      await api("DELETE", `api/children/${child.id}`);
      location.hash = "#/parents/config/children";
    },
  }));
  const draw = () => box.replaceChildren(
    h("button", { type: "button", class: "btn btn--danger", onclick: ask }, icon("trash"), t.children.deleteNamed(child.name)));
  draw();
  return box;
}

export async function viewChildSettings(childId) {
  const [children, missions] = await Promise.all([api("GET", "api/children"), api("GET", "api/missions"), loadAvatars()]);
  const child = children.find((c) => c.id === childId);
  if (!child) {
    location.hash = "#/parents/config/children";
    return;
  }
  const here = `#/parents/config/children/${childId}`;
  const on = missions.filter((m) => m.children.find((c) => c.id === childId)?.active).length;

  render(
    parentsHeader(t.childCard.settings(child.name), { href: here, label: child.name }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("ul", { class: "rows" },
          h("li", {}, link(`${here}/edit`, avatar(child, { size: "sm" }), t.children.identity)),
          h("li", {}, link(`${here}/missions`, h("span", { class: "row__icon" }, icon("missions")),
            t.missionChild.childMissions(child.name), t.childCard.missionsOn(on, missions.length)))),
        deleteBox(child))));
}
