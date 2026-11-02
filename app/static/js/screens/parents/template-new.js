import { newMissionForm } from "../../components/new-mission-form.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export async function viewTemplateNew() {
  const backHref = "#/parents/config/templates";
  const form = await newMissionForm({
    createUrl: "/api/templates",
    itemUrl: (template) => `/api/templates/${template.id}`,
    cancelHref: backHref,
    missingName: t.templates.missingName,
    onCreated: (template) => { location.hash = `#/parents/config/templates/${template.id}`; },
  });
  render(
    parentsHeader(t.templates.newTitle, { href: backHref, label: t.templates.title }),
    h("main", { class: "page" }, form.element));
  form.focus();
}
