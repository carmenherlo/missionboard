import { h } from "../dom.js";
import { icon } from "../icons.js";
import { t } from "../texts.js";

// Top-left corner of the home screen: the app in full screen, or back. The app
// is one page, so it stays in full screen on every screen until tapped again.
// Not shown where the browser cannot do it (an iPhone, some embedded views).
export function fullscreenButton() {
  if (!document.fullscreenEnabled) return null;
  const button = h("button", {
    type: "button", class: "icon-button icon-button--ghost fullscreen-button",
    onclick: () => (document.fullscreenElement
      ? document.exitFullscreen()
      : document.documentElement.requestFullscreen()).catch(() => {}),
  });
  const show = () => {
    const on = Boolean(document.fullscreenElement);
    const label = on ? t.home.exitFullscreen : t.home.fullscreen;
    button.setAttribute("aria-label", label);
    button.title = label;
    button.replaceChildren(icon(on ? "fullscreenExit" : "fullscreen"));
  };
  show();
  document.addEventListener("fullscreenchange", show);
  return button;
}
