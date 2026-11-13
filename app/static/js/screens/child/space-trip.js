// The rocket's trip (13/11): after taking off from the workshop, it flies through space
// (the stars streak past) to a moon that grows as it comes, slows down, straightens
// and lands on it. The moon shakes, and out of it comes the prize: its picture in a
// bubble with rays of light, "¡Has ganado …!", the fanfare and confetti. Each week's
// moon has its own colour (from the week's date). The moves are in effects.css and
// their lengths in tokens.css (--trip-*); here only the scene, the sounds and the waits.
import { say } from "../../components/speech.js";
import { sounds } from "../../components/sound.js";
import { h } from "../../dom.js";
import { confetti } from "../../effects/confetti.js";
import { reducedMotion, tokenMs } from "../../effects/motion.js";
import { t } from "../../texts.js";

const FLUENT = "static/libraries/fluent";
const MOONS = 6; // colours, in tokens.css (--trip-moon-1…6)
const wait = (ms) => new Promise((done) => setTimeout(done, ms));

// The same stars every time.
let seed = 11;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const STARS = Array.from({ length: 90 }, () => [rand() * 100, rand() * 100, 0.6 + rand() * 1.6]);
const STREAKS = Array.from({ length: 34 }, () => [rand() * 140 - 20, rand() * 140 - 20, 6 + rand() * 14]);

// result: the week's result ({ end, prize_text, prize_image_url }). Ends when they tap "¡Bien!".
export function spaceTrip(host, result) {
  const moon = 1 + ([...result.end].reduce((sum, c) => sum + c.charCodeAt(0), 0) % MOONS);
  const picture = h("img", {
    class: "trip__prize-picture", alt: "",
    src: result.prize_image_url || `${FLUENT}/wrapped-gift.svg`,
    onerror: (e) => { e.target.src = `${FLUENT}/wrapped-gift.svg`; }, // a photo removed since
  });
  const done = h("button", { type: "button", class: "btn btn--primary btn--big trip__done" }, t.week.great);
  const trip = h("div", { class: "trip", role: "dialog", "aria-label": t.week.wonTitle(result.prize_text) },
    sky(),
    h("div", { class: `trip__moon trip__moon--${moon}` },
      h("span", { class: "trip__crater trip__crater--1" }),
      h("span", { class: "trip__crater trip__crater--2" }),
      h("span", { class: "trip__crater trip__crater--3" })),
    h("div", { class: "trip__rocket" }, rocket(), h("span", { class: "trip__dust" })),
    h("div", { class: "trip__prize" },
      h("span", { class: "trip__rays", "aria-hidden": "true" }),
      h("span", { class: "trip__bubble" }, picture)),
    h("div", { class: "trip__won" },
      h("p", { class: "trip__title" }, t.week.wonTitle(result.prize_text)),
      h("p", { class: "trip__hint" }, t.week.wonHint),
      done));
  host.append(trip);
  const finished = new Promise((close) => done.addEventListener("click", () => { trip.remove(); close(); }));

  if (reducedMotion()) {
    trip.classList.add("trip--landed", "trip--prize");
    say(t.week.wonSay(result.prize_text));
    return finished;
  }
  (async () => {
    trip.classList.add("trip--flying");
    sounds.whoosh();
    await wait(tokenMs("--trip-flight", 3800));
    trip.classList.replace("trip--flying", "trip--landed");
    sounds.thud();
    await wait(tokenMs("--trip-land", 900));
    trip.classList.add("trip--shake");
    sounds.boing();
    await wait(tokenMs("--trip-shake", 900));
    trip.classList.remove("trip--shake");
    trip.classList.add("trip--prize");
    sounds.pop();
    sounds.win();
    confetti(trip);
    say(t.week.wonSay(result.prize_text));
  })();
  return finished;
}

function svg(markup, className) {
  const box = h("span", { class: className, "aria-hidden": "true" });
  box.innerHTML = markup;
  return box;
}

// The night with its stars, and the streaks that rush past while flying.
function sky() {
  const stars = STARS.map(([x, y, r]) => `<circle class="garage__star" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r / 6).toFixed(2)}"/>`).join("");
  const streaks = STREAKS.map(([x, y, l]) =>
    `<line x1="${x.toFixed(1)}" y1="${y.toFixed(1)}" x2="${(x - l * 0.7).toFixed(1)}" y2="${(y + l * 0.7).toFixed(1)}"/>`).join("");
  return h("div", { class: "trip__sky" },
    svg(`<svg viewBox="0 0 100 100" preserveAspectRatio="none">${stars}</svg>`, "trip__stars"),
    svg(`<svg viewBox="0 0 100 100" preserveAspectRatio="none">${streaks}</svg>`, "trip__streaks"));
}

// The workshop's rocket (garage-scene.js), alone, with its flame.
function rocket() {
  return svg(`<svg viewBox="0 0 260 640" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="trip-body" x1="0" y1="0" x2="1" y2="0"><stop offset="0" class="garage__body-shade"/>
      <stop offset=".45" class="garage__body-light"/><stop offset="1" class="garage__body-shade"/></linearGradient></defs>
    <path class="trip__flame" d="M90 540 Q130 660 170 540Z"/>
    <polygon class="garage__fin" points="66,400 0,540 66,520"/><polygon class="garage__fin" points="194,400 260,540 194,520"/>
    <path d="M130 0 C 250 160, 212 430, 196 530 H64 C 48 430, 10 160, 130 0Z" fill="url(#trip-body)"/>
    <path class="garage__fin" d="M130 0 C 182 62, 202 110, 209 140 H51 C 58 110, 78 62, 130 0Z"/>
    <circle class="garage__window" cx="130" cy="225" r="40"/>
    <circle class="garage__light garage__light--on" cx="130" cy="330" r="13"/>
    <circle class="garage__light garage__light--on" cx="130" cy="380" r="13"/>
    <circle class="garage__light garage__light--on" cx="130" cy="430" r="13"/>
  </svg>`, "trip__ship");
}
