import { h } from "../dom.js";
import { t } from "../texts.js";
import { avatar } from "./avatar.js";

// The children's colours in six columns (rainbow order; under each basic
// colour, the extra that looks like it). The chosen one has a ring, the
// suggested one says so, and a sibling's colour carries their avatar.
export function colorPicker({ palette, columns, chosen, suggested, siblings, onChoose }) {
  const byId = new Map(palette.map((entry) => [entry.id, entry]));
  const ownersOf = (color) => siblings.filter((child) => child.color === color);

  const dot = ({ color, label }) => {
    const owners = ownersOf(color);
    const name = owners.length ? t.childForm.colorOf(label, owners.map((c) => c.name)) : label;
    return h("button", {
      type: "button",
      class: `color-picker__dot${color === chosen ? " color-picker__dot--chosen" : ""}`,
      style: `--child-color: ${color}`,
      "aria-pressed": String(color === chosen),
      "aria-label": name,
      title: name,
      onclick: () => onChoose(color),
    },
      owners.length > 0 && h("span", { class: "color-picker__owner" }, avatar(owners[0], { size: "xs" })),
      color === suggested && h("span", { class: "color-picker__suggested" }, t.childForm.suggested));
  };

  return h("div", { class: "color-picker" },
    columns.map((column) => h("div", { class: "color-picker__column" }, column.map((id) => dot(byId.get(id))))));
}

// The first colour, in suggestion order, that no sibling has (the first one if all are taken).
export function suggestedColor(palette, siblings) {
  const used = new Set(siblings.map((child) => child.color));
  return (palette.find((entry) => !used.has(entry.color)) ?? palette[0]).color;
}
