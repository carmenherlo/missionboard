// The gift cards' moments (vales-2.html), on top of the screen they happen in:
// winning one (it grows and shines, then drops into the child's chest) and opening one
// in a momento de vales (it lights up, turns and opens into light: «¡A disfrutar!").
// The timeline is in gift-effects.css; here, the sounds at their moment and the end.
import { chestLayers } from "../components/chest.js";
import { shiningCard } from "../components/gift-card.js";
import { sounds } from "../components/sound.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { confetti } from "./confetti.js";
import { reducedMotion, tokenMs } from "./motion.js";

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Resolves once the card is in the chest (and the stage gone).
export async function winCard(container, card, child) {
  const [inside, front] = chestLayers(child);
  const stage = h("div", { class: "gift-win" },
    h("h2", { class: "gift-win__title" }, t.gift.title),
    h("div", { class: "gift-win__chest" }, inside),
    h("div", { class: "gift-win__card" }, shiningCard(card)),
    h("div", { class: "gift-win__chest" }, front));
  container.append(stage);
  if (reducedMotion()) {
    await wait(tokenMs("--gift-still", 3000));
  } else {
    const total = tokenMs("--gift-win", 6600);
    stage.classList.add("gift-win--go");
    setTimeout(() => sounds.shimmer(), total * 0.08);
    setTimeout(() => sounds.lid(), total * 0.81);
    await wait(total + 200);
  }
  stage.remove();
}

// The card asked about (a layer with it big): it opens into light. Resolves at the end.
export async function openCard(layer) {
  if (reducedMotion()) {
    layer.classList.add("gift-open--still");
    sounds.enjoy();
    await wait(tokenMs("--gift-still", 3000));
    return;
  }
  const total = tokenMs("--gift-open", 5000);
  layer.classList.add("gift-open--go");
  sounds.shimmer();
  setTimeout(() => {
    sounds.enjoy();
    confetti(layer);
  }, total * 0.72);
  await wait(total);
}

// Not now: the card shakes its head.
export function shake(element) {
  element.classList.remove("gift-card--shake");
  void element.offsetWidth; // so the same shake starts again
  element.classList.add("gift-card--shake");
}
