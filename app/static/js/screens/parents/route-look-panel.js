// Ajustes → La ruta de los niños (prueba-ruta-rueda.html): the route as a wheel or a line,
// and how the wheel turns and looks. Beside the options, the first child's route of today,
// in small and live (it turns), changing as they are tapped. Saved on the spot.
import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { panel } from "../../components/panel.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { routeView } from "../child/route.js";
import { saveSettings } from "./settings-parts.js";

export async function routeLookPanel({ look: saved, status, onReset }) {
  const children = await api("GET", "api/children");
  const child = children[0];
  const day = child ? await api("GET", `api/children/${child.id}/today`).catch(() => null) : null;
  const look = { ...saved };
  const options = h("div", { class: "stack stack--tight" });
  const preview = h("div", {});
  const resetBox = h("div", {});

  const change = (changes) => {
    Object.assign(look, changes);
    draw();
    saveSettings(status, { route: { ...look } });
  };
  const choice = (label, key, choices) => h("div", { class: "setting" },
    h("span", { class: "setting__label" }, label),
    h("div", { class: "tabs tabs--wrap" }, choices.map(([value, text]) => h("button", {
      type: "button", class: `tab${look[key] === value ? " tab--on" : ""}`, "aria-pressed": String(look[key] === value),
      onclick: () => look[key] !== value && change({ [key]: value }),
    }, look[key] === value && icon("check"), text))));
  const check = (label, key) => h("label", { class: "toggle" },
    h("input", { type: "checkbox", checked: look[key], onchange: (e) => change({ [key]: e.target.checked }) }),
    label);

  function draw() {
    const wheel = look.shape === "wheel";
    // replaceChildren, unlike h(), takes neither lists nor false: cleaned first.
    const children = (...items) => items.flat().filter(Boolean);
    options.replaceChildren(...children(
      choice(t.settings.routeShape, "shape", t.settings.routeShapes),
      !wheel && h("p", { class: "hint" }, t.settings.routeLineHint),
      wheel && choice(t.settings.routeJoint, "joint", t.settings.routeJoints),
      wheel && check(t.settings.routeGrey, "grey"),
      wheel && choice(t.settings.routeWidth, "width", t.settings.routeWidths),
      wheel && choice(t.settings.routeSpacing, "spacing", t.settings.routeSpacings),
      wheel && choice(t.settings.routeInertia, "inertia", t.settings.routeInertias),
      wheel && choice(t.settings.routeDepth, "depth", t.settings.routeDepths),
      wheel && choice(t.settings.routeTick, "tick", t.settings.routeTicks),
      wheel && choice(t.settings.routeEnds, "ends", t.settings.routeEndsChoices),
      choice(t.settings.routeVeil, "veil", t.settings.routeVeils),
      resetBox));
    preview.replaceChildren(...children(day && day.missions.length
      ? [
          h("p", { class: "section-title" }, t.settings.routePreview(day.child.name)),
          // The child's own screen in small: its colour, its background and its route.
          h("div", {
            class: `route-preview child-screen child-screen--veil-${look.veil}`,
            style: `--child-color: ${day.colors.color}; --child-soft: ${day.colors.soft}; --child-strong: ${day.colors.strong}; --on-child: ${day.colors.on}`,
          },
            h("div", { class: "child-scene", "aria-hidden": "true" },
              day.background_url && h("img", { class: "child-scene__picture", src: day.background_url, alt: "" }),
              h("div", { class: "child-scene__veil" })),
            routeView({ ...day, route_look: { ...look } }, LOOK_ONLY)),
        ]
      : h("p", { class: "hint" }, t.settings.routeNoChild)));
  }

  const showReset = () => resetBox.replaceChildren(h("button", {
    type: "button", class: "btn", onclick: () => resetBox.replaceChildren(confirmBar({
      message: t.settings.routeResetConfirm, detail: t.settings.routeResetDetail, confirmLabel: t.settings.routeResetYes,
      onCancel: showReset,
      onConfirm: async () => { await api("POST", "api/settings/route/reset"); await onReset(); },
    })),
  }, t.settings.routeReset));
  showReset();
  draw();

  return panel(t.settings.routeTitle, h("div", { class: "home-look-panel" }, options, preview));
}

// In the preview the route turns, but tapping a mission opens nothing.
const nothing = () => {};
const LOOK_ONLY = { onOpen: nothing, onLocked: nothing, onHold: nothing, onPrize: nothing, onPrizeLocked: nothing };
