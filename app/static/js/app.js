"use strict";

const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];

const state = {
  parentCode: null,
  avatars: null,
};

// ---------- helpers ----------

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else if (key === "class") el.className = value;
    else el.setAttribute(key, value === true ? "" : value);
  }
  el.append(...children.flat().filter((c) => c !== null && c !== undefined && c !== false));
  return el;
}

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
  }
}

async function api(method, path, { json, body, contentType } = {}) {
  const headers = {};
  if (state.parentCode) headers["X-Parent-Code"] = state.parentCode;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (contentType) {
    headers["Content-Type"] = contentType;
  }
  const res = await fetch(path, { method, headers, body });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new ApiError(res.status, typeof payload.detail === "string" ? payload.detail : null);
  }
  return res.status === 204 ? null : res.json();
}

async function loadAvatars() {
  if (!state.avatars) state.avatars = await api("GET", "/api/avatars");
  return state.avatars;
}

function presetById(id) {
  return state.avatars.presets.find((p) => p.id === id);
}

function render(...nodes) {
  document.getElementById("app").replaceChildren(...nodes);
}

function avatar(child, { size = "md", photoUrl } = {}) {
  const url = photoUrl ?? child.photo_url;
  let content;
  if (child.avatar_type === "photo" && url) {
    content = h("img", { src: url, alt: "" });
  } else if (child.avatar_type === "preset" && presetById(child.preset)) {
    content = presetById(child.preset).emoji;
  } else {
    content = (child.name || "?").charAt(0).toUpperCase();
  }
  return h("div", { class: `avatar avatar--${size}`, style: `--child-color: ${child.color || "#ccc"}` }, content);
}

function errorMessage(err) {
  if (!(err instanceof ApiError)) return "No se ha podido conectar con la app.";
  if (err.status === 401) return "El código de padres no es válido.";
  if (err.status === 409) return "Ese color ya lo tiene otro niño.";
  if (err.status === 413) return "La foto es demasiado grande (máximo 5 MB).";
  if (err.status === 415 || err.status === 422) return "Revisa los datos: hay algo que no es válido.";
  return "Algo ha fallado. Inténtalo otra vez.";
}

// ---------- views ----------

async function viewHome() {
  state.parentCode = null;
  const [children] = await Promise.all([api("GET", "/api/children"), loadAvatars()]);
  const grid = children.length
    ? h("section", { class: "children" },
        children.map((child) =>
          h("button", { class: "child-card", type: "button" },
            avatar(child, { size: "lg" }),
            h("span", { class: "child-card__name" }, child.name))))
    : h("p", { class: "empty" }, "Todavía no hay niños.");

  render(
    h("main", { class: "home" },
      h("a", { class: "corner-button", href: "#/parents", "aria-label": "Zona de padres" }, "⚙️"),
      h("h1", { class: "home__title" }, "¿Quién eres?"),
      grid));
}

function viewParentsLock(target) {
  const input = h("input", {
    type: "password", inputmode: "numeric", autocomplete: "off",
    class: "code-input", "aria-label": "Código de padres", required: true,
  });
  const error = h("p", { class: "form-error", role: "alert" });

  async function onsubmit(event) {
    event.preventDefault();
    try {
      await api("POST", "/api/parents/unlock", { json: { code: input.value } });
      state.parentCode = input.value;
      if (location.hash === target) route();
      else location.hash = target;
    } catch (err) {
      error.textContent = errorMessage(err);
      input.value = "";
      input.focus();
    }
  }

  render(
    h("main", { class: "page page--center" },
      h("a", { class: "corner-button", href: "#/", "aria-label": "Inicio" }, "🏠"),
      h("form", { class: "lock", onsubmit },
        h("h1", {}, "Zona de padres"),
        h("label", {}, "Código", input),
        error,
        h("button", { class: "btn btn--primary", type: "submit" }, "Entrar"))));
  input.focus();
}

function parentsHeader(title, back) {
  return h("header", { class: "page__header" },
    h("a", { class: "btn btn--ghost", href: back.href }, back.label),
    h("h1", {}, title));
}

function viewConfigIndex() {
  const sections = [
    { href: "#/parents/config/children", icon: "🧒", label: "Niños" },
    { href: "#/parents/config/code", icon: "🔒", label: "Código de padres" },
  ];
  render(
    h("main", { class: "page" },
      parentsHeader("Configurar", { href: "#/", label: "🏠 Salir" }),
      h("ul", { class: "rows" },
        sections.map(({ href, icon, label }) =>
          h("li", {},
            h("a", { class: "row row--link", href },
              h("span", { class: "row__icon" }, icon),
              h("span", { class: "row__name" }, label),
              h("span", { class: "row__chevron" }, "›")))))));
}

function viewChangeCode() {
  const codeInput = () => h("input", {
    type: "password", inputmode: "numeric", autocomplete: "off",
    class: "code-input", minlength: 4, maxlength: 8, required: true,
  });
  const newCode = codeInput();
  const repeatCode = codeInput();
  const error = h("p", { class: "form-error", role: "alert" });
  const done = h("p", { class: "form-success", role: "status" });

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = "";
    done.textContent = "";
    if (!/^\d{4,8}$/.test(newCode.value)) {
      error.textContent = "El código tiene que tener entre 4 y 8 números.";
      return;
    }
    if (newCode.value !== repeatCode.value) {
      error.textContent = "Los dos códigos no coinciden.";
      return;
    }
    try {
      await api("PUT", "/api/parents/code", { json: { code: newCode.value } });
      state.parentCode = newCode.value;
      newCode.value = "";
      repeatCode.value = "";
      done.textContent = "Código cambiado. Úsalo la próxima vez que entres.";
    } catch (err) {
      error.textContent = errorMessage(err);
    }
  }

  render(
    h("main", { class: "page" },
      parentsHeader("Código de padres", { href: "#/parents/config", label: "← Configurar" }),
      h("form", { class: "lock lock--left", onsubmit },
        h("label", {}, "Código nuevo (4 a 8 números)", newCode),
        h("label", {}, "Repite el código nuevo", repeatCode),
        error,
        done,
        h("button", { class: "btn btn--primary", type: "submit" }, "Cambiar código"))));
  newCode.focus();
}

async function viewChildrenList() {
  const [children] = await Promise.all([api("GET", "/api/children"), loadAvatars()]);

  function row(child) {
    const actions = h("div", { class: "row__actions" });

    function showDefault() {
      actions.replaceChildren(
        h("a", { class: "btn", href: `#/parents/config/children/${child.id}` }, "Editar"),
        h("button", { class: "btn btn--danger", type: "button", onclick: showConfirm }, "Borrar"));
    }

    function showConfirm() {
      actions.replaceChildren(
        h("span", { class: "row__confirm" }, `¿Borrar a ${child.name}?`),
        h("button", { class: "btn btn--danger", type: "button", onclick: remove }, "Sí, borrar"),
        h("button", { class: "btn", type: "button", onclick: showDefault }, "Cancelar"));
    }

    async function remove() {
      try {
        await api("DELETE", `/api/children/${child.id}`);
        viewChildrenList();
      } catch (err) {
        actions.prepend(h("span", { class: "form-error" }, errorMessage(err)));
      }
    }

    showDefault();
    return h("li", { class: "row" },
      avatar(child),
      h("span", { class: "row__name" }, child.name),
      actions);
  }

  render(
    h("main", { class: "page" },
      parentsHeader("Niños", { href: "#/parents/config", label: "← Configurar" }),
      children.length
        ? h("ul", { class: "rows" }, children.map(row))
        : h("p", { class: "empty" }, "Todavía no hay niños. Añade el primero."),
      h("a", { class: "btn btn--primary btn--block", href: "#/parents/config/children/new" },
        "+ Añadir niño"),
      h("p", { class: "note" },
        "Borrar un niño no borra su historial de estrellas.")));
}

async function viewChildForm(childId) {
  const [children] = await Promise.all([api("GET", "/api/children"), loadAvatars()]);
  const existing = childId ? children.find((c) => c.id === childId) : null;
  if (childId && !existing) {
    location.hash = "#/parents/config/children";
    return;
  }

  const usedColors = new Set(children.filter((c) => c.id !== childId).map((c) => c.color));
  const form = {
    name: existing?.name ?? "",
    avatar_type: existing?.avatar_type ?? null,
    preset: existing?.preset ?? null,
    color: existing?.color ?? null,
    photoFile: null,
    photoPreview: null,
  };
  let pickerOpen = !existing;

  const nameInput = h("input", {
    type: "text", maxlength: 30, required: true, value: form.name,
    oninput: (e) => { form.name = e.target.value; refreshPreview(); },
  });
  const preview = h("div", { class: "avatar-edit" });
  const picker = h("div", { class: "picker" });
  const error = h("p", { class: "form-error", role: "alert" });

  function refreshPreview() {
    preview.replaceChildren(
      avatar(
        { ...form, name: form.name, photo_url: existing?.photo_url },
        { size: "lg", photoUrl: form.photoPreview ?? undefined }),
      h("button", {
        class: "avatar-edit__pencil", type: "button", "aria-label": "Cambiar avatar",
        onclick: () => { pickerOpen = !pickerOpen; refreshPicker(); },
      }, "✏️"));
  }

  function choosePreset(preset) {
    Object.assign(form, { avatar_type: "preset", preset: preset.id, color: preset.color });
    form.photoFile = null;
    form.photoPreview = null;
    refreshAll();
  }

  function choosePhoto(file) {
    if (!file) return;
    if (!PHOTO_TYPES.includes(file.type)) {
      error.textContent = "La foto tiene que ser JPG, PNG o WebP.";
      return;
    }
    error.textContent = "";
    if (form.photoPreview) URL.revokeObjectURL(form.photoPreview);
    form.avatar_type = "photo";
    form.preset = null;
    form.photoFile = file;
    form.photoPreview = URL.createObjectURL(file);
    if (usedColors.has(form.color)) form.color = null;
    refreshAll();
  }

  function chooseColor(color) {
    form.color = color;
    refreshAll();
  }

  function refreshPicker() {
    if (!pickerOpen) {
      picker.replaceChildren();
      return;
    }
    const presets = state.avatars.presets.map((preset) => {
      const taken = usedColors.has(preset.color);
      const selected = form.avatar_type === "preset" && form.preset === preset.id;
      return h("button", {
        type: "button",
        class: `choice${selected ? " choice--selected" : ""}`,
        disabled: taken,
        title: taken ? `${preset.label} (color en uso)` : preset.label,
        onclick: () => choosePreset(preset),
      }, h("span", { class: "avatar avatar--md", style: `--child-color: ${preset.color}` }, preset.emoji),
         h("span", { class: "choice__label" }, preset.label));
    });

    const fileInput = h("input", {
      type: "file", accept: PHOTO_TYPES.join(","), hidden: true,
      onchange: (e) => choosePhoto(e.target.files[0]),
    });
    const photoButton = h("button", {
      type: "button",
      class: `choice${form.avatar_type === "photo" ? " choice--selected" : ""}`,
      onclick: () => fileInput.click(),
    }, h("span", { class: "avatar avatar--md avatar--photo-choice" }, "📷"),
       h("span", { class: "choice__label" }, "Foto propia"), fileInput);

    const sections = [
      h("h2", {}, "Elige un avatar"),
      h("div", { class: "choices" }, presets, photoButton),
    ];

    if (form.avatar_type === "photo") {
      sections.push(
        h("h2", {}, "Elige un color"),
        h("div", { class: "swatches" },
          state.avatars.palette.map(({ color, label }) => {
            const taken = usedColors.has(color);
            return h("button", {
              type: "button",
              class: `swatch${form.color === color ? " swatch--selected" : ""}`,
              style: `--swatch: ${color}`,
              disabled: taken,
              title: taken ? `${label} (en uso)` : label,
              "aria-label": label,
              onclick: () => chooseColor(color),
            });
          })));
    }
    picker.replaceChildren(...sections);
  }

  function refreshAll() {
    error.textContent = "";
    refreshPreview();
    refreshPicker();
  }

  function validate() {
    if (!form.name.trim()) return "Escribe el nombre.";
    if (!form.avatar_type) return "Elige un avatar.";
    if (form.avatar_type === "photo" && !form.photoFile && !existing?.photo_url) {
      return "Elige una foto.";
    }
    if (!form.color) return "Elige un color.";
    return null;
  }

  // Set after the first successful save, so a retry (e.g. failed photo upload)
  // updates the same child instead of creating a duplicate.
  let savedId = existing?.id ?? null;

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = validate() ?? "";
    if (error.textContent) return;

    const payload = {
      name: form.name,
      avatar_type: form.avatar_type,
      preset: form.preset,
      color: form.color,
    };
    try {
      const saved = savedId
        ? await api("PUT", `/api/children/${savedId}`, { json: payload })
        : await api("POST", "/api/children", { json: payload });
      savedId = saved.id;
      if (form.photoFile) {
        await api("PUT", `/api/children/${saved.id}/photo`, {
          body: form.photoFile, contentType: form.photoFile.type,
        });
      }
      location.hash = "#/parents/config/children";
    } catch (err) {
      error.textContent = errorMessage(err);
    }
  }

  refreshAll();
  render(
    h("main", { class: "page" },
      parentsHeader(existing ? `Editar a ${existing.name}` : "Añadir niño",
        { href: "#/parents/config/children", label: "← Niños" }),
      h("form", { class: "child-form", onsubmit },
        preview,
        h("label", {}, "Nombre", nameInput),
        picker,
        error,
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: "#/parents/config/children" }, "Cancelar"),
          h("button", { class: "btn btn--primary", type: "submit" }, "Guardar")))));
  if (!existing) nameInput.focus();
}

// ---------- router ----------

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
    if (parentsOnly && !state.parentCode) return viewParentsLock(hash);
    try {
      await view(match);
    } catch (err) {
      render(h("main", { class: "page page--center" },
        h("p", { class: "form-error" }, errorMessage(err)),
        h("a", { class: "btn", href: "#/" }, "Volver al inicio")));
    }
    return;
  }
  location.hash = "#/";
}

window.addEventListener("hashchange", route);
document.addEventListener("DOMContentLoaded", route);
