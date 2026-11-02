import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

// The children (each one's missions) and, below, the templates: always shown,
// even with one child or none, so templates can be prepared at any time.
export async function viewMissionsHome() {
  const [children, templates] = await Promise.all([
    api("GET", "/api/children"),
    api("GET", "/api/templates"),
    loadAvatars(),
  ]);
  const counts = await Promise.all(
    children.map((c) => api("GET", `/api/children/${c.id}/missions`).then((m) => m.length)));

  const kids = children.length
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
      ...kids,
      h("div", { class: "stack stack--tight section-gap" },
        h("a", { class: "row row--link", href: "#/parents/config/templates" },
          h("span", { class: "row__icon" }, icon("templates")),
          h("span", { class: "row__name" }, t.missions.templates,
            h("span", { class: "row__detail" },
              h("span", { class: "pill pill--muted" }, t.templates.count(templates.length)))),
          h("span", { class: "row__chevron" }, icon("next"))),
        h("p", { class: "hint" }, t.missions.templatesHint))));
}
