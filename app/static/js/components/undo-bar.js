// "Borrada «El aseo» · Deshacer" at the bottom of the screen for a few seconds
// (Material 3's snackbar, rutinas-7). onUndo: "Deshacer" was tapped; onTimeout: it
// went by (or the screen changed) without it. Returns { close } (neither is called).
import { h } from "../dom.js";
import { t } from "../texts.js";

const SHOW_MS = 8000;

export function undoBar({ message, onUndo, onTimeout }) {
  let open = true;
  const finish = (then) => {
    if (!open) return;
    open = false;
    clearTimeout(timer);
    window.removeEventListener("hashchange", leave);
    bar.remove();
    then?.();
  };
  const leave = () => finish(onTimeout);
  const bar = h("div", { class: "undo-bar", role: "status" },
    h("span", {}, message),
    h("button", { type: "button", class: "undo-bar__action", onclick: () => finish(onUndo) }, t.common.undo));
  const timer = setTimeout(leave, SHOW_MS);
  window.addEventListener("hashchange", leave);
  document.body.append(bar);
  return { close: () => finish(), flush: leave };
}
