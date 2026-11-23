// Zona de padres · Ajustes (menu-padres-2.html, 3d): the house rules as a page, with the
// same groups and lines as the menu at the side. On a phone it is the fourth door of
// the bottom bar; thin lines, not cards: it is a menu, read at a glance.
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { notifyOnlyWithHA, SETTINGS } from "./menu.js";

const line = (href, iconName, label, extra = "") => h("a", { class: `nav-item${extra}`, href },
  icon(iconName), h("span", {}, label), h("span", { class: "settings-list__chevron" }, icon("next")));

export function viewSettingsHome() {
  const item = ([path, iconName, label, { notOnPhone = false } = {}]) => {
    const link = line(`#/parents/config/${path}`, iconName, label, notOnPhone ? " not-on-phone" : "");
    return path === "notify" ? notifyOnlyWithHA(link, "settings") : link;
  };
  render(
    parentsHeader(t.config.title),
    h("main", { class: "page" },
      h("nav", { class: "settings-list", "aria-label": t.config.title },
        SETTINGS.flatMap(([title, sections]) => [h("p", { class: "drawer__group" }, title), ...sections.map(item)]),
        h("hr", { class: "drawer__line" }),
        line("#/", "home", t.menu.kids))));
}
