// Configurar → Pantalla (reloj.html): this tablet's rest mode and the screen the app
// opens with. Kept on the device (display.js), so it saves on the spot, here only.
import { panel } from "../../components/panel.js";
import { display, setDisplay } from "../../display.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const REST_CHOICES = [2, 5, 10, 30];

export function viewDisplaySettings() {
  const restBox = h("div", { class: "stack stack--tight" });
  const openBox = h("div", {});

  function draw() {
    const now = display();
    restBox.replaceChildren(...[
      h("label", { class: "toggle" },
        h("input", { type: "checkbox", checked: now.rest, onchange: (e) => { setDisplay({ rest: e.target.checked }); draw(); } }),
        t.display.rest),
      now.rest && h("div", { class: "times" }, h("label", { class: "time" }, t.display.after,
        h("select", { onchange: (e) => setDisplay({ restMinutes: Number(e.target.value) }) },
          [...new Set([...REST_CHOICES, now.restMinutes])].sort((a, b) => a - b).map((n) =>
            h("option", { value: n, selected: n === now.restMinutes }, t.routine.minutes(n)))))),
      h("p", { class: "hint" }, t.display.restHint),
    ].filter(Boolean));
    openBox.replaceChildren(h("div", { class: "tabs" },
      [["last", t.display.openLast], ["kids", t.clock.toKids], ["clock", t.clock.toClock]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${now.open === value ? " tab--on" : ""}`, "aria-pressed": String(now.open === value),
          onclick: () => { setDisplay({ open: value }); draw(); },
        }, now.open === value && icon("check"), label))));
  }
  draw();

  render(
    parentsHeader(t.display.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("p", { class: "hint" }, t.display.hint),
      h("div", { class: "columns columns--equal" },
        panel(t.display.restTitle, restBox),
        panel(t.display.openTitle, openBox))));
}
