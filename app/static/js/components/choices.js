import { h } from "../dom.js";

// Two ways of doing something, each with its own choices (rutina-modos.html): folder tabs on
// top, and the chosen one's box below them. items: [{ label, on, onSelect }].
export function folderTabs(items, ...box) {
  return h("div", { class: "folder" },
    h("div", { class: "folder__tabs", role: "group" }, items.map(({ label, on, onSelect }) =>
      h("button", {
        type: "button", class: `folder__tab${on ? " folder__tab--on" : ""}`, "aria-pressed": String(on),
        onclick: () => !on && onSelect(),
      }, label))),
    h("div", { class: "folder__box" }, ...box));
}

// Choices that need a line each to be understood: a radio and its words.
// items: [{ label, hint, on, onSelect }].
export function choiceList(items) {
  return h("div", { class: "option-list", role: "radiogroup" }, items.map(({ label, hint, on, onSelect }) =>
    h("button", {
      type: "button", role: "radio", "aria-checked": String(on), class: `option${on ? " option--on" : ""}`,
      onclick: () => !on && onSelect(),
    },
    h("span", { class: "option__dot" }),
    h("span", { class: "option__text" }, h("b", {}, label), hint && h("span", { class: "hint" }, hint)))));
}
