import { api, errorMessage, session } from "../../api.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";

// Asks for the parent code, then calls onUnlock().
export function viewParentsLock(onUnlock) {
  const input = h("input", {
    type: "password", inputmode: "numeric", autocomplete: "off",
    class: "code-input", "aria-label": t.lock.code, required: true,
  });
  const error = h("p", { class: "form-error", role: "alert" });

  async function onsubmit(event) {
    event.preventDefault();
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
      h("a", { class: "corner-button", href: "#/", "aria-label": t.lock.homeLabel }, "🏠"),
      h("form", { class: "lock", onsubmit },
        h("h1", {}, t.lock.title),
        h("label", {}, t.lock.code, input),
        error,
        h("button", { class: "btn btn--primary", type: "submit" }, t.lock.submit))));
  input.focus();
}
