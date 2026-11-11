// 07 : 30 — a time of day, always in 24 hours (11/11: the browser's own time field
// follows the device's language and shows AM/PM in English). Two lists, hour and minutes.
// It behaves like an <input type="time">: .value is "HH:MM" ("" when empty, if it may be
// empty) and it fires "change" on itself, so e.target.value works as before.
import { h } from "../dom.js";

const pad = (n) => String(n).padStart(2, "0");

export function timeInput({ value = "", required = false, label = "", class: extra = "", onchange } = {}) {
  const options = (count, chosen) => [
    !required && h("option", { value: "", selected: chosen === "" }, "--"),
    ...Array.from({ length: count }, (_, i) => h("option", { value: pad(i), selected: pad(i) === chosen }, pad(i))),
  ];
  const [hour, minute] = value ? value.split(":") : ["", ""];
  const hours = h("select", { class: "time-input__part", "aria-label": `${label} · hora` }, options(24, hour));
  const minutes = h("select", { class: "time-input__part", "aria-label": `${label} · minutos` }, options(60, minute));
  const box = h("span", { class: `time-input ${extra}`.trim(), role: "group", "aria-label": label },
    hours, h("span", { class: "time-input__colon", "aria-hidden": "true" }, ":"), minutes);

  Object.defineProperty(box, "value", {
    get: () => (hours.value && minutes.value ? `${hours.value}:${minutes.value}` : ""),
    set: (time) => {
      const [hh, mm] = time ? time.split(":") : ["", ""];
      hours.value = hh;
      minutes.value = mm;
    },
  });

  for (const select of [hours, minutes]) {
    select.addEventListener("change", (e) => {
      e.stopPropagation();
      // A time with only its hour chosen is that hour sharp; with no hour, empty.
      if (select === hours && hours.value && !minutes.value) minutes.value = "00";
      if (select === hours && !hours.value) minutes.value = "";
      if (select === minutes && minutes.value && !hours.value) return;
      box.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }
  if (onchange) box.addEventListener("change", onchange);
  return box;
}
