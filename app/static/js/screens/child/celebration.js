// "¡Misión cumplida!": the child's avatar in their full ring, the star won
// and how many they have now. Closes by itself or with a tap. The confetti
// and the glow are effects (effects/, effects.css): without them it works the same.
import { avatarPicture } from "../../components/avatar.js";
import { sounds } from "../../components/sound.js";
import { h } from "../../dom.js";
import { confetti } from "../../effects/confetti.js";
import { flyStar } from "../../effects/star-flight.js";
import { tokenMs } from "../../effects/motion.js";
import { t } from "../../texts.js";
import { ring } from "./ring.js";

export function showCelebration(container, day, starsEarned, onClose) {
  let timer = null;
  const close = () => {
    clearTimeout(timer);
    layer.remove();
    onClose();
  };
  // With a star won (12/11): it is not there at first; it pops up big in the middle and
  // flies to the avatar, and then the count jumps in.
  const won = starsEarned > 0;
  const seat = h("img", { class: `celebration__star${won ? " celebration__star--waiting" : ""}`, src: day.celebration_star_url, alt: "" });
  const count = won && h("span", { class: "stars celebration__count celebration__count--waiting" },
    h("img", { src: day.star_url, alt: "" }), t.child.starsWon(starsEarned, day.stars));
  const layer = h("div", { class: "celebration-layer celebration", role: "status", onclick: close },
    h("h2", { class: "celebration__title" }, t.child.missionDone),
    h("div", { class: "celebration__hero" }, ring(1, avatarPicture(day.child), { className: "fx-shine" }), seat),
    count);

  container.append(layer);
  sounds.win();
  confetti(layer);
  if (won) landOnAvatar(layer, day, seat, count);
  timer = setTimeout(close, tokenMs("--celebration-duration", 6000));
}

async function landOnAvatar(layer, day, seat, count) {
  await new Promise((resolve) => setTimeout(resolve, tokenMs("--celebration-star-delay", 700)));
  if (!layer.isConnected) return;
  await flyStar(day.celebration_star_url, seat, { size: 300, layer });
  seat.classList.replace("celebration__star--waiting", "celebration__star--landed");
  count.classList.replace("celebration__count--waiting", "celebration__count--landed");
  sounds.ding();
  confetti(layer);
}
