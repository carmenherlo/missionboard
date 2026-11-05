import { api, errorMessage } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

// Like Premios del día, each item with its price in stars.
export async function viewShopList() {
  const items = await api("GET", "/api/shop");

  const text = h("input", { type: "text", maxlength: 40, placeholder: t.shop.newItem });
  const price = h("input", { type: "number", min: 1, max: 999, value: 5, "aria-label": t.shop.price });
  const error = h("p", { class: "form-error", role: "alert" });
  const add = h("form", {
    class: "row row--add", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      if (!text.value.trim() || !(Number(price.value) >= 1)) return;
      try {
        await api("POST", "/api/shop", { json: { text: text.value.trim(), price: Number(price.value) } });
        await viewShopList();
        document.querySelector(".row--add input")?.focus();
      } catch (err) {
        error.textContent = errorMessage(err);
      }
    },
  }, text, price, h("button", { class: "btn btn--primary", type: "submit" }, icon("plus"), t.shop.add));

  render(
    parentsHeader(t.shop.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("p", { class: "hint" }, items.length ? t.shop.hint : t.shop.empty),
        panel(t.shop.count(items.length),
          items.length > 0 && h("ul", { class: "rows" }, items.map((item) =>
            h("li", { class: "row row--compact row--covered" }, // the whole card opens it (rutinas-7)
              imageThumb(item.image_url, { size: "sm", label: item.text, suggested: item.image_suggested }),
              h("a", {
                class: "row__text row__cover", href: `#/parents/config/shop/${item.id}`,
                "aria-label": t.shop.editNamed(item.text),
              }, item.text,
                h("span", { class: "row__detail" }, h("span", { class: "pill" }, t.shop.priceText(item.price)))),
              h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next"))))),
          add, error))));
}
