import { ApiError, api, errorMessage, session } from "../../api.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export function viewChangeCode() {
  const codeInput = () => h("input", {
    type: "password", inputmode: "numeric", autocomplete: "off",
    class: "code-input", minlength: 4, maxlength: 8, required: true,
  });
  const currentCode = codeInput();
  const newCode = codeInput();
  const repeatCode = codeInput();
  const error = h("p", { class: "form-error", role: "alert" });

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = "";
    if (!currentCode.value) {
      error.textContent = t.changeCode.missingCurrent;
      return;
    }
    if (!/^\d{4,8}$/.test(newCode.value)) {
      error.textContent = t.changeCode.badFormat;
      return;
    }
    if (newCode.value !== repeatCode.value) {
      error.textContent = t.changeCode.mismatch;
      return;
    }
    try {
      await api("PUT", "/api/parents/code", {
        json: { current_code: currentCode.value, code: newCode.value },
      });
      session.parentCode = newCode.value;
      // Drop the form entirely: only the message and the back link remain.
      form.replaceWith(h("p", { class: "form-success", role: "status" }, t.changeCode.done));
    } catch (err) {
      error.textContent = err instanceof ApiError && err.status === 403
        ? t.changeCode.wrongCurrent
        : errorMessage(err);
      currentCode.value = "";
      currentCode.focus();
    }
  }

  const form = h("form", { class: "lock lock--left", onsubmit },
    h("label", {}, t.changeCode.current, currentCode),
    h("label", {}, t.changeCode.new, newCode),
    h("label", {}, t.changeCode.repeat, repeatCode),
    error,
    h("button", { class: "btn btn--primary", type: "submit" }, t.changeCode.submit));

  render(
    h("main", { class: "page" },
      parentsHeader(t.changeCode.title, { href: "#/parents/config", label: t.config.back }),
      form));
  currentCode.focus();
}
