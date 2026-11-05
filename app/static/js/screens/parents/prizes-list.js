import { api, errorMessage } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

// Like the steps of a mission: a list, "add" at the bottom, the pencil to edit.
// No order to drag: the wheel picks at random.
export async function viewPrizesList() {
  const prizes = await api("GET", "/api/prizes");

  const input = h("input", { type: "text", maxlength: 40, placeholder: t.prizes.newPrize });
  const error = h("p", { class: "form-error", role: "alert" });
  const add = h("form", {
    class: "row row--add", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      try {
        await api("POST", "/api/prizes", { json: { text } });
        await viewPrizesList();
        document.querySelector(".row--add input")?.focus();
      } catch (err) {
        error.textContent = errorMessage(err);
      }
    },
  }, input, h("button", { class: "btn btn--primary", type: "submit" }, icon("plus"), t.prizes.add));

  render(
    parentsHeader(t.prizes.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("p", { class: "hint" }, prizes.length ? t.prizes.hint : t.prizes.empty),
        panel(t.prizes.count(prizes.length),
          prizes.length > 0 && h("ul", { class: "rows" }, prizes.map((prize) =>
            h("li", { class: "row row--compact row--covered" }, // the whole card opens it (rutinas-7)
              imageThumb(prize.image_url, { size: "sm", label: prize.text, suggested: prize.image_suggested }),
              h("a", {
                class: "row__text row__cover", href: `#/parents/config/prizes/${prize.id}`,
                "aria-label": t.prizes.editNamed(prize.text),
              }, prize.text),
              h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next"))))),
          add, error))));
}
