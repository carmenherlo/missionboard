// Padres · Hoy (step 7): the first screen after the code. How each child is doing
// today (missions, stars, streak, prize), and what is waiting to be handed over:
// the prizes of the wheel and the shop's orders. Configurar is one tap away.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { dayMonth, ordersPanel } from "./orders-panel.js";

const STAR = "static/libraries/fluent/star.svg";
const FIRE = "static/libraries/fluent/fire.svg";

export async function viewParentsToday() {
  const [view, orders] = await Promise.all([api("GET", "api/overview/today"), api("GET", "api/orders"), loadAvatars()]);
  const status = saveStatus();
  const prizes = h("div", {});

  function drawPrizes(list) {
    prizes.replaceChildren(list.length
      ? panel(t.overview.prizesTitle,
          h("p", { class: "hint" }, t.overview.prizesHint),
          h("ul", { class: "rows" }, list.map((spin) => h("li", { class: "row row--compact" },
            imageThumb(spin.image_url, { size: "sm", label: spin.prize_text }),
            h("span", { class: "row__text" }, spin.prize_text,
              h("span", { class: "row__detail" }, t.overview.wonOn(spin.child_name, dayMonth(spin.day)))),
            h("button", {
              type: "button", class: "btn btn--primary",
              onclick: async () => {
                await status.track(api("POST", `api/overview/prizes/${spin.id}/deliver`)).catch(() => {});
                drawPrizes((await api("GET", "api/overview/today")).prizes);
              },
            }, icon("check"), t.shop.given)))))
      : "");
  }
  drawPrizes(view.prizes);

  render(
    parentsHeader(h("span", { class: "title-line" }, t.overview.title, status.element)),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("a", { class: "row row--link", href: "#/parents/config" },
          h("span", { class: "row__icon" }, icon("settings")),
          h("span", { class: "row__name" }, t.config.title),
          h("span", { class: "row__chevron" }, icon("next"))),
        view.children.length
          ? h("div", { class: "day-cards" }, view.children.map(dayCard))
          : h("p", { class: "hint" }, t.overview.noChildren),
        prizes,
        (orders.waiting.length > 0 || orders.handed.length > 0) && ordersPanel(orders, status))));
}

const STATE = {
  done: (m) => ["day-card__state--done", t.overview.done],
  open: (m) => ["day-card__state--open", t.overview.progress(m.done, m.total)],
  upcoming: (m) => ["", m.schedule ? t.overview.at(m.schedule.start) : t.overview.later],
  closed: () => ["day-card__state--closed", t.overview.closed],
};

// One child's day, as a card that opens Padres · Niño.
function dayCard(day) {
  const prize = day.prize;
  return h("a", {
    class: "day-card", href: `#/parents/kids/${day.child.id}`,
    style: `--child-color: ${day.colors.color}`, // the child's colour: the one style from code
    "aria-label": t.overview.openChild(day.child.name),
  },
    h("div", { class: "day-card__head" },
      avatar(day.child, { size: "md" }),
      h("b", { class: "day-card__name" }, day.child.name),
      h("span", { class: "day-card__count" }, h("img", { src: STAR, alt: "" }), String(day.stars)),
      day.streak > 0 && h("span", { class: "day-card__count", title: t.overview.streak(day.streak) },
        h("img", { src: FIRE, alt: "" }), String(day.streak))),
    day.missions.length
      ? h("ul", { class: "day-card__missions" }, day.missions.map((m) => {
          const [kind, text] = STATE[m.state](m);
          return h("li", {},
            imageThumb(m.image_url, { size: "sm", label: m.name }),
            h("span", { class: "day-card__mission" }, m.name),
            h("span", { class: `day-card__state ${kind}` }, text));
        }))
      : h("p", { class: "hint" }, t.overview.noMissions),
    prize && h("p", { class: "day-card__prize" }, icon("prize"),
      prize.state === "won" ? t.overview.prizeWon(prize.won.map((w) => w.text).join(", "))
        : prize.state === "unlocked" ? t.overview.prizeUnlocked : t.overview.prizeLocked));
}
