// A mission for one child (misiones-para-quien.html): whether it is theirs, and which of
// its tasks they do, each with all its steps; and, from Niños → Bea → Misiones, every
// mission with whether it is theirs. Texts and pictures are the mission's, once for everyone.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { missionStyle } from "../child/ring.js";
import { parentsHeader } from "./common.js";
import { childCount } from "./mission-edit.js";

const kidUrl = (missionId, childId) => `api/missions/${missionId}/children/${childId}`;

// "☑ Noa tiene esta misión": puts them in or takes them out, saved on the spot.
function theirsBox(mission, child, onChange) {
  return h("label", { class: "toggle" },
    h("input", {
      type: "checkbox", checked: mission.kids.includes(child.id), "aria-label": t.missionChild.theirs(child.name),
      onchange: (e) => onChange(e.target.checked),
    }),
    h("span", {}, t.missionChild.theirs(child.name)));
}

export async function viewMissionChild(missionId, childId, fromChild = false) {
  const [first, children] = await Promise.all([
    api("GET", `api/missions/${missionId}`),
    api("GET", "api/children"),
    loadAvatars(),
  ]);
  let mission = first;
  const child = children.find((c) => c.id === childId);
  const status = saveStatus();
  const back = fromChild
    ? { href: `#/parents/config/children/${childId}/missions`, label: t.missionChild.childMissions(child.name) }
    : { href: `#/parents/config/missions/${missionId}`, label: mission.name };
  const box = h("div", { class: "stack" });
  const isOn = (task) => mission.kids.includes(childId) && !(mission.off[childId] ?? []).includes(task.id);

  async function change(request) {
    mission = await status.track(request).catch(() => api("GET", `api/missions/${missionId}`));
    draw();
  }

  function taskRow(task) {
    const on = isOn(task);
    return h("li", { class: `row row--compact${on ? "" : " row--off"}` },
      h("input", {
        type: "checkbox", checked: on, disabled: !mission.kids.includes(childId), "aria-label": task.text,
        onchange: (e) => change(api("PUT", `${kidUrl(missionId, childId)}/tasks/${task.id}`, { json: { active: e.target.checked } })),
      }),
      imageThumb(task.image_url, { size: "sm", label: task.text }),
      h("span", { class: "row__text" }, task.text,
        task.steps.length > 0 && h("span", { class: "row__detail" }, t.missions.steps(task.steps.length))));
  }

  function draw() {
    const theirs = mission.kids.includes(childId);
    box.replaceChildren(
      theirsBox(mission, child, (on) => change(api("PUT", kidUrl(missionId, childId), { json: { on } }))),
      h("p", { class: "hint" }, !mission.tasks.length ? t.missionChild.empty
        : theirs ? t.missionChild.hint(child.name) : t.missionChild.notTheirs(child.name)),
      mission.tasks.length > 0 && h("ul", { class: "rows" }, mission.tasks.map(taskRow)));
  }
  draw();

  render(
    parentsHeader(h("span", { class: "title-line" },
      h("span", { class: "title-with-avatar" }, avatar(child, { size: "sm" }), t.missionChild.title(mission.name, child.name)),
      status.element), back),
    h("main", { class: "page", style: missionStyle(mission.colors) }, box));
}

export async function viewChildMissions(childId) {
  const [missions, children] = await Promise.all([
    api("GET", "api/missions"),
    api("GET", "api/children"),
    loadAvatars(),
  ]);
  const child = children.find((c) => c.id === childId);
  const status = saveStatus();

  function row(mission) {
    const theirs = mission.kids.includes(childId);
    const item = h("li", { class: `row row--covered row--mission${theirs ? "" : " row--off"}`, style: missionStyle(mission.colors) },
      h("input", {
        type: "checkbox", checked: theirs, "aria-label": t.missionChild.theirs(child.name),
        onchange: (e) => status.track(api("PUT", kidUrl(mission.id, childId), { json: { on: e.target.checked } }))
          .then((updated) => item.replaceWith(row(updated))).catch(() => {}),
      }),
      imageThumb(mission.image_url, { size: "md", label: mission.name }),
      h("a", { class: "row__name row__cover", href: `#/parents/config/children/${childId}/missions/${mission.id}` },
        mission.name,
        h("span", { class: "row__detail" }, theirs ? childCount(mission, childId) : t.missionChild.notHers)),
      h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")));
    return item;
  }

  render(
    parentsHeader(h("span", { class: "title-line" },
      h("span", { class: "title-with-avatar" }, avatar(child, { size: "sm" }), t.missionChild.childMissions(child.name)),
      status.element),
    { href: `#/parents/config/children/${childId}/settings`, label: t.childCard.settings(child.name) }),
    h("main", { class: "page" },
      h("p", { class: "hint" }, missions.length ? t.missionChild.childHint(child.name) : t.missions.empty),
      h("ul", { class: "rows" }, missions.map(row))));
}
