import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

// By groups (ajustes.html): what the children do, what they earn, this tablet, the whole app.
const GROUPS = [
  [t.config.groupDay, [
    ["children", "children", t.config.children],
    ["missions", "missions", t.config.missions],
    ["routines", "clock", t.config.routines],
  ]],
  [t.config.groupRewards, [
    ["prizes", "prize", t.config.prizes],
    ["shop", "shop", t.config.shop],
  ]],
  [t.config.groupDevice, [
    ["display", "eye", t.config.display],
  ]],
  [t.config.groupApp, [
    ["settings", "settings", t.config.settings],
    ["avatars", "smile", t.config.avatars],
    ["code", "parentCode", t.config.parentCode],
    ["backup", "download", t.config.backup],
    ["log", "history", t.config.eventLog],
  ]],
];

export function viewConfigIndex() {
  render(
    parentsHeader(t.config.title),
    h("main", { class: "page config-groups" },
      GROUPS.map(([title, sections]) =>
        h("section", { class: "config-group" },
          h("h2", { class: "section-title" }, title),
          h("ul", { class: "rows" },
            sections.map(([path, iconName, label]) =>
              h("li", {},
                h("a", { class: "row row--link", href: `#/parents/config/${path}` },
                  h("span", { class: "row__icon" }, icon(iconName)),
                  h("span", { class: "row__name" }, label),
                  h("span", { class: "row__chevron" }, icon("next"))))))))));
}
