// Zona de padres · Ajustes (menu-padres-2.html, 3d): the house rules as a page, the same
// groups as the menu at the side. On a phone it is the fourth door of the bottom bar.
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { notifyOnlyWithHA, SETTINGS } from "./menu.js";

const link = (href, iconName, label) => h("a", { class: "row row--link", href },
  h("span", { class: "row__icon" }, icon(iconName)),
  h("span", { class: "row__name" }, label),
  h("span", { class: "row__chevron" }, icon("next")));

export function viewSettingsHome() {
  const row = ([path, iconName, label, { notOnPhone = false } = {}]) => {
    const item = h("li", { class: notOnPhone ? "not-on-phone" : null }, link(`#/parents/config/${path}`, iconName, label));
    return path === "notify" ? notifyOnlyWithHA(item, "settings") : item;
  };
  render(
    parentsHeader(t.config.title),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        SETTINGS.map(([title, sections]) => panel(title, h("ul", { class: "rows" }, sections.map(row)))),
        link("#/", "home", t.menu.kids))));
}
