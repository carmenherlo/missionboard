// Zona de padres · Hoy, «Cómo van» (zona-padres.html, H1 and section 3): each child's day.
// On a tablet or a computer, one table: a row per child, a column per mission (the
// missions are the family's, the same for all). On a phone (CSS, under 600 px) the table
// does not fit: each child is a folded card with a chip per mission; a tap opens it.
// A mission done opens «¿no la ha hecho?» (undo-mission.js); «Hoy no puede…», day-off.js.
import { avatar } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { rocketReady, weekMini } from "../child/week-bar.js";
import { askDayOff } from "./day-off.js";
import { askUndo } from "./undo-mission.js";

const STAR = "static/libraries/fluent/star.svg";

// [class, short text] of a mission's state today.
const STATE = {
  done: () => ["done", t.overview.done],
  open: (m) => ["open", t.overview.progressShort(m.done, m.total)],
  upcoming: (m) => ["later", m.schedule ? m.schedule.start : t.overview.later],
  closed: () => ["closed", t.overview.closedShort],
  off: () => ["off", t.dayOff.stateOff],
};

export function kidsDay(view, redraw) {
  return h("div", { class: "kids-day" }, kidsTable(view, redraw), kidsCards(view, redraw));
}

// The family's missions of today, in the order they come.
function columns(children) {
  const seen = new Map();
  children.forEach((day) => day.missions.forEach((m) => { if (!seen.has(m.id)) seen.set(m.id, m); }));
  return [...seen.values()];
}

// A mission's state; done, a button that asks whether to undo it (plain: only to look).
function stateChip(day, m, redraw, { long = false, plain = false } = {}) {
  const [kind, text] = STATE[m.state](m);
  const content = [!long && imageThumb(m.image_url, { size: "xs", label: m.name }), text];
  const kindClass = `state state--${kind}`;
  return m.state === "done" && !plain
    ? h("button", {
        type: "button", class: `${kindClass} state--button`, "aria-label": t.dayOff.undoTitle(m.name, day.child.name),
        onclick: () => askUndo(day.child, m.id, day.day, { onDone: redraw }),
      }, ...content)
    : h("span", { class: kindClass, title: m.name }, ...content);
}

function prizeText(prize) {
  if (!prize) return "—";
  if (prize.state === "won") return prize.won.map((w) => w.text).join(", ");
  return prize.state === "unlocked" ? t.overview.prizeShortUnlocked : t.overview.prizeShortLocked;
}

const weekShown = (day) => day.week?.on && day.week.shown && day.week.tanks.length > 0;
const week = (day) => weekShown(day) && h("span", { class: "kid-week" },
  weekMini(day.week, { onTap: () => { location.hash = `#/parents/config/children/${day.child.id}`; } }), rocketReady(day.week) && h("span", { class: "kid-week__ready" }, t.overview.weekReady));

const stars = (day) => h("span", { class: "day-card__count" }, h("img", { src: STAR, alt: "" }), String(day.stars));

const canNot = (day, redraw, extra = "btn") => h("button", {
  type: "button", class: extra,
  onclick: () => askDayOff(day.child, day.day, { onClose: redraw }),
}, t.dayOff.canNot);

const childLink = (day) => h("a", {
  class: "kids-table__child", href: `#/parents/config/children/${day.child.id}`, "aria-label": t.overview.openChild(day.child.name),
}, avatar(day.child, { size: "sm" }), h("b", {}, day.child.name));

function kidsTable(view, redraw) {
  const missions = columns(view.children);
  const anyPrize = view.children.some((day) => day.prize);
  const anyWeek = view.children.some(weekShown);
  const head = h("tr", {},
    h("th", { scope: "col", "aria-label": t.config.children }),
    missions.map((m) => h("th", { scope: "col" },
      h("span", { class: "kids-table__mission" }, imageThumb(m.image_url, { size: "sm", label: m.name }), m.name))),
    anyPrize && h("th", { scope: "col" }, t.overview.colPrize),
    anyWeek && h("th", { scope: "col" }, t.overview.colWeek),
    h("th", { scope: "col" }, h("img", { class: "kids-table__star", src: STAR, alt: t.overview.colStars })));

  const row = (day) => {
    const byId = Object.fromEntries(day.missions.map((m) => [m.id, m]));
    const cells = day.day_off
      ? [h("td", { colspan: Math.max(missions.length, 1) }, h("span", { class: "state state--off" }, t.dayOff.dayOffCard))]
      : missions.map((m) => h("td", {}, byId[m.id] ? stateChip(day, byId[m.id], redraw, { long: true }) : "—"));
    return h("tr", { style: `--child-color: ${day.colors.color}` },
      h("th", { scope: "row" }, h("span", { class: "kids-table__who" }, childLink(day), !day.day_off && canNot(day, redraw, "kids-table__can-not"))),
      ...cells,
      anyPrize && h("td", { class: "kids-table__prize" }, prizeText(day.prize)),
      anyWeek && h("td", {}, week(day) || "—"),
      h("td", { class: "kids-table__stars" }, String(day.stars)));
  };

  return h("div", { class: "kids-table-wrap" },
    h("table", { class: "kids-table" }, h("thead", {}, head), h("tbody", {}, view.children.map(row))));
}

// On a phone: a folded card per child (avatar, name, stars, a chip per mission and the
// week); open, the missions by name, the day's prize and what a parent can do.
function kidsCards(view, redraw) {
  const card = (day) => h("details", { class: "kid-card", style: `--child-color: ${day.colors.color}` },
    h("summary", { class: "kid-card__summary" },
      h("span", { class: "kid-card__head" }, avatar(day.child, { size: "sm" }), h("b", {}, day.child.name), stars(day),
        h("span", { class: "kid-card__fold" }, icon("next"))),
      h("span", { class: "kid-card__chips" },
        day.day_off
          ? h("span", { class: "state state--off" }, t.dayOff.dayOffCard)
          : day.missions.map((m) => stateChip(day, m, redraw, { plain: true })), // a tap opens the card
        week(day))),
    h("div", { class: "kid-card__more" },
      !day.day_off && h("ul", { class: "day-card__missions" }, day.missions.map((m) => h("li", {},
        imageThumb(m.image_url, { size: "sm", label: m.name }),
        h("span", { class: "day-card__mission" }, m.name),
        stateChip(day, m, redraw, { long: true })))),
      day.prize && h("p", { class: "day-card__prize" }, icon("prize"), `${t.overview.colPrize}: ${prizeText(day.prize)}`),
      h("p", { class: "kid-card__actions" },
        !day.day_off && canNot(day, redraw),
        h("a", { class: "btn", href: `#/parents/config/children/${day.child.id}` }, t.overview.seeChild(day.child.name)))));
  return h("div", { class: "kid-cards" }, view.children.map(card));
}
