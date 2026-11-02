import { api } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { missionPills } from "./mission-summary.js";

// Same cards as a child's missions, without order: templates have no route.
export async function viewTemplatesList() {
  const templates = await api("GET", "/api/templates");

  const list = h("ul", { class: "rows" }, templates.map((template) =>
    h("li", { class: "row" },
      imageThumb(template.image_url, { size: "md", label: template.name, suggested: template.image_suggested }),
      h("span", { class: "row__name" }, template.name,
        h("span", { class: "row__detail" }, missionPills(template))),
      h("span", { class: "row__actions" },
        h("a", {
          class: "btn", href: `#/parents/config/templates/${template.id}/apply`,
          "aria-label": t.templates.applyNamed(template.name),
        }, t.templates.apply),
        h("a", {
          class: "icon-button icon-button--ghost", href: `#/parents/config/templates/${template.id}`,
          "aria-label": t.templates.editNamed(template.name), title: t.childMissions.edit,
        }, icon("edit"))))));

  render(
    parentsHeader(t.templates.title, { href: "#/parents/config/missions", label: t.missions.title }),
    h("main", { class: "page" },
      h("div", { class: "page-header" },
        h("p", { class: "hint" }, templates.length ? t.templates.hint : t.templates.empty),
        h("a", { class: "btn btn--primary", href: "#/parents/config/templates/new" }, icon("plus"), t.templates.add)),
      templates.length ? list : null));
}
