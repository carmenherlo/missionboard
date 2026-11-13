import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export async function viewChildrenList() {
  const [children, missions] = await Promise.all([api("GET", "api/children"), api("GET", "api/missions"), loadAvatars()]);
  const status = saveStatus();

  function row(child) {
    const actions = h("div", { class: "row__actions" });

    function showDefault() {
      actions.replaceChildren(
        h("button", { class: "btn btn--danger", type: "button", onclick: showConfirm }, t.children.delete));
    }

    function showConfirm() {
      actions.replaceChildren(
        h("span", { class: "row__confirm" }, t.children.confirmDelete(child.name)),
        h("button", { class: "btn btn--danger", type: "button", onclick: remove }, t.children.confirmYes),
        h("button", { class: "btn", type: "button", onclick: showDefault }, t.children.cancel));
    }

    async function remove() {
      try {
        await api("DELETE", `api/children/${child.id}`);
        viewChildrenList();
      } catch (err) {
        actions.prepend(h("span", { class: "form-error" }, errorMessage(err)));
      }
    }

    showDefault();
    // The whole card opens the child (rutinas-7, as every list of the parents' zone).
    return h("li", { class: "row row--covered" },
      avatar(child),
      h("a", {
        class: "row__name row__cover", href: `#/parents/config/children/${child.id}`,
        "aria-label": t.children.editNamed(child.name),
      }, child.name),
      actions);
  }

  render(
    parentsHeader(h("span", { class: "title-line" }, t.children.title, status.element), { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      children.length
        ? h("ul", { class: "rows" }, children.map(row))
        : h("p", { class: "empty" }, t.children.empty),
      h("a", { class: "btn btn--primary btn--block", href: "#/parents/config/children/new" },
        t.children.add),
      // The first child, and no missions yet: what comes next (Primeros pasos).
      children.length > 0 && !missions.length && h("a", { class: "row row--link", href: "#/parents/config/missions" },
        h("span", { class: "row__icon" }, icon("missions")),
        h("span", { class: "row__name" }, t.overview.nextMissions),
        h("span", { class: "row__chevron" }, icon("next"))),
      h("p", { class: "note" }, t.children.historyNote)));
}
