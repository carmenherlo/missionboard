// The child's chest, open (vales-2.html): the whole screen is the inside of their chest, as the
// shop is a shop front, so they always know where they are. Their gift cards lie in it. Out of
// a momento de vales a card only shakes and says what it is; in one, they pick a card and it
// opens into light («¡A disfrutar!»): its prize is handed over, and it leaves the chest.
import { api } from "../../api.js";
import { avatarPicture } from "../../components/avatar.js";
import { giftCard, shiningCard } from "../../components/gift-card.js";
import { sounds } from "../../components/sound.js";
import { say } from "../../components/speech.js";
import { openCard, shake } from "../../effects/gift-card.js";
import { tokenMs } from "../../effects/motion.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

const FLUENT = "static/libraries/fluent";

export async function openChest(container, child, { onClose }) {
  let view = await api("GET", `api/children/${child.id}/vouchers`);
  const wood = h("div", { class: "chest-room__wood" });
  const notice = h("p", { class: "chest-room__notice", "aria-live": "polite" });
  const flag = h("span", { class: "chest-room__moment" },
    h("img", { src: `${FLUENT}/sparkles.svg`, alt: "" }), t.gift.momentOn);
  const close = () => {
    room.remove();
    onClose?.();
  };
  const room = h("div", { class: "chest-room", role: "dialog", "aria-modal": "true", "aria-label": t.gift.chestTitle(child.name) },
    h("header", { class: "chest-room__lid" },
      h("button", { type: "button", class: "btn btn--primary btn--big place-back", onclick: close },
        h("img", { class: "place-back__picture", src: `${FLUENT}/house.svg`, alt: "" }), t.gift.backHome),
      h("span", { class: "chest-room__animal" }, avatarPicture(child)),
      h("h2", { class: "chest-room__title" }, t.gift.chestTitle(child.name)),
      flag),
    wood, notice);
  container.append(room);

  let hideNotice;
  function tell(text) {
    notice.textContent = text;
    notice.classList.add("chest-room__notice--on");
    clearTimeout(hideNotice);
    hideNotice = setTimeout(() => notice.classList.remove("chest-room__notice--on"), tokenMs("--gift-notice", 4000));
  }

  function draw() {
    room.classList.toggle("chest-room--moment", Boolean(view.moment?.can_pick));
    flag.hidden = !view.moment;
    wood.replaceChildren(...(view.cards.length
      ? view.cards.map((card) => {
          const item = h("button", { type: "button", class: "chest-room__card", onclick: () => tap(card, item) },
            giftCard(card),
            card.source === "week" && h("span", { class: "chest-room__week" },
              h("img", { src: `${FLUENT}/rocket.svg`, alt: "" }), t.gift.week));
          return item;
        })
      : [h("p", { class: "chest-room__empty" }, t.gift.empty)]));
  }

  function tap(card, item) {
    if (!view.moment?.can_pick) {
      shake(item);
      sounds.nope();
      say(card.text);
      tell(view.moment ? t.gift.picked : t.gift.notYet);
      return;
    }
    ask(card);
  }

  // In a momento de vales: the card big, "¿Usamos…?", then it opens into light.
  function ask(card) {
    const enjoy = h("p", { class: "gift-open__enjoy" }, t.gift.enjoy);
    const answers = h("div", { class: "gift-open__answers" },
      h("button", { type: "button", class: "btn btn--primary btn--big", onclick: () => pick(card) }, t.gift.yes),
      h("button", { type: "button", class: "btn btn--big", onclick: () => layer.remove() }, t.gift.other));
    const layer = h("div", { class: "gift-open" },
      h("div", { class: "gift-open__card" }, shiningCard(card)),
      h("div", { class: "gift-open__light", "aria-hidden": "true" }), enjoy, answers);
    room.append(layer);
    say(t.gift.askSay(card.text));

    async function pick() {
      answers.remove();
      try {
        await api("POST", `api/children/${child.id}/vouchers/${card.id}/pick`);
      } catch {
        layer.remove(); // the moment ended meanwhile, or already picked: the chest as it is now
        view = await api("GET", `api/children/${child.id}/vouchers`);
        draw();
        return;
      }
      setTimeout(() => say(t.gift.enjoySay(card.text)), tokenMs("--gift-open", 5000) * 0.74);
      await openCard(layer);
      layer.remove();
      view = await api("GET", `api/children/${child.id}/vouchers`);
      draw();
    }
  }

  draw();
  if (!view.cards.length) say(t.gift.empty);
}
