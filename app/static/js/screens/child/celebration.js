// "¡Misión cumplida!": the child's avatar in their full ring, the star won
// and how many they have now. Closes by itself or with a tap. The confetti
// and the glow are effects (effects/, effects.css): without them it works the same.
import { avatarPicture } from "../../components/avatar.js";
import { h } from "../../dom.js";
import { confetti } from "../../effects/confetti.js";
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
  const layer = h("div", { class: "celebration-layer celebration", role: "status", onclick: close },
    h("h2", { class: "celebration__title" }, t.child.missionDone),
    h("div", { class: "celebration__hero" },
      ring(1, avatarPicture(day.child), { className: "fx-shine" }),
      h("img", { class: "celebration__star", src: day.celebration_star_url, alt: "" })),
    starsEarned > 0 && h("span", { class: "stars" },
      h("img", { src: day.star_url, alt: "" }), t.child.starsWon(starsEarned, day.stars)));

  container.append(layer);
  confetti(layer);
  timer = setTimeout(close, tokenMs("--celebration-duration", 5000));
}
