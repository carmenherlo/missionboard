import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { sortable } from "../../components/sortable.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { missionPills } from "./mission-summary.js";

export async function viewChildMissions(childId) {
  const [children, missions] = await Promise.all([
    api("GET", "/api/children"),
    api("GET", `/api/children/${childId}/missions`),
    loadAvatars(),
  ]);
  const child = children.find((c) => c.id === childId);
  // With one child, "← Misiones" would bounce straight back here.
  const back = children.length > 1
    ? { href: "#/parents/config/missions", label: t.childMissions.back }
    : { href: "#/parents/config", label: t.config.back };
  const error = h("p", { class: "form-error", role: "alert" });

  // The order number follows the route, so it is redrawn after dragging.
  function renumber() {
    list.querySelectorAll(".order").forEach((el, i) => { el.textContent = i + 1; });
  }

  const list = h("ul", { class: "rows" }, missions.map((mission, i) =>
    h("li", { class: "row row--sortable", "data-id": mission.id },
      h("span", { class: "drag-handle", "aria-label": t.childMissions.dragLabel }, icon("drag")),
      h("span", { class: "order" }, i + 1),
      imageThumb(mission.image_url, { size: "md", label: mission.name, suggested: mission.image_suggested }),
      h("span", { class: "row__name" }, mission.name,
        h("span", { class: "row__detail" }, missionPills(mission))),
      h("a", {
        class: "icon-button icon-button--ghost", href: `#/parents/config/missions/${mission.id}`,
        "aria-label": t.childMissions.editMission(mission.name), title: t.childMissions.edit,
      }, icon("edit")))));

  sortable(list, {
    onEnd: async (ids) => {
      renumber();
      error.textContent = "";
      try {
        await api("PUT", `/api/children/${childId}/missions/order`, { json: { ids } });
      } catch (err) {
        error.textContent = errorMessage(err);
      }
    },
  });

  render(
    parentsHeader(h("span", { class: "title-with-avatar" }, avatar(child, { size: "sm" }), t.childMissions.title(child.name)), back),
    h("main", { class: "page" },
      h("div", { class: "page-header" },
        h("p", { class: "hint" }, missions.length ? t.childMissions.routeHint(child.name) : t.childMissions.empty(child.name)),
        h("a", { class: "btn btn--primary", href: `#/parents/config/missions/child/${childId}/new` },
          icon("plus"), t.childMissions.add)),
      missions.length ? list : null,
      error));
}
