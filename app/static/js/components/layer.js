// A small window over the screen, with the page dimmed behind it (the same look as the
// one that opens a mission only today). Tapping outside closes it.
import { h } from "../dom.js";

export function layer(content, { onClose = () => {} } = {}) {
  const close = () => {
    element.remove();
    onClose();
  };
  const element = h("div", {
    class: "mission-layer open-today layer", role: "dialog", "aria-modal": "true",
    onclick: (e) => { if (e.target === e.currentTarget) close(); },
  }, content);
  document.body.append(element);
  return { close, element };
}
