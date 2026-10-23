import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export async function viewMissionsHome() {
  const [children] = await Promise.all([api("GET", "/api/children"), loadAvatars()]);
  // With one child there is nothing to choose: go straight to their missions.
  if (children.length === 1) {
    location.replace(`#/parents/config/missions/child/${children[0].id}`);
    return;
  }
  const counts = await Promise.all(
    children.map((c) => api("GET", `/api/children/${c.id}/missions`).then((m) => m.length)));

  const content = children.length
    ? [
        h("p", { class: "hint" }, t.missions.whose),
        h("div", { class: "kid-cards" },
          children.map((child, i) =>
            h("a", { class: "kid-card", href: `#/parents/config/missions/child/${child.id}` },
              avatar(child, { size: "xl" }),
              h("span", { class: "child-card__name" }, child.name),
              h("span", { class: counts[i] ? "pill" : "pill pill--muted" }, t.missions.count(counts[i]))))),
      ]
    : [
        h("p", { class: "empty" }, t.missions.noChildren),
        h("a", { class: "btn btn--primary", href: "#/parents/config/children/new" }, t.missions.addChild),
      ];

  render(
    parentsHeader(t.missions.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      ...content));
}
