// The mailbox of the child's place (mi-sitio.html): the notices of their orders. One
// that has arrived opens with the truck bringing it home (the film of the shop), and
// from then on it is theirs; one that arrives today is new until they tap it; the rest
// say when they arrive. Every notice is said aloud. Letters from the parents, later.
import { api } from "../../api.js";
import { markRead, wasRead } from "../../components/news.js";
import { say } from "../../components/speech.js";
import { h } from "../../dom.js";
import { bringHome } from "../../effects/delivery.js";
import { t } from "../../texts.js";
import { placeSheet } from "./place-sheet.js";
import { picture } from "./ring.js";

const FLUENT = "static/libraries/fluent";

export async function openMailbox(container, childId, { colors, onClose }) {
  let view = await api("GET", `api/children/${childId}/shop`);
  const { body } = placeSheet(container, {
    title: t.mail.title, picture: `${FLUENT}/open-mailbox-with-raised-flag.svg`, colors, onClose,
  });

  const isNew = (order) => order.state === "arrived" || (order.nights === 0 && !wasRead(order.id));

  function draw() {
    const notices = view.orders.filter((o) => o.state !== "done");
    // The new ones first: what has arrived, then what arrives today.
    notices.sort((a, b) => Number(isNew(b)) - Number(isNew(a)) || Number(b.state === "arrived") - Number(a.state === "arrived"));
    body.replaceChildren(notices.length
      ? h("ul", { class: "mail" }, notices.map(notice))
      : h("p", { class: "mail__empty" }, h("img", { src: `${FLUENT}/closed-mailbox-with-lowered-flag.svg`, alt: "" }), t.mail.empty));
    if (!notices.length) say(t.mail.emptySay);
  }

  function notice(order) {
    const fresh = isNew(order);
    const text = order.state === "arrived" ? t.mail.arrived(order.item_text)
      : order.nights === 0 ? t.mail.today(order.item_text) : t.mail.onWay(order.item_text, order.nights);
    const sign = order.state === "arrived" ? "package" : order.nights === 0 ? "sun" : "delivery-truck";
    return h("li", {},
      h("button", { type: "button", class: `mail__notice${fresh ? " mail__notice--new" : ""}`, onclick: () => open(order) },
        h("span", { class: "step-tile" }, picture(order.image_url, order.item_text, "step-tile__letter")),
        h("img", { class: "mail__sign", src: `${FLUENT}/${sign}.svg`, alt: "" }),
        h("span", { class: "mail__text" }, text),
        fresh && h("span", { class: "mail__new" }, t.mail.isNew)));
  }

  async function open(order) {
    if (order.state === "arrived") return arrive(order);
    if (order.nights === 0) {
      markRead(order.id);
      say(t.shop.todaySay(order.item_text));
      return draw();
    }
    say(t.shop.whenSay(order.item_text, order.nights));
  }

  // Handed over by a parent: the truck brings it home, and it is theirs.
  async function arrive(order) {
    const stage = h("div", { class: "parcel-stage" });
    body.replaceChildren(stage);
    api("POST", `api/children/${childId}/orders/${order.id}/seen`).catch(() => {});
    say(t.shop.arrivedSay(order.item_text));
    await bringHome(stage, { itemUrl: order.image_url });
    view = await api("GET", `api/children/${childId}/shop`).catch(() => view);
    body.replaceChildren(
      h("h3", { class: "prize-body__title" }, t.shop.arrivedTitle),
      h("div", { class: "prize-won" },
        h("span", { class: "step-tile" }, picture(order.image_url, order.item_text, "step-tile__letter")), order.item_text),
      h("button", { type: "button", class: "btn btn--primary spin-button", onclick: draw }, t.shop.great));
  }

  draw();
}
