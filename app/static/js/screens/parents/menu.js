// The parents' menu (menu-padres-2.html): four doors, one question each. Hoy (how are
// they doing), Por dar (what to hand over, with how many), Niños (each child) and Ajustes
// (the house rules, the same for everyone). On a wide screen, all at the side, Ajustes
// open; on a vertical tablet, behind ☰; on a phone, a bar at the bottom with the four
// and Ajustes as a page of its own (settings-home.js).
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

// [title, [path under #/parents/config, icon, label, options], key]: Ajustes by groups
// (the key gives each group its colour on the Ajustes page).
export const SETTINGS = [
  [t.config.groupDo, [
    ["missions", "missions", t.config.missions],
    ["routines", "clock", t.config.routines],
  ], "do"],
  [t.config.groupEarn, [
    ["stars", "star", t.config.stars],
    ["prizes", "wheel", t.config.prizes],
    ["streaks", "rocket", t.config.streaksMenu],
    ["shop", "shop", t.config.shop],
  ], "earn"],
  [t.config.groupApp, [
    ["appearance", "palette", t.config.appearance],
    ["notify", "phone", t.config.notify], // only with Home Assistant
    ["display", "eye", t.config.display, { notOnPhone: true }], // the screen the children use
  ], "app"],
  [t.config.groupSafety, [
    ["code", "parentCode", t.config.parentCode],
    ["device", "phone", t.config.device], // a parent's phone, without the code
    ["backup", "download", t.config.backup],
    ["log", "history", t.config.eventLog],
  ], "safety"],
];

// Avisos al móvil only inside Home Assistant (nobody to tell elsewhere): asked once.
let notifyAvailable = null;
const askNotify = () => (notifyAvailable ??= api("GET", "api/notify")
  .then((answer) => answer.available).catch(() => false));

// Hides «Avisos al móvil» until the server says there is Home Assistant (not while on it).
export function notifyOnlyWithHA(element, on) {
  element.hidden = notifyAvailable !== true && on !== "notify";
  askNotify().then((available) => { element.hidden = !available && on !== "notify"; });
  return element;
}

// The number on «Por dar»: orders and week prizes waiting. Hidden at 0.
function showToGive(badges) {
  api("GET", "api/overview/to-give").then(({ count }) => badges.forEach((badge) => {
    badge.hidden = !count;
    badge.textContent = String(count);
    badge.title = t.menu.toGiveCount(count);
  })).catch(() => {});
}

// After handing something over: the number again, wherever it shows.
export function refreshToGive() {
  showToGive([...document.querySelectorAll(".nav-badge")]);
}

// The section open now: its id in the menu.
function sectionNow() {
  const hash = location.hash;
  if (hash.startsWith("#/parents/give")) return "give";
  if (/^#\/parents\/config\/?$/.test(hash)) return "settings";
  const match = hash.match(/^#\/parents\/config\/([\w-]+)/);
  if (!match) return "today"; // Hoy and Padres · Niño
  return { settings: "appearance", avatars: "children" }[match[1]] ?? match[1];
}

// [id, href, icon, label]: the three doors of every day, on top.
const DAILY = [
  ["today", "#/parents", "today", t.menu.today],
  ["give", "#/parents/give", "prize", t.menu.toGive],
  ["children", "#/parents/config/children", "children", t.config.children],
];

export function parentsMenu() {
  const on = sectionNow();
  const badges = [];
  const badge = (id) => {
    if (id !== "give") return null;
    const element = h("span", { class: "nav-badge", hidden: true });
    badges.push(element);
    return element;
  };
  const current = (id, active) => (id === active ? { "aria-current": "page" } : {});
  const item = (id, href, iconName, label, extra = "") => h("a", {
    class: `nav-item${id === on ? " nav-item--on" : ""}${extra}`, href, ...current(id, on),
  }, icon(iconName), h("span", {}, label), badge(id));

  const drawer = h("nav", { class: "drawer", "aria-label": t.menu.label },
    h("p", { class: "drawer__brand" }, t.menu.brand),
    DAILY.map(([id, href, iconName, label]) => item(id, href, iconName, label)),
    SETTINGS.flatMap(([title, sections]) => [
      h("p", { class: "drawer__group" }, title),
      ...sections.map(([path, iconName, label, { notOnPhone = false } = {}]) => {
        const link = item(path, `#/parents/config/${path}`, iconName, label, notOnPhone ? " not-on-phone" : "");
        return path === "notify" ? notifyOnlyWithHA(link, on) : link;
      }),
    ]),
    h("hr", { class: "drawer__line" }),
    item("kids", "#/", "home", t.menu.kids));

  const scrim = h("div", { class: "drawer-scrim", onclick: () => close() });
  const close = () => drawer.classList.remove("drawer--open");
  const open = () => {
    drawer.classList.add("drawer--open");
    drawer.querySelector(".nav-item--on, .nav-item")?.focus();
  };
  drawer.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });

  const button = h("button", {
    type: "button", class: "icon-button icon-button--ghost menu-button",
    "aria-label": t.menu.open, title: t.menu.open, onclick: open,
  }, icon("menu"));

  // On a phone, the bar at the bottom for the thumb; any section of Ajustes lights it.
  const tabOn = DAILY.some(([id]) => id === on) ? on : "settings";
  const tab = (id, href, iconName, label) => h("a", {
    class: `bottom-nav__item${id === tabOn ? " bottom-nav__item--on" : ""}`, href, ...current(id, tabOn),
  }, h("span", { class: "bottom-nav__icon" }, icon(iconName), badge(id)), h("span", {}, label));
  const bottom = h("nav", { class: "bottom-nav", "aria-label": t.menu.bottom },
    DAILY.map(([id, href, iconName, label]) => tab(id, href, iconName, label)),
    tab("settings", "#/parents/config", "settings", t.config.title));

  showToGive(badges);
  return { drawer, scrim, button, bottom };
}
