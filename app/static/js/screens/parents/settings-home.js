// Zona de padres · Ajustes (menu-padres-2.html, 3d): the house rules as a page, the same
// groups as the menu at the side. Each group a card of its own, its lines split by thin
// rules and its icons in the group's colour, so a glance tells them apart. On a phone it
// is the fourth door of the bottom bar.
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { notifyOnlyWithHA, SETTINGS } from "./menu.js";

const line = (href, iconName, label, extra = "") => h("a", { class: `settings-line${extra}`, href },
  h("span", { class: "settings-line__icon" }, icon(iconName)),
  h("span", { class: "settings-line__name" }, label),
  h("span", { class: "settings-line__chevron" }, icon("next")));

function group([title, sections, key]) {
  const item = ([path, iconName, label, { notOnPhone = false } = {}]) => {
    const link = line(`#/parents/config/${path}`, iconName, label, notOnPhone ? " not-on-phone" : "");
    return path === "notify" ? notifyOnlyWithHA(link, "settings") : link;
  };
  return h("section", { class: `settings-group settings-group--${key}` },
    h("h2", { class: "settings-group__title" }, title),
    h("div", { class: "settings-group__card" }, sections.map(item)));
}

export function viewSettingsHome() {
  render(
    parentsHeader(t.config.title),
    h("main", { class: "page" },
      h("nav", { class: "settings-list", "aria-label": t.config.title },
        SETTINGS.map(group))));
}
