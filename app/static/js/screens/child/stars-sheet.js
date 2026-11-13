// Mis estrellas: the shop and the child's orders, in a panel over their route
// (tienda-2.html, concept A). Buying is ordering: the stars fly to it, it goes into
// a box and a truck takes it. "Mis pedidos" shows each order on the road from the
// shop to home, and how many nights are left; when a parent hands it over, the
// truck brings it home. Everything is drawn and said: no need to read.
import { api } from "../../api.js";
import { avatar } from "../../components/avatar.js";
import { say } from "../../components/speech.js";
import { h } from "../../dom.js";
import { bringHome, sendOff } from "../../effects/delivery.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { picture } from "./ring.js";

const FLUENT = "static/libraries/fluent";
const DRAWN_PRICE = 10; // up to this many stars, the price is drawn star by star
const DRAWN_PURSE = 20; // and their stars, to see which go

const img = (src, className) => h("img", { class: className, src, alt: "" });

// tab: "shop" or "orders". The news of their orders is in their mailbox (mailbox.js).
export async function openStars(container, childId, { onClose, tab = "shop" }) {
  const base = `api/children/${childId}/shop`;
  let view = await api("GET", base);
  let showing = tab;
  const head = h("div", { class: "shop-head" });
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
        head,
        h("span", { class: "child-bar__spacer" }),
        h("button", { type: "button", class: "icon-button mission-sheet__close", "aria-label": t.child.close, onclick: close },
          icon("close"))),
      body));

  const waiting = () => view.orders.filter((o) => o.state !== "done").length;

  // Their stars, and the two tabs with their pictures.
  function drawHead(tabs = true) {
    const tabButton = (name, src, text) => h("button", {
      type: "button", class: `shop-tab${showing === name ? " shop-tab--on" : ""}`,
      "aria-pressed": String(showing === name),
      onclick: () => (name === "shop" ? showShop() : showOrders()),
    }, img(src, "shop-tab__picture"), text);
    head.replaceChildren(...[
      h("span", { class: "stars" }, img(view.star_url), String(view.stars)),
      tabs && h("span", { class: "shop-tabs" },
        tabButton("shop", `${FLUENT}/shopping-cart.svg`, t.shop.tabShop),
        tabButton("orders", `${FLUENT}/delivery-truck.svg`, t.shop.tabOrders(waiting()))),
    ].filter(Boolean));
  }

  function price(n) {
    return n <= DRAWN_PRICE
      ? h("span", { class: "price price--drawn", "aria-label": String(n) },
          Array.from({ length: n }, () => img(view.star_url)))
      : h("span", { class: "price" }, img(view.star_url), String(n));
  }

  function showShop() {
    showing = "shop";
    drawHead();
    body.replaceChildren(...[
      view.items.length > 0 && h("div", { class: "step-grid" }, view.items.map((item) =>
        h("div", { class: `step-card${item.affordable ? "" : " step-card--locked"}` },
          h("button", {
            type: "button", class: "step-card__toggle",
            onclick: () => {
              if (item.affordable) return showConfirm(item);
              say(t.shop.missingSay(item.text, item.price - view.stars));
            },
          },
            h("span", { class: "step-tile" }, picture(item.image_url, item.text, "step-tile__letter")),
            h("span", { class: "step-card__text" }, item.text),
            price(item.price),
            !item.affordable && h("span", { class: "hint" }, t.shop.missing(item.price - view.stars)))))),
    ].filter(Boolean));
  }

  // Their stars in a row: those it costs, ringed; those they keep, faded.
  function purse(cost) {
    const left = view.stars - cost;
    if (view.stars > DRAWN_PURSE) {
      return h("p", { class: "shop-purse" }, price(cost), h("span", { class: "hint" }, t.shop.leftAfter(left)));
    }
    return h("p", { class: "shop-purse" },
      h("span", { class: "shop-purse__stars" },
        Array.from({ length: view.stars }, (_, i) => img(view.star_url, i < cost ? "shop-purse__goes" : "shop-purse__stays"))),
      h("span", { class: "hint" }, t.shop.leftAfter(left)));
  }

  function showConfirm(item) {
    drawHead(false);
    say(t.shop.orderSay(item.text, item.price, view.stars - item.price));
    const order = h("button", {
      type: "button", class: "btn btn--primary spin-button shop-order",
      onclick: async () => {
        order.disabled = true;
        try {
          view = await api("POST", `${base}/${item.id}/buy`);
        } catch {
          view = await api("GET", base);
          return showShop();
        }
        await sendIt(item);
      },
    }, img(`${FLUENT}/shopping-cart.svg`, "shop-order__picture"), t.shop.order);
    body.replaceChildren(
      h("h3", { class: "prize-body__title" }, t.shop.orderQuestion(item.text)),
      h("div", { class: "shop-confirm" },
        h("span", { class: "step-tile shop-confirm__tile" }, picture(item.image_url, item.text, "step-tile__letter")),
        purse(item.price)),
      order);
  }

  async function sendIt(item) {
    drawHead(false);
    const stage = h("div", { class: "parcel-stage" });
    body.replaceChildren(h("h3", { class: "prize-body__title" }, t.shop.ordered), stage);
    say(t.shop.orderedSay(item.text));
    await sendOff(stage, { itemUrl: item.image_url, starUrl: view.star_url, price: item.price });
    showOrders(view.order_id);
  }

  // Each order on the road from the shop to home, and when it arrives.
  function showOrders(fresh = null) {
    showing = "orders";
    drawHead();
    const open = view.orders.filter((o) => o.state !== "done");
    const done = view.orders.filter((o) => o.state === "done");
    body.replaceChildren(...[
      !view.orders.length && h("p", { class: "hint" }, t.shop.noOrders),
      open.length > 0 && h("ul", { class: "orders" }, open.map((o) => orderRow(o, o.id === fresh))),
      done.length > 0 && h("div", { class: "orders orders--done" },
        h("h3", {}, t.shop.youHaveThem),
        h("ul", { class: "orders__things" }, done.map((o) => h("li", { class: "orders__thing" },
          h("span", { class: "step-tile" }, picture(o.image_url, o.item_text, "step-tile__letter")),
          h("span", { class: "orders__check", "aria-hidden": "true" }, icon("check")))))),
    ].filter(Boolean));
  }

  function orderRow(order, fresh) {
    if (order.state === "arrived") {
      return h("li", { class: "delivery delivery--arrived" },
        h("span", { class: "step-tile" }, picture(order.image_url, order.item_text, "step-tile__letter")),
        h("button", { type: "button", class: "btn btn--primary spin-button delivery__open", onclick: () => arrive_(order) },
          img(`${FLUENT}/package.svg`, "shop-order__picture"), t.shop.openIt));
    }
    const when = order.nights === null
      ? [img(`${FLUENT}/hourglass-not-done.svg`), t.shop.soon]
      : order.nights === 0
        ? [img(`${FLUENT}/sun.svg`), t.shop.today]
        : [h("span", { class: "delivery__moons" }, Array.from({ length: Math.min(order.nights, 7) },
            () => img(`${FLUENT}/crescent-moon.svg`))), t.shop.nights(order.nights)];
    return h("li", {},
      h("button", {
        type: "button", class: `delivery${fresh ? " delivery--fresh" : ""}`,
        onclick: () => say(t.shop.whenSay(order.item_text, order.nights)),
      },
        h("span", { class: "step-tile" }, picture(order.image_url, order.item_text, "step-tile__letter")),
        h("span", { class: "delivery__road" },
          img(`${FLUENT}/convenience-store.svg`, "delivery__from"),
          // Where the truck is: the only number passed to the styles, as a custom property.
          h("span", { class: "delivery__truck", style: `--progress: ${order.progress}` },
            img(`${FLUENT}/delivery-truck.svg`)),
          img(`${FLUENT}/house-with-garden.svg`, "delivery__to")),
        h("span", { class: "delivery__when" }, ...when)));
  }

  // Handed over by a parent: the truck brings it home, and it is theirs.
  async function arrive_(order) {
    drawHead(false);
    const stage = h("div", { class: "parcel-stage" });
    body.replaceChildren(stage);
    api("POST", `api/children/${childId}/orders/${order.id}/seen`).catch(() => {});
    say(t.shop.arrivedSay(order.item_text));
    await bringHome(stage, { itemUrl: order.image_url });
    view = await api("GET", base).catch(() => view);
    body.replaceChildren(
      h("h3", { class: "prize-body__title" }, t.shop.arrivedTitle),
      h("div", { class: "prize-won" },
        h("span", { class: "step-tile" }, picture(order.image_url, order.item_text, "step-tile__letter")), order.item_text),
      h("button", { type: "button", class: "btn btn--primary spin-button", onclick: () => showOrders() }, t.shop.great));
  }

  container.append(layer);
  if (showing === "orders") showOrders();
  else showShop();
}
