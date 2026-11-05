import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export async function viewChildrenList() {
  const [children] = await Promise.all([api("GET", "api/children"), loadAvatars()]);

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
    parentsHeader(t.children.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      children.length
        ? h("ul", { class: "rows" }, children.map(row))
        : h("p", { class: "empty" }, t.children.empty),
      h("a", { class: "btn btn--primary btn--block", href: "#/parents/config/children/new" },
        t.children.add),
      h("p", { class: "note" }, t.children.historyNote)));
}
