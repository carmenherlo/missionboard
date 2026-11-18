// The parents' code over the routine, before something only they do: finish it for
// everyone, or pause it and let it go on (18/11). `send(code)` does it; if it fails,
// the code was wrong (or the routine is no longer on): it asks again.
import { codeField } from "../components/code-input.js";
import { h } from "../dom.js";
import { t } from "../texts.js";

export function askParentCode(r, { title, hint, submit, send }) {
  const { field, input } = codeField(t.routine.code);
  const error = h("p", { class: "form-error", role: "alert" });
  const close = () => r.showing?.view.finish.replaceChildren();
  const form = h("form", {
    class: "routine__code", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      try {
        await send(input.value);
        close();
      } catch {
        error.textContent = t.errors.badParentCode;
        input.value = "";
        input.focus();
      }
    },
  }, h("h2", {}, title), h("p", {}, hint), field, error,
    h("div", { class: "form-actions" },
      h("button", { type: "button", class: "btn", onclick: close }, t.common.cancel),
      h("button", { type: "submit", class: "btn btn--primary" }, submit)));
  r.showing.view.finish.replaceChildren(form);
  input.focus();
}
