// A mission as one child will see it, to switch on and off what they do; and, from
// Niños → Bea → Misiones, every mission with how much they have on. Texts and pictures
// are not written here: they are the mission's, once for everyone.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { missionStyle } from "../child/ring.js";
import { activationCard } from "../child/task-cards.js";
import { parentsHeader } from "./common.js";
import { childCount } from "./mission-edit.js";

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
  const grid = h("div", { class: "task-grid task-grid--parents" });
  const isOn = (id) => !(mission.off[childId] ?? []).includes(id);

  async function toggle(item) {
    const active = !isOn(item.id);
    mission = { ...mission, off: { ...mission.off, [childId]:
      active ? (mission.off[childId] ?? []).filter((id) => id !== item.id) : [...(mission.off[childId] ?? []), item.id] } };
    draw();
    mission = await status.track(api("PUT", `api/missions/${missionId}/children/${childId}/items/${item.id}`, { json: { active } }))
      .catch(() => api("GET", `api/missions/${missionId}`));
    draw();
  }

  function draw() {
    grid.replaceChildren(...mission.tasks.map((task) => activationCard(task, { isOn, onTap: toggle })));
  }
  draw();

  render(
    parentsHeader(h("span", { class: "title-line" },
      h("span", { class: "title-with-avatar" }, avatar(child, { size: "sm" }), t.missionChild.title(mission.name, child.name)),
      status.element), back),
    h("main", { class: "page", style: missionStyle(mission.colors) },
      h("p", { class: "hint" }, mission.tasks.length ? t.missionChild.hint(child.name) : t.missionChild.empty),
      grid));
}

export async function viewChildMissions(childId) {
  const [missions, children] = await Promise.all([
    api("GET", "api/missions"),
    api("GET", "api/children"),
    loadAvatars(),
  ]);
  const child = children.find((c) => c.id === childId);

  render(
    parentsHeader(h("span", { class: "title-with-avatar" }, avatar(child, { size: "sm" }), t.missionChild.childMissions(child.name)),
      { href: `#/parents/config/children/${childId}`, label: child.name }),
    h("main", { class: "page" },
      h("p", { class: "hint" }, missions.length ? t.missionChild.childHint(child.name) : t.missions.empty),
      h("ul", { class: "rows" }, missions.map((mission) =>
        h("li", { class: "row row--covered row--mission", style: missionStyle(mission.colors) },
          imageThumb(mission.image_url, { size: "md", label: mission.name }),
          h("a", { class: "row__name row__cover", href: `#/parents/config/children/${childId}/missions/${mission.id}` },
            mission.name,
            h("span", { class: "row__detail" }, childCount(mission, childId))),
          h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")))))));
}
