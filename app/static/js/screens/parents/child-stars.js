// Editar niño → Estrellas: how many the child has, and stars given as a present
// (choose how many with − / + and "Regalar"). It goes to the log.
import { api, errorMessage } from "../../api.js";
import { panel } from "../../components/panel.js";
import { stepper } from "../../components/stepper.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

const STAR = "static/libraries/fluent/star.svg";
const MAX_GIFT = 50; // as the server allows

export async function childStarsPanel(child) {
  let { stars } = await api("GET", `api/children/${child.id}/stars`);
  let amount = 1;

  const count = h("b", { class: "child-stars__count" });
  const message = h("p", { class: "hint", role: "status" });
  const give = h("button", { type: "button", class: "btn btn--primary", onclick: gift });
  const show = () => {
    count.textContent = t.childStars.has(stars);
    give.textContent = t.childStars.give(amount);
  };

  async function gift() {
    give.disabled = true;
    try {
      ({ stars } = await api("POST", `api/children/${child.id}/stars/gift`, { json: { stars: amount } }));
      message.textContent = t.childStars.given(amount, child.name);
    } catch (err) {
      message.textContent = errorMessage(err);
    }
    give.disabled = false;
    show();
  }

  show();
  return panel(t.childStars.title,
    h("div", { class: "child-stars" },
      h("p", { class: "child-stars__now" }, h("img", { src: STAR, alt: "" }), count),
      h("div", { class: "child-stars__gift" },
        stepper({
          value: amount, min: 1, max: MAX_GIFT, label: t.childStars.howMany,
          // Each tap shows at once (the stepper only tells onChange once the taps stop).
          format: (n) => { amount = n; give.textContent = t.childStars.give(n); return String(n); },
          onChange: () => {},
        }),
        give),
      message));
}
