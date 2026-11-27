// Apariencia → Laboratorio de animaciones (laboratorio-animaciones.html, 27/11): to watch the
// animations without living them. Today the race's end: how it ends and how many children
// (1–8: the family's first, then made-up ones). Nothing is kept: no stars, no race counts.
import { api } from "../../api.js";
import { loadAvatars } from "../../components/avatar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { reducedMotion } from "../../effects/motion.js";
import { icon } from "../../icons.js";
import { celebrate, resultCard } from "../../routine/race-result.js";
import { raceMusic } from "../../routine/race-music.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const OUTCOMES = ["record", "won", "slow", "lost"];
const MOST_KIDS = 8;
const MADE_UP = ["Bea", "Alex", "Noa", "Leo", "Mía", "Teo", "Lola", "Hugo"];
const PLANNED_S = 15 * 60;
const TOOK_S = { record: 11 * 60 + 40, won: 13 * 60 + 5, slow: 16 * 60 + 20, lost: null };
const STARS = { record: 3, won: 2, slow: 0, lost: 0 };

// The family's first `count` children, and made-up ones after them (an animal and a colour each).
function people(family, catalog, count) {
  const madeUp = MADE_UP.filter((name) => !family.some((c) => c.name === name)).map((name, i) => ({
    id: `lab-${i}`, name, preset: catalog.presets[i % catalog.presets.length]?.id, color: catalog.palette[i % catalog.palette.length].color,
  }));
  return [...family, ...madeUp].slice(0, count).map((child) => ({ child, colors: { color: child.color } }));
}

const pretend = (outcome) => ({ outcome, stars: STARS[outcome], given: true, took_seconds: TOOK_S[outcome], planned_seconds: PLANNED_S });

// One row of choices, the chosen one marked (as the songs' volume).
function tabs(label, values, chosen, name, onSelect) {
  return h("div", { class: "field" }, h("span", { class: "field__label" }, label),
    h("div", { class: "tabs", role: "group", "aria-label": label }, values.map((value) => h("button", {
      type: "button", class: `tab${value === chosen ? " tab--on" : ""}`, "aria-pressed": String(value === chosen),
      onclick: () => value !== chosen && onSelect(value),
    }, name(value)))));
}

// The race's end over the whole screen: the party, and the result card under it; «Cerrar» always on top.
function play(result, data) {
  const close = h("button", { type: "button", class: "btn lab__close", onclick: () => stage.remove() }, icon("close"), t.lab.close);
  const card = h("div", { class: "race__result" }, ...resultCard(result, data),
    reducedMotion() ? h("p", { class: "hint" }, t.lab.reduced) : "");
  const stage = h("div", { class: "lab__stage", role: "dialog", "aria-modal": "true", "aria-label": t.lab.race }, card, close);
  document.body.append(stage);
  celebrate(stage, result, data, { music: raceMusic() });
}

export async function viewAnimationLab() {
  const [family, catalog] = await Promise.all([api("GET", "api/children"), loadAvatars()]);
  const chosen = { outcome: "record", kids: Math.min(Math.max(family.length, 1), MOST_KIDS) };
  const draw = () => render(
    parentsHeader(t.lab.title, { href: "#/parents/config/appearance", label: t.appearance.title }),
    h("main", { class: "page" },
      h("p", { class: "hint" }, t.lab.hint),
      panel(t.lab.race,
        tabs(t.lab.outcome, OUTCOMES, chosen.outcome, (o) => t.lab.outcomes[o], (o) => { chosen.outcome = o; draw(); }),
        tabs(t.lab.kids, Array.from({ length: MOST_KIDS }, (_, i) => i + 1), chosen.kids, String, (n) => { chosen.kids = n; draw(); }),
        h("p", { class: "hint" }, t.lab.kidsHint),
        h("button", { type: "button", class: "btn btn--primary", onclick: () =>
          play(pretend(chosen.outcome), { name: t.lab.mission, trial: true, people: people(family, catalog, chosen.kids) }) },
        icon("play"), t.lab.play))));
  draw();
}
