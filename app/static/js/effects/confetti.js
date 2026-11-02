// Confetti: paper pieces and stars shoot up from the middle of `container`,
// spin and fall. One burst, then the canvas removes itself. Pure decoration:
// nothing waits for it, and with "reduce motion" it does nothing.
import { reducedMotion, token } from "./motion.js";

const PIECES = 220;
const LIFE = 230; // frames (~4 s)
const GRAVITY = 0.32;
const AIR = 0.98;

export function confetti(container) {
  if (reducedMotion()) return;
  const canvas = document.createElement("canvas");
  canvas.className = "confetti";
  canvas.setAttribute("aria-hidden", "true");
  canvas.width = container.clientWidth;
  canvas.height = container.clientHeight;
  container.prepend(canvas);

  const ctx = canvas.getContext("2d");
  const colors = [1, 2, 3, 4, 5, 6].map((n) => token(`--confetti-${n}`));
  const starColor = token("--confetti-star");
  const { width: W, height: H } = canvas;
  let pieces = Array.from({ length: PIECES }, (_, i) => {
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.1;
    const speed = 12 + Math.random() * 16;
    return {
      x: W / 2 + (Math.random() - 0.5) * 60, y: H * 0.5,
      vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed,
      rot: Math.random() * Math.PI, vrot: (Math.random() - 0.5) * 0.35,
      flip: Math.random() * Math.PI, vflip: 0.1 + Math.random() * 0.15,
      size: 16 + Math.random() * 14,
      color: colors[i % colors.length],
      star: i % 6 === 0,
      life: 0,
    };
  });

  function drawStar(r) {
    ctx.beginPath();
    for (let i = 0; i < 10; i++) {
      const a = (Math.PI / 5) * i - Math.PI / 2;
      const rr = i % 2 ? r * 0.45 : r;
      ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
    }
    ctx.closePath();
    ctx.fill();
  }

  function frame() {
    ctx.clearRect(0, 0, W, H);
    for (const p of pieces) {
      p.vy += GRAVITY;
      p.vx *= AIR;
      p.vy *= AIR;
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vrot;
      p.flip += p.vflip;
      p.life++;
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.globalAlpha = Math.min(1, Math.max(0, (LIFE - p.life) / 50)); // fade at the end only
      if (p.star) {
        ctx.fillStyle = starColor;
        drawStar(p.size * 0.9);
      } else {
        ctx.scale(1, Math.cos(p.flip)); // paper turning over
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
      }
      ctx.restore();
    }
    pieces = pieces.filter((p) => p.y < H + 40 && p.life < LIFE);
    if (pieces.length && canvas.isConnected) requestAnimationFrame(frame);
    else canvas.remove();
  }
  frame();
}
