import { errorMessage } from "../api.js";
import { h } from "../dom.js";
import { t } from "../texts.js";

// Inline confirmation for destructive actions: says what goes away and what stays.
export function confirmBar({ message, detail, confirmLabel, onConfirm, onCancel }) {
  const error = h("p", { class: "form-error", role: "alert" });
  const bar = h("div", { class: "confirm-bar", role: "alertdialog" },
    h("div", { class: "confirm-bar__text" },
      h("strong", {}, message),
      detail && h("span", {}, detail),
      error),
    h("div", { class: "confirm-bar__actions" },
      h("button", { class: "btn", type: "button", onclick: onCancel }, t.common.cancel),
      h("button", {
        class: "btn btn--danger-solid", type: "button",
        onclick: async () => {
          try {
            await onConfirm();
          } catch (err) {
            error.textContent = errorMessage(err);
          }
        },
      }, confirmLabel)));
  return bar;
}
