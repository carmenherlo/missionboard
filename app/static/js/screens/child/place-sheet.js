// A building of the child's place, open over it (mi-sitio.html): the same panel as a
// mission or the shop, with the building's picture, its name and ✕.
import { icon } from "../../icons.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

// Returns { body, close }: the screen fills the body; close() takes it away and calls onClose.
export function placeSheet(container, { title, picture, colors, onClose }) {
  const { color, soft, strong, on } = colors;
  const body = h("div", { class: "stars-body" });
  const close = () => {
    layer.remove();
    onClose?.();
  };
  const layer = h("div", {
    class: "mission-layer",
    style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`,
    onclick: (e) => { if (e.target === e.currentTarget) close(); },
  },
    h("section", { class: "mission-sheet", role: "dialog", "aria-modal": "true", "aria-label": title },
      h("header", { class: "mission-sheet__bar" },
        h("img", { class: "place-sheet__picture", src: picture, alt: "" }),
        h("h2", { class: "mission-sheet__title" }, title),
        h("span", { class: "child-bar__spacer" }),
        h("button", { type: "button", class: "icon-button mission-sheet__close", "aria-label": t.child.close, onclick: close },
          icon("close"))),
      body));
  container.append(layer);
  return { body, close };
}
