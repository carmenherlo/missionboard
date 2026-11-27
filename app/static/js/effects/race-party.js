// The race's celebration (carrera-divertida.html, 26/11): «Podio y Luna».
// Won: the team on the top step of a podium, jumping, with confetti; they rise, the podium
// goes down and the Moon comes down behind them; the alien comes in angry, tries to land on
// the Moon, is kicked off by the team, stays dizzy («¡Mañana os pillo!») and flies off like a
// shooting star (27/11); then a traca of bangers around the Moon, a boom that shakes it all,
// and a finale of fireworks. Lost: the Moon is there already, and the alien jumps on it, laughing.
// Over the routine's screen, about 11 seconds (a tap ends it); then the result card stays
// under it. Pure decoration: with "reduce motion" it does nothing. The moves are in
// race-party-effects.css and their lengths in tokens-effects.css (--party-*).
import { avatar } from "../components/avatar.js";
import { h } from "../dom.js";
import { raceSounds } from "../routine/race-sounds.js";
import { reducedMotion, tokenMs } from "./motion.js";

const FLUENT = "static/libraries/fluent";
const COLORS = 6; // --confetti-1…6 (tokens-effects.css)
const SKY_STARS = 80;
const BANGERS = 40; // the traca, faster and faster
const SPARKS = 16; // each ring of a firework
const LOST_MS = 5000;
const ALIEN_STEPS = [["in", 900], ["kick", 800], ["dizzy", 1600], ["off", 1000]]; // and their tokens' fallbacks
const LAYERS = { far: { reach: [5, 8], loud: 0.4 }, middle: { reach: [11, 17], loud: 0.8 }, near: { reach: [20, 28], loud: 1.2 } };

const pick = (n) => Math.floor(Math.random() * n);
const colour = () => `var(--confetti-${1 + pick(COLORS)})`;
const place = (node, vars) => { for (const [key, value] of Object.entries(vars)) node.style.setProperty(`--${key}`, value); return node; };

// `container`: where it goes over (the routine's layer); `people`: the children who ran it.
// Resolves once it is over.
export function raceParty(container, { people, won, title, alienSays }) {
  if (reducedMotion()) return Promise.resolve();
  const timers = [];
  const later = (ms, action) => timers.push(setTimeout(action, ms));
  const every = (ms, action) => { const id = setInterval(action, ms); timers.push(id); return id; };

  const moon = h("div", { class: "party__moon" }, ...Array.from({ length: 5 }, () => h("span", { class: "party__crater" })));
  const team = h("div", { class: "party__team" }, people.map((p) => avatar(p.child, { size: "lg" })));
  const alien = h("div", { class: "party__alien" },
    h("div", { class: "party__alien-body" }, h("img", { src: `${FLUENT}/alien-monster.svg`, alt: "" }),
      h("span", { class: "party__dizzy" }, h("span"), h("span"), h("span"))),
    h("span", { class: "party__say" }, alienSays));
  const party = h("div", { class: `party${won ? "" : " party--lost"}`, "aria-hidden": "true" },
    ...stars(), moon, won ? h("div", { class: "party__podium" }, "1º") : "", team, alien, h("p", { class: "party__title" }, title));
  container.append(party);

  return new Promise((resolve) => {
    let over = false;
    const finish = () => {
      if (over) return;
      over = true;
      timers.forEach(clearTimeout);
      timers.forEach(clearInterval);
      party.classList.add("party--out");
      setTimeout(() => { party.remove(); resolve(); }, tokenMs("--party-out", 600));
    };
    party.addEventListener("pointerdown", finish);
    if (!won) {
      party.dataset.phase = "lost";
      later(800, () => raceSounds.giggle());
      later(LOST_MS, finish);
      return;
    }
    const podiumMs = tokenMs("--party-podium", 2000);
    const riseMs = tokenMs("--party-rise", 2600);
    party.dataset.phase = "podium";
    const confetti = every(70, () => fall(party));
    later(podiumMs, () => { clearInterval(confetti); party.dataset.phase = "rise"; });
    later(podiumMs + riseMs, () => {
      const thrown = throwOff(party, alien, later, every);
      later(thrown, () => moonParty(party, later, every, finish));
    });
  });
}

// The alien's moment (race-party-alien-effects.css): in, kicked off, dizzy, off. Returns how long it lasts.
function throwOff(party, alien, later, every) {
  const lengths = Object.fromEntries(ALIEN_STEPS.map(([step, fallback]) => [step, tokenMs(`--party-alien-${step}`, fallback)]));
  const at = { in: 0, kick: lengths.in, dizzy: lengths.in + lengths.kick, off: lengths.in + lengths.kick + lengths.dizzy };
  const step = (name) => { party.dataset.alien = name; };
  step("in");
  raceSounds.alien(true);
  later(at.kick, () => step("kick"));
  later(at.kick + lengths.kick * 0.45, () => { // it touches the Moon: the team jumps
    party.dataset.kick = "";
    raceSounds.pop(0.6);
    raceSounds.ouch();
    later(500, () => delete party.dataset.kick);
  });
  later(at.dizzy, () => step("dizzy"));
  later(at.off, () => {
    step("off");
    raceSounds.whoosh();
    const trail = every(40, () => party.append(place(h("span", { class: "party__trail" }), centre(party, alien))));
    later(lengths.off, () => {
      clearInterval(trail);
      party.append(place(h("span", { class: "party__twinkle" }), centre(party, alien)));
      step("gone");
      raceSounds.pop(0.4);
    });
  });
  return at.off + lengths.off;
}

// Where the middle of `node` is, in the party (for its trail and its twinkle).
function centre(party, node) {
  const box = party.getBoundingClientRect();
  const it = node.getBoundingClientRect();
  return { x: `${it.left + it.width / 2 - box.left}px`, y: `${it.top + it.height / 2 - box.top}px` };
}

// Then the Moon's party: the title, the traca, the boom and the fireworks; then it ends.
function moonParty(party, later, every, finish) {
  party.dataset.phase = "moon";
  later(traca(party, later), () => {
    raceSounds.boom();
    party.dataset.shake = "";
    later(700, () => delete party.dataset.shake);
    every(140, () => firework(party));
    every(1300, () => { for (let i = 0; i < 4; i += 1) firework(party); });
    later(tokenMs("--party-finale", 3500), finish);
  });
}

// A starry sky: small stars here and there, some twinkling.
function stars() {
  return Array.from({ length: SKY_STARS }, () => place(h("span", { class: `party__star${Math.random() < 0.3 ? " party__star--twinkle" : ""}` }),
    { x: `${Math.random() * 100}%`, y: `${Math.random() * 100}%`, s: `${1 + Math.random() * 2}px` }));
}

// 🧨 Bangers around the Moon, one after another, faster and faster: a flash and a puff of
// smoke each. Returns how long it lasts (the boom comes after).
function traca(party, later) {
  let at = 0;
  for (let i = 0; i < BANGERS; i += 1) {
    const angle = -Math.PI / 2 + (i / BANGERS) * Math.PI * 2; // from the top, clockwise
    later(at, () => {
      const flash = place(h("span", { class: "party__flash" }), { cx: Math.cos(angle).toFixed(3), cy: Math.sin(angle).toFixed(3) });
      party.append(flash);
      raceSounds.crack();
      setTimeout(() => flash.remove(), 1200);
    });
    at += 25 + 110 * (1 - i / BANGERS) ** 1.5;
  }
  return at + 150;
}

// A firework anywhere: far (behind the Moon), middle or near (over everything); one colour or many.
function firework(party) {
  const layer = ["far", "far", "middle", "middle", "middle", "near"][pick(6)];
  const { reach: [least, most], loud } = LAYERS[layer];
  const reach = least + Math.random() * (most - least);
  const many = Math.random() < 0.3;
  const one = colour();
  const spot = place(h("span", { class: `party__burst party__burst--${layer}` }), { x: `${8 + Math.random() * 84}%`, y: `${6 + Math.random() * 60}%` });
  for (const [distance, turn] of [[reach, 0], [reach * 0.55, 0.5]]) {
    for (let i = 0; i < SPARKS; i += 1) {
      const angle = ((i + turn) / SPARKS) * Math.PI * 2;
      spot.append(place(h("span", { class: "party__spark" }),
        { c: many ? colour() : one, tx: `${(Math.cos(angle) * distance).toFixed(1)}vmin`, ty: `${(Math.sin(angle) * distance).toFixed(1)}vmin` }));
    }
  }
  party.append(spot);
  raceSounds.pop(loud);
  setTimeout(() => spot.remove(), 1500);
}

// A piece of confetti falling from the top.
function fall(party) {
  const piece = place(h("span", { class: "party__confetti" }), { x: `${Math.random() * 100}%`, c: colour(), d: `${2.5 + Math.random() * 2}s` });
  party.append(piece);
  setTimeout(() => piece.remove(), 5000);
}
