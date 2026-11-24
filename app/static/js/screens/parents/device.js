// Ajustes → Este aparato (padres-movil.html, the short way): a parent's phone remembers
// the code, so the app opens in the parents' zone without asking. Kept on the device only.
import { session } from "../../api.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { rememberCode, rememberedCode } from "../../remembered-device.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export function viewDevice() {
  const toggle = h("label", { class: "toggle" },
    h("input", {
      type: "checkbox", checked: !!rememberedCode(),
      onchange: (e) => rememberCode(e.target.checked ? session.parentCode : null),
    }),
    t.device.remember);

  render(
    parentsHeader(t.device.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      panel(t.device.title, h("div", { class: "stack stack--tight" },
        toggle,
        h("p", { class: "hint" }, t.device.hint),
        h("p", { class: "hint" }, t.device.notTablet)))));
}
