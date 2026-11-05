// The clock (reloj.html): the other home screen, to leave on in sight. The routine's
// clock with its hands, the time in numbers and the day, the next routine to ring,
// and the kids small below (a tap opens their route). "Niños" goes back to them.
import { api } from "../api.js";
import { avatar } from "../components/avatar.js";
import { h } from "../dom.js";
import { clockFace } from "../routine/clock-face.js";
import { t } from "../texts.js";

const NEXT_EVERY_MS = 60_000;

export function clockScreen(children) {
  const dial = h("div", { class: "clock-screen__dial" });
  const time = h("p", { class: "clock-screen__time" });
  const date = h("p", { class: "clock-screen__date" });
  const next = h("div", { class: "clock-screen__next", hidden: true });
  const element = h("section", { class: "clock-screen" },
    h("div", { class: "clock-screen__main" }, dial, h("div", { class: "clock-screen__side" }, time, date, next)),
    children.length > 0 && h("div", { class: "clock-screen__kids" }, children.map((child) =>
      h("a", { class: "clock-screen__kid", href: `#/child/${child.id}`, "aria-label": child.name },
        avatar(child, { size: "md" })))));

  function tick() {
    const now = new Date();
    const minute = now.getHours() * 60 + now.getMinutes() + now.getSeconds() / 60 + now.getMilliseconds() / 60000;
    dial.replaceChildren(clockFace({ kind: "done" }, minute, []));
    time.textContent = `${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")}`;
    date.textContent = now.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  }

  async function loadNext() {
    const routine = await api("GET", "api/routines/next").catch(() => null);
    next.hidden = !routine;
    if (!routine) return;
    next.replaceChildren(h("img", { src: routine.image_url, alt: "" }),
      h("span", {}, h("b", {}, routine.name), h("span", {}, t.clock.rings(routine.in_days, routine.at))));
  }

  tick();
  loadNext();
  // While on screen: the hands every second, the next routine every minute.
  const ticker = setInterval(() => (element.isConnected ? tick() : clearInterval(ticker)), 1000);
  const nexter = setInterval(() => (element.isConnected ? loadNext() : clearInterval(nexter)), NEXT_EVERY_MS);
  return element;
}
