// ¿Quién está? (rutinas-flexibles.html): a parent takes a child out of the routine going on, or
// puts them back. Out, they leave its screen, the goal does not wait for them and, in a race,
// they do not count; they lose nothing (their mission stays as it is). Nobody left: it is
// finished. In «± Tiempo» (extra-time.js) and the parents' phone panel (remote.js).
import { api } from "../api.js";
import { avatar, loadAvatars } from "../components/avatar.js";
import { h } from "../dom.js";
import { t } from "../texts.js";

// `parentCode` null: the session's.
export function whoList(r, parentCode = null) {
  const url = () => `api/routines/${r.showing.data.id}/who`;
  const body = h("ul", { class: "rows" });
  const element = h("div", { class: "who" }, h("h3", { class: "remote-panel__title" }, t.routine.whoTitle), body);
  let kids = [];

  async function change(kid, here) {
    const chosen = kids.filter((k) => (k.id === kid.id ? here : k.here)).map((k) => k.id);
    await api("PUT", url(), { parentCode, json: { kids: chosen } }).catch(() => {});
    if (!chosen.length) return r.end();
    await r.check();
    load();
  }

  async function load() {
    if (!r.showing) return;
    [kids] = await Promise.all([api("GET", url(), { parentCode }).catch(() => []), loadAvatars()]);
    body.replaceChildren(...kids.map((kid) => h("li", { class: "row row--compact" },
      h("input", { type: "checkbox", checked: kid.here, "aria-label": kid.name, onchange: (e) => change(kid, e.target.checked) }),
      avatar(kid, { size: "sm" }),
      h("span", { class: "row__text" }, kid.name))));
  }
  load();
  return { element };
}
