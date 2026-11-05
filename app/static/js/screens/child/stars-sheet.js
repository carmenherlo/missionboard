// Mis estrellas: the child's stars and the shop, in a panel over their route.
// An item they can afford: tap, confirm, and it is bought ("Díselo a papá o a
// mamá"); one they cannot: faded, with how many stars they still need.
import { api } from "../../api.js";
import { avatar } from "../../components/avatar.js";
import { h } from "../../dom.js";
import { confetti } from "../../effects/confetti.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { picture } from "./ring.js";

export async function openStars(container, childId, { onClose }) {
  const base = `api/children/${childId}/shop`;
  let view = await api("GET", base);
  const body = h("div", { class: "stars-body" });
  const close = () => {
    layer.remove();
    onClose(view);
  };
  const { color, soft, strong, on } = view.colors;
  const layer = h("div", {
    class: "mission-layer",
    style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`,
    onclick: (e) => { if (e.target === e.currentTarget) close(); },
  },
    h("section", { class: "mission-sheet", role: "dialog", "aria-modal": "true", "aria-label": t.shop.myStars },
      h("header", { class: "mission-sheet__bar" },
        avatar(view.child, { size: "md" }),
        h("h2", { class: "mission-sheet__title" }, t.shop.myStars),
        h("span", { class: "child-bar__spacer" }),
        h("button", { type: "button", class: "icon-button mission-sheet__close", "aria-label": t.child.close, onclick: close },
          icon("close"))),
      body));

  function showShop() {
    body.replaceChildren(...[
      h("p", { class: "stars stars--big" }, h("img", { src: view.star_url, alt: "" }), t.shop.youHave(view.stars)),
      view.items.length > 0 && h("div", { class: "step-grid" }, view.items.map((item) =>
        h("div", { class: `step-card${item.affordable ? "" : " step-card--locked"}` },
          h("button", {
            type: "button", class: "step-card__toggle", disabled: !item.affordable,
            onclick: () => showConfirm(item),
          },
            h("span", { class: "step-tile" }, picture(item.image_url, item.text, "step-tile__letter")),
            h("span", { class: "step-card__text" }, item.text),
            h("span", { class: "price" }, h("img", { src: view.star_url, alt: "" }), String(item.price)),
            !item.affordable && h("span", { class: "hint" }, t.shop.missing(item.price - view.stars)))))),
      view.purchases.length > 0 && h("div", { class: "purchases" },
        h("h3", {}, t.shop.yourPurchases),
        h("ul", { class: "rows" }, view.purchases.map((p) => h("li", { class: "row row--compact" },
          h("span", { class: "row__text" }, p.item_text),
          h("span", { class: "pill pill--muted" }, p.delivered_at ? t.shop.delivered : t.shop.toDeliver))))),
    ].filter(Boolean));
  }

  function showConfirm(item) {
    body.replaceChildren(
      h("h3", { class: "prize-body__title" }, t.shop.buyQuestion(item.text, item.price)),
      h("div", { class: "prize-won" },
        h("span", { class: "step-tile" }, picture(item.image_url, item.text, "step-tile__letter")), item.text),
      h("div", { class: "form-actions form-actions--center" },
        h("button", { type: "button", class: "btn spin-button", onclick: showShop }, t.shop.no),
        h("button", {
          type: "button", class: "btn btn--primary spin-button",
          onclick: async (e) => {
            e.target.disabled = true;
            try {
              view = await api("POST", `${base}/${item.id}/buy`);
              showBought(item);
            } catch {
              view = await api("GET", base);
              showShop();
            }
          },
        }, t.shop.yesBuy)));
  }

  function showBought(item) {
    body.replaceChildren(
      h("h3", { class: "prize-body__title" }, t.shop.bought),
      h("div", { class: "prize-won" },
        h("span", { class: "step-tile" }, picture(item.image_url, item.text, "step-tile__letter")), item.text),
      h("p", { class: "prize-body__hint" }, t.child.tellAdult),
      h("button", { type: "button", class: "btn btn--primary spin-button", onclick: showShop }, t.shop.back));
    confetti(layer);
  }

  showShop();
  container.append(layer);
}
