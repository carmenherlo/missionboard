import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { sortable } from "../../components/sortable.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { missionStyle } from "../child/ring.js";
import { parentsHeader } from "./common.js";
import { missionPills } from "./mission-summary.js";

// The family's missions, in the order of the children's route. Each card says who has
// something on, and opens the mission.
export async function viewMissionsHome() {
  const [missions, children] = await Promise.all([
    api("GET", "api/missions"),
    api("GET", "api/children"),
    loadAvatars(),
  ]);
  const error = h("p", { class: "form-error", role: "alert" });

  function renumber() {
    list.querySelectorAll(".order").forEach((el, i) => { el.textContent = i + 1; });
  }

  const list = h("ul", { class: "rows" }, missions.map((mission, i) =>
    h("li", { class: "row row--sortable row--covered row--mission", "data-id": mission.id, style: missionStyle(mission.colors) },
      h("span", { class: "drag-handle", "aria-label": t.missions.dragLabel }, icon("drag")),
      h("span", { class: "order order--mission" }, i + 1),
      imageThumb(mission.image_url, { size: "md", label: mission.name, suggested: mission.image_suggested }),
      h("a", {
        class: "row__name row__cover", href: `#/parents/config/missions/${mission.id}`,
        "aria-label": t.missions.editMission(mission.name),
      }, mission.name,
        h("span", { class: "row__detail" }, missionPills(mission))),
      h("span", { class: "kids-on" }, children
        .filter((child) => mission.children.find((c) => c.id === child.id)?.active > 0)
        .map((child) => avatar(child, { size: "sm" }))),
      h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")))));

  sortable(list, {
    onEnd: async (ids) => {
      renumber();
      error.textContent = "";
      try {
        await api("PUT", "api/missions/order", { json: { ids } });
      } catch (err) {
        error.textContent = errorMessage(err);
      }
    },
  });

  render(
    parentsHeader(t.missions.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "page-header" },
        h("p", { class: "hint" }, missions.length ? t.missions.hint : t.missions.empty),
        h("a", { class: "btn btn--primary", href: "#/parents/config/missions/new" }, icon("plus"), t.missions.add)),
      missions.length ? list : null,
      error));
}
