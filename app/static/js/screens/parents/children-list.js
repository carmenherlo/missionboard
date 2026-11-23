// Niños (menu-padres-2.html): one row per child, opening their card (child-page.js), and
// «Añadir niño». Deleting a child is at the bottom of their card, far from a slip of the finger.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export async function viewChildrenList() {
  const [children, missions] = await Promise.all([api("GET", "api/children"), api("GET", "api/missions"), loadAvatars()]);
  const row = (child) => h("li", {},
    h("a", { class: "row row--link", href: `#/parents/config/children/${child.id}` },
      avatar(child),
      h("span", { class: "row__name" }, child.name),
      h("span", { class: "row__chevron" }, icon("next"))));

  render(
    parentsHeader(t.children.title), // Niños is a door of the menu: no back
    h("main", { class: "page" },
      children.length
        ? h("ul", { class: "rows" }, children.map(row))
        : h("p", { class: "empty" }, t.children.empty),
      // The big button only for the first child; afterwards, a quiet one under the family.
      children.length
        ? h("a", { class: "btn children-add", href: "#/parents/config/children/new" }, icon("plus"), t.children.addMore)
        : h("a", { class: "btn btn--primary btn--block", href: "#/parents/config/children/new" }, t.children.add),
      // The first child, and no missions yet: what comes next (Primeros pasos).
      children.length > 0 && !missions.length && h("a", { class: "row row--link", href: "#/parents/config/missions" },
        h("span", { class: "row__icon" }, icon("missions")),
        h("span", { class: "row__name" }, t.overview.nextMissions),
        h("span", { class: "row__chevron" }, icon("next")))));
}
