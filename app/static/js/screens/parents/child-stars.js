// A child's card · Estrellas (ficha-nino.html): give or take some (− / + and the
// buttons; it goes to the log), the stars won and spent each day of the last two weeks,
// and their latest stars in and out in thin lines, with «Ver todos» for the rest.
import { api, errorMessage } from "../../api.js";
import { panel } from "../../components/panel.js";
import { stepper } from "../../components/stepper.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { dayMonth } from "./orders-panel.js";

const MAX_GIFT = 50; // as the server allows
const WEEKDAY = ["D", "L", "M", "X", "J", "V", "S"];

// − / +, Regalar and Quitar (never more than they have). onChange: the card again.
function giver(child, stars, onChange) {
  let amount = 1;
  const message = h("p", { class: "form-error", role: "alert" });
  const give = h("button", { type: "button", class: "btn btn--primary", onclick: () => send("gift") });
  const take = h("button", { type: "button", class: "btn", onclick: () => send("take") });
  const show = () => {
    give.textContent = t.childStars.give(amount);
    take.textContent = t.childStars.take(amount);
    take.disabled = amount > stars;
  };
  async function send(what) {
    give.disabled = take.disabled = true;
    try {
      await api("POST", `api/children/${child.id}/stars/${what}`, { json: { stars: amount } });
      onChange();
    } catch (err) {
      message.textContent = errorMessage(err);
      give.disabled = false;
      show();
    }
  }
  show();
  return h("div", { class: "child-stars__gift" },
    stepper({
      value: amount, min: 1, max: MAX_GIFT, label: t.childStars.howMany,
      // Each tap shows at once (the stepper only tells onChange once the taps stop).
      format: (n) => { amount = n; show(); return String(n); },
      onChange: () => {},
    }),
    give, take, message);
}

// A bar per day: won upwards, spent downwards. Their heights, --won and --spent (0 to 1),
// the only numbers passed to the styles.
function chart(days) {
  const top = Math.max(1, ...days.map((d) => Math.max(d.earned, d.spent)));
  const sum = (key) => days.reduce((n, d) => n + d[key], 0);
  return [
    h("div", { class: "star-chart", role: "img", "aria-label": t.childCard.chartLabel(sum("earned"), sum("spent")) },
      days.map((d) => h("div", { class: "star-chart__day", style: `--won: ${d.earned / top}; --spent: ${d.spent / top}` },
        h("span", { class: "star-chart__won" }),
        h("span", { class: "star-chart__spent" }),
        h("span", { class: "star-chart__label" }, WEEKDAY[new Date(`${d.day}T12:00:00`).getDay()])))),
    h("p", { class: "star-chart__legend" },
      h("span", { class: "star-chart__key star-chart__key--won" }), t.childCard.won(sum("earned")),
      h("span", { class: "star-chart__key star-chart__key--spent" }), t.childCard.spent(sum("spent"))),
  ];
}

// Their stars in and out, one thin line each: what, when, how many.
export function movementLines(movements) {
  if (!movements.length) return h("p", { class: "hint" }, t.overview.noHistory);
  return h("ul", { class: "thin-rows" }, movements.map((m) => h("li", { class: "thin-row" },
    h("span", { class: "thin-row__text" }, t.overview.movement(m)),
    h("span", { class: "thin-row__detail" }, dayMonth(m.day)),
    h("b", { class: `star-amount${m.amount < 0 ? " star-amount--out" : ""}` }, `${m.amount > 0 ? "+" : ""}${m.amount}`))));
}

export function starsBlock(view, here, onChange) {
  return panel(t.childStars.title,
    giver(view.child, view.stars, onChange),
    h("h3", { class: "card-block__sub" }, t.childCard.chartTitle),
    chart(view.chart),
    h("h3", { class: "card-block__sub" }, t.overview.historyTitle),
    movementLines(view.movements),
    view.movements.length > 0 && h("a", { class: "card-block__more", href: `${here}/stars` }, t.childCard.seeAll, icon("next")));
}
