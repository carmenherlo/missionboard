// Entry point: maps each URL hash to its screen.

import { errorMessage, session } from "./api.js";
import { h, render } from "./dom.js";
import { viewHome } from "./screens/home.js";
import { viewChangeCode } from "./screens/parents/change-code.js";
import { viewChildForm } from "./screens/parents/child-form.js";
import { viewChildrenList } from "./screens/parents/children-list.js";
import { viewConfigIndex } from "./screens/parents/config-index.js";
import { viewParentsLock } from "./screens/parents/lock.js";
import { t } from "./texts.js";

// [pattern, screen, parentsOnly]
const routes = [
  [/^#?\/?$/, () => viewHome()],
  [/^#\/parents\/?$/, () => { location.hash = "#/parents/config"; }, true],
  [/^#\/parents\/config$/, () => viewConfigIndex(), true],
  [/^#\/parents\/config\/code$/, () => viewChangeCode(), true],
  [/^#\/parents\/config\/children$/, () => viewChildrenList(), true],
  [/^#\/parents\/config\/children\/new$/, () => viewChildForm(null), true],
  [/^#\/parents\/config\/children\/([\w-]+)$/, (m) => viewChildForm(m[1]), true],
];

async function route() {
  const hash = location.hash;
  for (const [pattern, view, parentsOnly] of routes) {
    const match = hash.match(pattern);
    if (!match) continue;
    if (parentsOnly && !session.parentCode) return viewParentsLock(route);
    try {
      await view(match);
    } catch (err) {
      render(h("main", { class: "page page--center" },
        h("p", { class: "form-error" }, errorMessage(err)),
        h("a", { class: "btn", href: "#/" }, t.errors.backHome)));
    }
    return;
  }
  location.hash = "#/";
}

window.addEventListener("hashchange", route);
route();
