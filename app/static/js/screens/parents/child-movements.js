// Niños → Bea → Ver todos (ficha-nino.html, question 4): all their stars in and out.
import { api } from "../../api.js";
import { loadAvatars } from "../../components/avatar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { movementLines } from "./child-stars.js";
import { parentsHeader } from "./common.js";

export async function viewChildMovements(childId) {
  const [movements, children] = await Promise.all([api("GET", `api/overview/children/${childId}/movements`),
    api("GET", "api/children"), loadAvatars()]);
  const child = children.find((c) => c.id === childId);
  render(
    parentsHeader(t.childCard.movementsTitle(child.name), { href: `#/parents/config/children/${childId}`, label: child.name }),
    h("main", { class: "page" }, panel(null, movementLines(movements))));
}
