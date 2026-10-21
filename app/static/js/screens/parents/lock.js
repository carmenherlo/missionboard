import { api, errorMessage, session } from "../../api.js";
import { codeField } from "../../components/code-input.js";
import { cornerButton } from "../../components/corner-button.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";

// Asks for the parent code, then calls onUnlock().
export function viewParentsLock(onUnlock) {
  const { field, input } = codeField(t.lock.code);
  const error = h("p", { class: "form-error", role: "alert" });

  async function onsubmit(event) {
    event.preventDefault();
    if (!input.value) {
      error.textContent = t.lock.missing;
      return;
    }
    try {
      await api("POST", "/api/parents/unlock", { json: { code: input.value } });
      session.parentCode = input.value;
      onUnlock();
    } catch (err) {
      error.textContent = errorMessage(err);
      input.value = "";
      input.focus();
    }
  }

  render(
    h("main", { class: "page page--center" },
      cornerButton("#/", "home", t.home.homeLabel),
      h("form", { class: "lock", novalidate: true, onsubmit },
        h("h1", {}, t.lock.title),
        field,
        error,
        h("button", { class: "btn btn--primary", type: "submit" }, t.lock.submit))));
  input.focus();
}
