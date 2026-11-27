import { h } from "../dom.js";
import { avatar } from "./avatar.js";

// Who something is for (misiones-para-quien.html): one chip per child, with their face;
// a tap puts them in or takes them out. isOn(child); onToggle(child, on).
export function kidChips(children, { isOn, onToggle }) {
  return h("div", { class: "chips" }, children.map((child) => {
    const on = isOn(child);
    return h("button", {
      type: "button", class: `chip chip--kid${on ? " chip--on" : ""}`, "aria-pressed": String(on),
      onclick: () => onToggle(child, !on),
    }, avatar(child, { size: "sm" }), child.name);
  }));
}
