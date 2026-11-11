// Configurar → Pantalla (reloj.html; "Configuración avanzada" until ajustes.html): this tablet's rest mode, the
// screen the app opens with, and the clock light or dark. Kept on the device (display.js), so it saves on the spot, here only.
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
  const clockBox = h("div", { class: "stack stack--tight" });
  const tabs = (current, choices, onPick) => h("div", { class: "tabs" }, choices.map(([value, label]) =>
    h("button", {
      type: "button", class: `tab${current === value ? " tab--on" : ""}`, "aria-pressed": String(current === value),
      onclick: () => { onPick(value); draw(); },
    }, current === value && icon("check"), label)));

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
    openBox.replaceChildren(tabs(now.open, [["last", t.display.openLast], ["kids", t.clock.toKids], ["clock", t.clock.toClock]],
      (value) => setDisplay({ open: value })));
    clockBox.replaceChildren(tabs(now.clockTheme, [["light", t.display.light], ["dark", t.display.dark]],
      (value) => setDisplay({ clockTheme: value })), h("p", { class: "hint" }, t.display.clockHint));
  }
  draw();

  render(
    parentsHeader(t.display.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("p", { class: "hint" }, t.display.hint),
      h("div", { class: "columns columns--equal" },
        h("div", { class: "stack" }, panel(t.display.restTitle, restBox), panel(t.display.clockTitle, clockBox)),
        panel(t.display.openTitle, openBox))));
}
