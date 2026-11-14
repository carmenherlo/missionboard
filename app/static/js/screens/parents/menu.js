// The parents' menu (padres-menu.html, «como Home Assistant»): everything of Configurar,
// by groups, with Hoy on top and «A los niños» at the bottom. Always open on a wide
// screen; behind ☰ on a narrow one (vertical tablet, phone), over the screen.
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

// [path under #/parents/config, icon, label]; the groups of Configurar (ajustes.html).
const GROUPS = [
  [t.config.groupDay, [
    ["children", "children", t.config.children],
    ["missions", "missions", t.config.missions],
    ["routines", "clock", t.config.routines],
  ]],
  [t.config.groupRewards, [
    ["stars", "star", t.config.stars],
    ["streaks", "rocket", t.config.streaks],
    ["prizes", "prize", t.config.prizes],
    ["shop", "shop", t.config.shop],
  ]],
  [t.config.groupApp, [
    ["appearance", "palette", t.config.appearance],
    ["avatars", "smile", t.config.avatars],
    ["display", "eye", t.config.display],
    ["notify", "phone", t.config.notify], // only with Home Assistant
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
  const item = (href, iconName, label, id) => h("a", {
    class: `nav-item${id === on ? " nav-item--on" : ""}`, href,
    ...(id === on ? { "aria-current": "page" } : {}),
  }, icon(iconName), h("span", {}, label));

  const notifyItem = item("#/parents/config/notify", "phone", t.config.notify, "notify");
  notifyItem.hidden = notifyAvailable !== true && on !== "notify";
  askNotify().then((available) => { notifyItem.hidden = !available && on !== "notify"; });

  const drawer = h("nav", { class: "drawer", "aria-label": t.menu.label },
    h("p", { class: "drawer__brand" }, t.menu.brand),
    item("#/parents", "today", t.menu.today, "today"),
    GROUPS.flatMap(([title, sections]) => [
      h("p", { class: "drawer__group" }, title),
      ...sections.map(([path, iconName, label]) =>
        path === "notify" ? notifyItem : item(`#/parents/config/${path}`, iconName, label, path)),
    ]),
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
  return { drawer, scrim, button };
}
