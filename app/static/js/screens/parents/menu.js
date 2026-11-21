// The parents' menu (padres-menu.html, «como Home Assistant»): everything of Configurar,
// by groups, with Hoy on top and «A los niños» at the bottom. Always open on a wide
// screen; behind ☰ on a narrow one (vertical tablet, phone), over the screen.
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

// [path under #/parents/config, icon, label]; the groups by rhythm (zona-padres.html, M2):
// what happens each day, each week, and what the stars are for; then the app itself.
const GROUPS = [
  [t.config.groupDaily, [
    ["missions", "missions", t.config.missions],
    ["routines", "clock", t.config.routines],
    ["prizes", "prize", t.config.prizes],
  ]],
  [t.config.groupWeekly, [
    ["streaks", "rocket", t.config.streaksMenu],
  ]],
  [t.config.groupStars, [
    ["stars", "star", t.config.stars],
    ["shop", "shop", t.config.shop],
  ]],
  [t.config.groupApp, [
    ["appearance", "palette", t.config.appearance],
    ["avatars", "smile", t.config.avatars],
    ["notify", "phone", t.config.notify], // only with Home Assistant
  ]],
  [t.config.groupDevice, [
    ["display", "eye", t.config.display],
  ], { notOnPhone: true }], // rest and front page: for the screen the children use
  [t.config.groupSafety, [
    ["code", "parentCode", t.config.parentCode],
    ["backup", "download", t.config.backup],
    ["log", "history", t.config.eventLog],
  ]],
];

// Avisos al móvil only inside Home Assistant (nobody to tell elsewhere): asked once.
let notifyAvailable = null;
const askNotify = () => (notifyAvailable ??= api("GET", "api/notify")
  .then((answer) => answer.available).catch(() => false));

// The section of the screen open now: "today" for Hoy and Padres · Niño.
function sectionNow() {
  const match = location.hash.match(/^#\/parents\/config\/([\w-]+)/);
  return match ? ({ settings: "appearance" }[match[1]] ?? match[1]) : "today";
}

export function parentsMenu() {
  const on = sectionNow();
  const item = (href, iconName, label, id, extra = "") => h("a", {
    class: `nav-item${id === on ? " nav-item--on" : ""}${extra}`, href,
    ...(id === on ? { "aria-current": "page" } : {}),
  }, icon(iconName), h("span", {}, label));

  const notifyItem = item("#/parents/config/notify", "phone", t.config.notify, "notify");
  notifyItem.hidden = notifyAvailable !== true && on !== "notify";
  askNotify().then((available) => { notifyItem.hidden = !available && on !== "notify"; });

  const drawer = h("nav", { class: "drawer", "aria-label": t.menu.label },
    h("p", { class: "drawer__brand" }, t.menu.brand),
    item("#/parents", "today", t.menu.today, "today"),
    item("#/parents/config/children", "children", t.config.children, "children"),
    GROUPS.flatMap(([title, sections, { notOnPhone = false } = {}]) => {
      const extra = notOnPhone ? " not-on-phone" : "";
      return [
        h("p", { class: `drawer__group${extra}` }, title),
        ...sections.map(([path, iconName, label]) =>
          path === "notify" ? notifyItem : item(`#/parents/config/${path}`, iconName, label, path, extra)),
      ];
    }),
    h("hr", { class: "drawer__line" }),
    item("#/", "home", t.menu.kids, "kids"));

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

  // On a phone, a bar at the bottom for the thumb (zona-padres.html, section 3): Hoy,
  // Niños and «Más», which opens the menu. Hidden on wider screens (parents-menu.css).
  const tab = (href, iconName, label, id) => h("a", {
    class: `bottom-nav__item${id === on ? " bottom-nav__item--on" : ""}`, href,
    ...(id === on ? { "aria-current": "page" } : {}),
  }, icon(iconName), h("span", {}, label));
  const bottom = h("nav", { class: "bottom-nav", "aria-label": t.menu.bottom },
    tab("#/parents", "today", t.menu.today, "today"),
    tab("#/parents/config/children", "children", t.config.children, "children"),
    h("button", { type: "button", class: "bottom-nav__item", onclick: open }, icon("menu"), h("span", {}, t.menu.more)));
  return { drawer, scrim, button, bottom };
}
