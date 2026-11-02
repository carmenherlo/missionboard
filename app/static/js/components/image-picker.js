import { h } from "../dom.js";
import { icon } from "../icons.js";
import { isPhotoRef, loadImageLibraries } from "../images.js";
import { search } from "../search.js";
import { t } from "../texts.js";
import { imageThumb } from "./image-thumb.js";

const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_RESULTS = 120;

// Choose the image of a mission or step: none, one from a library, or a photo.
// `initial` is the saved image ({ ref, url } or null). onChange(choice) gets:
//   { kind: "none" }
//   { kind: "library", ref, url }
//   { kind: "photo", file, url }   (a new photo, not uploaded yet)
//   { kind: "current", ref, url }  (the photo already saved)
export async function imagePicker({ initial, onChange }) {
  const libraries = await loadImageLibraries();
  let choice = !initial?.ref
    ? { kind: "none" }
    : isPhotoRef(initial.ref)
      ? { kind: "current", ...initial }
      : { kind: "library", ...initial };
  let tab = { none: "none", library: "library", current: "photo", photo: "photo" }[choice.kind];
  let query = "";
  let libraryFilter = null;

  const tabs = h("div", { class: "tabs", role: "tablist" });
  const panel = h("div", { class: "picker-panel" });
  const element = h("div", { class: "image-picker" }, tabs, panel);

  function choose(next) {
    choice = next;
    onChange(choice);
    if (next.kind !== "library") {
      render();
      return;
    }
    // Only move the selection mark, so the list does not jump.
    for (const button of panel.querySelectorAll(".image-choice")) {
      const selected = button.dataset.ref === next.ref;
      button.classList.toggle("image-choice--selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    }
  }

  function renderTabs() {
    const entries = [["none", t.imagePicker.none], ["library", t.imagePicker.library], ["photo", t.imagePicker.photo]];
    tabs.replaceChildren(...entries.map(([id, label]) =>
      h("button", {
        type: "button", role: "tab", class: `tab${tab === id ? " tab--on" : ""}`,
        "aria-selected": String(tab === id),
        onclick: () => {
          tab = id;
          if (id === "none") choose({ kind: "none" });
          else render();
        },
      }, tab === id && icon("check"), label)));
  }

  function imageButton(item) {
    const selected = choice.kind === "library" && choice.ref === item.ref;
    return h("button", {
      type: "button", class: `image-choice${selected ? " image-choice--selected" : ""}`,
      "data-ref": item.ref,
      title: item.name, "aria-label": item.name, "aria-pressed": String(selected),
      onclick: () => choose({ kind: "library", ref: item.ref, url: item.url }),
    }, h("img", { src: item.url, alt: "", loading: "lazy" }));
  }

  function libraryPanel() {
    const shown = libraryFilter ? libraries.filter((l) => l.id === libraryFilter) : libraries;
    const results = h("div", { class: "image-results" });

    function renderResults() {
      if (!query.trim()) {
        results.replaceChildren(...shown.flatMap((library) => library.featured.map((theme) =>
          h("section", {},
            h("h3", { class: "image-theme" }, theme.name),
            h("div", { class: "image-grid" }, theme.items.map(imageButton))))));
        return;
      }
      const hits = search(shown.flatMap((l) => l.items), query, MAX_RESULTS);
      results.replaceChildren(hits.length
        ? h("div", { class: "image-grid" }, hits.map(imageButton))
        : h("p", { class: "empty" }, t.imagePicker.noResults(query)));
    }

    const input = h("input", {
      type: "search", class: "search-input", value: query,
      placeholder: t.imagePicker.searchPlaceholder, "aria-label": t.imagePicker.searchPlaceholder,
      oninput: (e) => { query = e.target.value; renderResults(); },
    });
    // Only when there is more than one library, so it can be told apart.
    const filters = libraries.length > 1
      ? h("div", { class: "chips" },
          [[null, t.imagePicker.allLibraries], ...libraries.map((l) => [l.id, l.name])].map(([id, label]) =>
            h("button", {
              type: "button", class: `chip${libraryFilter === id ? " chip--on" : ""}`,
              onclick: () => { libraryFilter = id; render(); },
            }, label)))
      : null;

    renderResults();
    return [h("label", { class: "search" }, icon("search"), input), filters, results];
  }

  function photoPanel() {
    const error = h("p", { class: "form-error", role: "alert" });
    const fileInput = h("input", {
      type: "file", accept: PHOTO_TYPES.join(","), hidden: true,
      onchange: (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (!PHOTO_TYPES.includes(file.type)) {
          error.textContent = t.imagePicker.badPhotoType;
          return;
        }
        if (choice.kind === "photo") URL.revokeObjectURL(choice.url);
        choose({ kind: "photo", file, url: URL.createObjectURL(file) });
      },
    });
    const hasPhoto = choice.kind === "photo" || choice.kind === "current";
    return [
      hasPhoto ? imageThumb(choice.url, { size: "lg" }) : null,
      h("button", { type: "button", class: "btn", onclick: () => fileInput.click() },
        hasPhoto ? t.imagePicker.changePhoto : t.imagePicker.choosePhoto),
      fileInput,
      error,
    ];
  }

  function render() {
    renderTabs();
    if (tab === "none") panel.replaceChildren(h("p", { class: "hint" }, t.imagePicker.noneHint));
    else if (tab === "library") {
      const focused = document.activeElement?.classList.contains("search-input");
      panel.replaceChildren(...libraryPanel().filter(Boolean));
      if (focused) panel.querySelector(".search-input")?.focus();
    } else panel.replaceChildren(...photoPanel().filter(Boolean));
  }

  render();
  return { element, value: () => choice };
}

// Save a picker choice: library/none through `patch`, a new photo through `upload`.
export async function saveImageChoice(choice, { patch, upload }) {
  if (choice.kind === "none") return patch(null);
  if (choice.kind === "library") return patch(choice.ref);
  if (choice.kind === "photo") return upload(choice.file);
  return null; // "current": nothing changed
}
