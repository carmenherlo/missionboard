// A building of the child's place, open over it (mi-sitio.html): the whole screen, as the
// rocket's workshop (16/11), with "Mi sitio" to go back, then the building's picture and
// name (or what `top` brings, as the shop's stars and tabs). The place shows blurred behind.
import { h } from "../../dom.js";
import { t } from "../../texts.js";

const FLUENT = "static/libraries/fluent";

// Returns { body, close }: the screen fills the body; close() takes it away and calls onClose.
export function placeSheet(container, { title, picture, top, colors, onClose }) {
  const { color, soft, strong, on } = colors;
  const body = h("div", { class: "stars-body" });
  const close = () => {
    layer.remove();
    onClose?.();
  };
  const layer = h("div", {
    class: "mission-layer place-layer",
    style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`,
  },
    h("section", { class: "mission-sheet place-layer__sheet", role: "dialog", "aria-modal": "true", "aria-label": title },
      h("header", { class: "mission-sheet__bar" },
        h("button", { type: "button", class: "btn btn--primary btn--big place-back", onclick: close },
          h("img", { class: "place-back__picture", src: `${FLUENT}/rocket.svg`, alt: "" }), t.place.backHere),
        ...(top ?? [
          h("img", { class: "place-sheet__picture", src: picture, alt: "" }),
          h("h2", { class: "mission-sheet__title" }, title),
        ])),
      body));
  container.append(layer);
  return { body, close };
}
