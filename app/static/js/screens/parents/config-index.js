import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export function viewConfigIndex() {
  const sections = [
    { href: "#/parents/config/children", iconName: "children", label: t.config.children },
    { href: "#/parents/config/missions", iconName: "missions", label: t.config.missions },
    { href: "#/parents/config/code", iconName: "parentCode", label: t.config.parentCode },
  ];
  render(
    parentsHeader(t.config.title),
    h("main", { class: "page" },
      h("ul", { class: "rows" },
        sections.map(({ href, iconName, label }) =>
          h("li", {},
            h("a", { class: "row row--link", href },
              h("span", { class: "row__icon" }, icon(iconName)),
              h("span", { class: "row__name" }, label),
              h("span", { class: "row__chevron" }, icon("next"))))))));
}
