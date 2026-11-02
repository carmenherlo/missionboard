import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

// Choose children by tapping their cards; each gets an independent copy.
// Reached from the templates list or from the template's editor (`fromEditor`),
// and "←" / "Cancelar" go back there.
export async function viewTemplateApply(templateId, fromEditor = false) {
  const [template, children] = await Promise.all([
    api("GET", `/api/templates/${templateId}`),
    api("GET", "/api/children"),
    loadAvatars(),
  ]);
  const missionsOf = await Promise.all(
    children.map((c) => api("GET", `/api/children/${c.id}/missions`)));
  const listHref = "#/parents/config/templates";
  const backHref = fromEditor ? `${listHref}/${templateId}` : listHref;
  const header = parentsHeader(t.templateApply.title(template.name),
    { href: backHref, label: fromEditor ? template.name : t.templates.title });

  if (!children.length) {
    render(header, h("main", { class: "page" },
      h("p", { class: "empty" }, t.templateApply.noChildren),
      h("a", { class: "btn btn--primary", href: "#/parents/config/children/new" }, t.missions.addChild)));
    return;
  }

  const chosen = new Set();
  const error = h("p", { class: "form-error", role: "alert" });
  const submit = h("button", { type: "button", class: "btn btn--primary", onclick: applyTemplate });
  const chosenChildren = () => children.filter((c) => chosen.has(c.id));

  function renderSubmit() {
    const names = chosenChildren().map((c) => c.name);
    submit.textContent = t.templateApply.submit(names);
    submit.disabled = names.length === 0;
  }

  const cards = h("div", { class: "kid-cards" }, children.map((child, i) => {
    const alreadyHas = missionsOf[i].some((m) => m.name === template.name);
    const card = h("button", {
      type: "button", class: "kid-card kid-card--choice", "aria-pressed": "false",
      onclick: () => {
        const on = !chosen.has(child.id);
        if (on) chosen.add(child.id); else chosen.delete(child.id);
        card.classList.toggle("kid-card--selected", on);
        card.setAttribute("aria-pressed", String(on));
        renderSubmit();
      },
    },
    h("span", { class: "icon-button kid-card__check", "aria-hidden": "true" }, icon("check")),
    avatar(child, { size: "xl" }),
    h("span", { class: "child-card__name" }, child.name),
    alreadyHas && h("span", { class: "pill pill--muted" }, t.templateApply.alreadyHas(template.name)));
    return card;
  }));

  async function applyTemplate() {
    error.textContent = "";
    const applied = chosenChildren();
    try {
      await api("POST", `/api/templates/${templateId}/apply`, { json: { child_ids: applied.map((c) => c.id) } });
    } catch (err) {
      error.textContent = errorMessage(err);
      return;
    }
    render(header, h("main", { class: "page" },
      panel(null,
        h("p", { class: "form-success" }, t.templateApply.done(template.name, applied.map((c) => c.name))),
        h("p", { class: "hint" }, t.templateApply.doneHint),
        h("ul", { class: "rows" }, applied.map((child) =>
          h("li", {},
            h("a", { class: "row row--link", href: `#/parents/config/missions/child/${child.id}` },
              avatar(child, { size: "sm" }),
              h("span", { class: "row__name" }, t.childMissions.title(child.name)),
              h("span", { class: "row__chevron" }, icon("next"))))))),
      h("div", { class: "form-actions" }, h("a", { class: "btn btn--primary", href: listHref }, t.common.done))));
  }

  renderSubmit();
  render(header, h("main", { class: "page" },
    h("p", { class: "hint" }, t.templateApply.hint),
    cards,
    error,
    h("div", { class: "form-actions" }, h("a", { class: "btn", href: backHref }, t.common.cancel), submit)));
}
