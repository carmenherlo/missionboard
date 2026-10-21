import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export function viewConfigIndex() {
  const sections = [
    { href: "#/parents/config/children", icon: "🧒", label: t.config.children },
    { href: "#/parents/config/code", icon: "🔒", label: t.config.parentCode },
  ];
  render(
    h("main", { class: "page" },
      parentsHeader(t.config.title, { href: "#/", label: t.config.exit }),
      h("ul", { class: "rows" },
        sections.map(({ href, icon, label }) =>
          h("li", {},
            h("a", { class: "row row--link", href },
              h("span", { class: "row__icon" }, icon),
              h("span", { class: "row__name" }, label),
              h("span", { class: "row__chevron" }, "›")))))));
}
