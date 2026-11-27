import { api, errorMessage } from "../../api.js";
import { loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { newMissionForm } from "../../components/new-mission-form.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { missionStyle } from "../child/ring.js";
import { parentsHeader } from "./common.js";

const LIST_HREF = "#/parents/config/missions";
const SHOWN_TASKS = 3;

const openMission = (mission) => { location.hash = `${LIST_HREF}/${mission.id}`; };

// A new mission: from scratch (the form, first) or from one of the app's templates below (a copy, the family's to
// change, for every child).
export async function viewMissionNew() {
  const [templates, children] = await Promise.all([
    api("GET", "api/mission-templates"),
    api("GET", "api/children"),
    loadAvatars(),
  ]);
  const form = await newMissionForm({
    createUrl: "api/missions",
    itemUrl: (mission) => `api/missions/${mission.id}`,
    cancelHref: LIST_HREF,
    missingName: t.missionNew.missingName,
    onCreated: openMission,
    children,
  });
  const error = h("p", { class: "form-error", role: "alert" });

  async function use(template, button) {
    button.disabled = true;
    error.textContent = "";
    try {
      openMission(await api("POST", `api/mission-templates/${template.id}/use`));
    } catch (err) {
      error.textContent = errorMessage(err);
      button.disabled = false;
    }
  }

  const rows = h("ul", { class: "rows" }, templates.map((template) => {
    const button = h("button", { class: "btn btn--primary", type: "button" }, t.missionNew.use);
    button.addEventListener("click", () => use(template, button));
    return h("li", { class: "row row--mission", style: missionStyle(template.colors) },
      imageThumb(template.image_url, { size: "md", label: template.name }),
      h("span", { class: "row__text" },
        h("span", { class: "row__name" }, template.name),
        h("span", { class: "row__detail" }, t.missionNew.tasks(template.tasks.map((task) => task.text), SHOWN_TASKS))),
      button);
  }));

  render(
    parentsHeader(t.missionNew.title, { href: LIST_HREF, label: t.missions.title }),
    h("main", { class: "page stack" },
      form.element,
      templates.length ? panel(t.missionNew.fromTemplate, h("p", { class: "hint" }, t.missionNew.templateHint), rows, error) : null));
  form.focus();
}
