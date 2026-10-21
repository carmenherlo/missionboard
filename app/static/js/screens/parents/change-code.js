import { ApiError, api, errorMessage, session } from "../../api.js";
import { codeField } from "../../components/code-input.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export function viewChangeCode() {
  const current = codeField(t.changeCode.current);
  const fresh = codeField(t.changeCode.new);
  const repeat = codeField(t.changeCode.repeat);
  const [currentCode, newCode, repeatCode] = [current.input, fresh.input, repeat.input];
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
    if (newCode.value === currentCode.value) {
      error.textContent = t.changeCode.sameAsCurrent;
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
      if (err instanceof ApiError && err.status === 403) error.textContent = t.changeCode.wrongCurrent;
      else if (err instanceof ApiError && err.status === 409) error.textContent = t.changeCode.sameAsCurrent;
      else error.textContent = errorMessage(err);
      currentCode.value = "";
      currentCode.focus();
    }
  }

  // novalidate: our messages replace the browser's own pop-ups.
  const form = h("form", { class: "lock lock--left", novalidate: true, onsubmit },
    current.field,
    fresh.field,
    repeat.field,
    error,
    h("button", { class: "btn btn--primary", type: "submit" }, t.changeCode.submit));

  render(
    parentsHeader(t.changeCode.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      form));
  currentCode.focus();
}
