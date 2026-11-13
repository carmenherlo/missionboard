import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

// By groups (ajustes.html, reorganised 12/11): what the children do, what they earn, this tablet,
// the whole app (how it looks, its avatars, its code, its copies and its log).
const GROUPS = [
  [t.config.groupDay, [
    ["children", "children", t.config.children],
    ["missions", "missions", t.config.missions],
    ["routines", "clock", t.config.routines],
  ]],
  [t.config.groupRewards, [
    ["stars", "star", t.config.stars],
    ["streaks", "rocket", t.config.streaks],
    ["prizes", "prize", t.config.prizes],
    ["shop", "shop", t.config.shop],
  ]],
  [t.config.groupApp, [
    ["appearance", "palette", t.config.appearance],
    ["avatars", "smile", t.config.avatars],
    ["display", "eye", t.config.display], // only this tablet (was its own group, Este aparato)
    ["code", "parentCode", t.config.parentCode],
    ["backup", "download", t.config.backup],
    ["log", "history", t.config.eventLog],
  ]],
];

export function viewConfigIndex() {
  render(
    parentsHeader(t.config.title, { href: "#/parents", label: t.overview.back }),
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
