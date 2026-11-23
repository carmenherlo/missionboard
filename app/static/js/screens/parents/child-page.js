// Niños → Bea (ficha-nino.html): a child's card, only to look and to act on the day.
// On top, who they are, their stars and «Ajustes de Bea» (their settings, apart:
// child-settings.js); below, two blocks: Esta semana (child-week.js) and Estrellas
// (child-stars.js), side by side when there is room.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { starsBlock } from "./child-stars.js";
import { weekBlock } from "./child-week.js";
import { parentsHeader } from "./common.js";

const STAR = "static/libraries/fluent/star.svg";

export async function viewChildPage(childId) {
  const [view, done] = await Promise.all([api("GET", `api/overview/children/${childId}`),
    api("GET", `api/children/${childId}/undoable`), loadAvatars()]);
  const here = `#/parents/config/children/${childId}`;
  const again = () => viewChildPage(childId);

  render(
    parentsHeader(h("span", { class: "title-with-avatar" }, avatar(view.child, { size: "md" }), view.child.name),
      { href: "#/parents/config/children", label: t.children.back }),
    h("main", { class: "page" },
      h("div", { class: "card-head" },
        h("p", { class: "card-head__stars" },
          h("img", { src: STAR, alt: "" }), t.childStars.has(view.stars)),
        h("a", { class: "btn", href: `${here}/settings` }, icon("settings"), t.childCard.settings(view.child.name))),
      h("div", { class: "card-blocks" },
        weekBlock(view, done, again),
        starsBlock(view, here, again))));
}
