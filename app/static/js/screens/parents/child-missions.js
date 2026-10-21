import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { sortable } from "../../components/sortable.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { missionSummary } from "./mission-summary.js";

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

  const list = h("ul", { class: "rows" }, missions.map((mission) =>
    h("li", { class: "row row--sortable", "data-id": mission.id },
      h("span", { class: "drag-handle", "aria-label": t.childMissions.dragLabel }, icon("drag")),
      imageThumb(mission.image_url),
      h("span", { class: "row__name" }, mission.name,
        h("small", { class: "row__detail" }, missionSummary(mission))),
      h("a", { class: "btn", href: `#/parents/config/missions/${mission.id}` }, t.childMissions.edit))));

  sortable(list, {
    onEnd: async (ids) => {
      error.textContent = "";
      try {
        await api("PUT", `/api/children/${childId}/missions/order`, { json: { ids } });
      } catch (err) {
        error.textContent = errorMessage(err);
      }
    },
  });

  render(
    h("main", { class: "page" },
      parentsHeader(h("span", { class: "title-with-avatar" }, avatar(child, { size: "sm" }), t.childMissions.title(child.name)), back),
      missions.length
        ? [h("p", { class: "hint" }, t.childMissions.routeHint(child.name)), list]
        : h("p", { class: "empty" }, t.childMissions.empty(child.name)),
      error,
      h("a", { class: "btn btn--primary btn--block", href: `#/parents/config/missions/child/${childId}/new` },
        t.childMissions.add)));
}
