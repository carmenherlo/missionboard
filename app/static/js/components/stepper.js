// − 5 min + : a number changed a step at a time (rutinas-7: a part's minutes and the
// routine's time, right on its card). Each tap shows at once; the change is sent
// once the taps stop (onChange(value)), so quick taps add up instead of getting lost.
import { h } from "../dom.js";

const SEND_AFTER_MS = 500;

export function stepper({ value, step = 1, min = -Infinity, max = Infinity, format = String, label, onChange }) {
  let current = value;
  let timer = null;
  const shown = h("b", { class: "stepper__value" }, format(current));
  const button = (sign, text) => h("button", {
    type: "button", class: "stepper__button", "aria-label": `${label} ${text}`,
    onclick: (e) => {
      e.stopPropagation();
      const next = Math.min(max, Math.max(min, current + sign * step));
      if (next === current) return;
      current = next;
      shown.textContent = format(current);
      clearTimeout(timer);
      timer = setTimeout(() => current !== value && onChange(current), SEND_AFTER_MS);
    },
  }, sign < 0 ? "−" : "+");
  return h("span", { class: "stepper", role: "group", "aria-label": label }, button(-1, "−"), shown, button(1, "+"));
}
