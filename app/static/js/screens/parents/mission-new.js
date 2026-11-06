import { newMissionForm } from "../../components/new-mission-form.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const LIST_HREF = "#/parents/config/missions";

export async function viewMissionNew() {
  const form = await newMissionForm({
    createUrl: "api/missions",
    itemUrl: (mission) => `api/missions/${mission.id}`,
    cancelHref: LIST_HREF,
    missingName: t.missionNew.missingName,
    onCreated: (mission) => { location.hash = `${LIST_HREF}/${mission.id}`; },
  });
  render(
    parentsHeader(t.missionNew.title, { href: LIST_HREF, label: t.missions.title }),
    h("main", { class: "page" }, form.element));
  form.focus();
}
