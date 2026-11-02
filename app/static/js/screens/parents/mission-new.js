import { api, errorMessage } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { newMissionForm } from "../../components/new-mission-form.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { missionPills } from "./mission-summary.js";

// Two ways side by side: from scratch (left) or from a template (right).
export async function viewMissionNew(childId) {
  const [children, templates] = await Promise.all([
    api("GET", "/api/children"),
    api("GET", "/api/templates"),
  ]);
  const child = children.find((c) => c.id === childId);
  const backHref = `#/parents/config/missions/child/${childId}`;
  const openMission = (mission) => { location.hash = `#/parents/config/missions/${mission.id}`; };

  const form = await newMissionForm({
    createUrl: `/api/children/${childId}/missions`,
    itemUrl: (mission) => `/api/missions/${mission.id}`,
    cancelHref: backHref,
    missingName: t.missionNew.missingName,
    onCreated: openMission,
  });

  const error = h("p", { class: "form-error", role: "alert" });
  // "Usar": the copy is made at once and opened to adjust it.
  const useTemplate = (template) => async () => {
    error.textContent = "";
    try {
      const [mission] = await api("POST", `/api/templates/${template.id}/apply`, { json: { child_ids: [childId] } });
      openMission(mission);
    } catch (err) {
      error.textContent = errorMessage(err);
    }
  };

  const fromTemplate = templates.length > 0 && h("div", { class: "stack" },
    h("p", { class: "section-title" }, t.missionNew.fromTemplate),
    panel(null,
      h("p", { class: "hint" }, t.missionNew.fromTemplateHint(child.name)),
      h("ul", { class: "rows" }, templates.map((template) =>
        h("li", { class: "row row--compact" },
          imageThumb(template.image_url, { size: "sm", label: template.name, suggested: template.image_suggested }),
          h("span", { class: "row__name row__name--md" }, template.name,
            h("span", { class: "row__detail" }, missionPills(template))),
          h("button", {
            type: "button", class: "btn", onclick: useTemplate(template),
            "aria-label": t.missionNew.useNamed(template.name),
          }, t.missionNew.use)))),
      error));

  render(
    parentsHeader(t.missionNew.title(child.name), { href: backHref, label: t.childMissions.title(child.name) }),
    h("main", { class: "page" },
      fromTemplate
        ? h("div", { class: "columns columns--equal" },
          h("div", { class: "stack" }, h("p", { class: "section-title" }, t.missionNew.fromScratch), form.element),
          fromTemplate)
        : form.element));
  form.focus();
}
