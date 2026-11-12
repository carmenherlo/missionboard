// Configurar → Apariencia (12/11; was Ajustes, ajustes.html): how the app looks, a page for
// each screen: the home, the missions' way, and the seasons with their backgrounds.
// The stars went to Recompensas → Estrellas, and when the day starts to El día de los niños → El día.
// Saved on the spot in config.yaml (settings), like the rest of the parents' zone.
import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { timeInput } from "../../components/time-input.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { homeLookPanel } from "./home-look-panel.js";
import { routeLookPanel } from "./route-look-panel.js";
import { loadSettings, saveSettings } from "./settings-parts.js";
import { icon } from "../../icons.js";

const MOMENTS = ["manana", "dia", "tarde", "noche"];
const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

const seasonName = (season) => t.settings.seasons[season.name] ?? season.name;

// When each background shows: from its time until the next one starts (as current_moment
// in app/today/service.py); the night goes on past midnight until the morning.
const until = (season, moment) => season[MOMENTS[(MOMENTS.indexOf(moment) + 1) % MOMENTS.length]];

// The same rules as the server (Settings), said in words before saving.
function problem(seasons) {
  if (new Set(seasons.map((s) => s.start)).size !== seasons.length) return t.settings.sameStart;
  for (const season of seasons) {
    const times = MOMENTS.map((moment) => season[moment]);
    if (times.some((time, i) => i > 0 && time <= times[i - 1])) return t.settings.outOfOrder(seasonName(season));
  }
  return null;
}

export async function viewSeasons() {
  const { settings, now } = await loadSettings();
  const status = saveStatus();
  const seasons = settings.seasons.map((season) => ({ ...season }));
  const redraws = [];

  function saveSeasons() {
    redraws.forEach((redraw) => redraw());
    const wrong = problem(seasons);
    if (wrong) return status.fail(wrong);
    // In order of their start date, as the app reads them (a date moved past the next one).
    const sorted = [...seasons].sort((a, b) => a.start.localeCompare(b.start));
    saveSettings(status, { seasons: sorted });
  }

  function seasonCard(season) {
    const shots = h("div", { class: "season__shots" });
    const isNow = season.name === now.season;
    // Under each background, the time it starts; the time it ends follows the next one.
    const ends = {};
    shots.replaceChildren(...MOMENTS.map((moment) =>
      h("figure", { class: `season__shot${isNow && moment === now.moment ? " season__shot--now" : ""}` },
        h("img", { src: `static/backgrounds/${season.name}/${moment}.webp`, alt: "", loading: "lazy" }),
        h("figcaption", {}, h("b", {}, t.settings.moments[moment])),
        timeInput({
          class: "season__time", value: season[moment], required: true,
          label: `${seasonName(season)} · ${t.settings.moments[moment]} · ${t.settings.from}`,
          onchange: (e) => { if (!e.target.value) return; season[moment] = e.target.value; saveSeasons(); },
        }),
        ends[moment] = h("span", { class: "season__until" }))));
    redraws.push(() => MOMENTS.forEach((moment) => {
      ends[moment].textContent = t.settings.until(until(season, moment));
    }));

    const [month, day] = season.start.split("-").map(Number);
    const daySelect = h("select", { "aria-label": `${seasonName(season)} · ${t.settings.day}` });
    const fillDays = (chosen) => {
      const days = DAYS_IN_MONTH[Number(monthSelect.value) - 1];
      daySelect.replaceChildren(...Array.from({ length: days }, (_, i) =>
        h("option", { value: i + 1, selected: i + 1 === Math.min(chosen, days) }, String(i + 1))));
    };
    const changeStart = () => {
      fillDays(Number(daySelect.value));
      season.start = `${String(monthSelect.value).padStart(2, "0")}-${String(daySelect.value).padStart(2, "0")}`;
      saveSeasons();
    };
    const monthSelect = h("select", { "aria-label": `${seasonName(season)} · ${t.settings.month}`, onchange: changeStart },
      t.settings.months.map((name, i) => h("option", { value: i + 1, selected: i + 1 === month }, name)));
    fillDays(day);
    daySelect.onchange = changeStart;

    return h("div", { class: `season${isNow ? " season--now" : ""}` },
      h("div", { class: "season__head" },
        h("span", { class: "season__name" }, seasonName(season), " ", isNow && h("span", { class: "pill" }, t.settings.now)),
        h("span", { class: "season__field" }, t.settings.starts, daySelect, monthSelect)),
      shots);
  }

  const resetBox = h("div", {});
  const showReset = () => resetBox.replaceChildren(
    h("button", { type: "button", class: "btn", onclick: () => resetBox.replaceChildren(confirmBar({
      message: t.settings.resetConfirm, detail: t.settings.resetDetail, confirmLabel: t.settings.resetYes,
      onCancel: showReset,
      onConfirm: async () => { await api("POST", "api/settings/seasons/reset"); await viewSeasons(); },
    })) }, t.settings.reset));
  showReset();

  const cards = seasons.map(seasonCard);
  redraws.forEach((redraw) => redraw());

  render(
    pageHeader(t.appearance.seasons, status),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        panel(t.settings.seasonsTitle,
          h("div", { class: "stack" },
            h("p", { class: "hint" }, t.settings.seasonsHint),
            ...cards,
            resetBox)),
        h("p", { class: "note" }, t.settings.fileHint))));
}

const APPEARANCE = "#/parents/config/appearance";
const pageHeader = (title, status) => parentsHeader(h("span", { class: "title-line" }, title, status.element),
  { href: APPEARANCE, label: t.appearance.title });

// Apariencia: one row for each screen (more will come).
export function viewAppearance() {
  const pages = [["home", "home", t.appearance.home], ["missions", "missions", t.appearance.missions],
    ["seasons", "sun", t.appearance.seasons]];
  render(
    parentsHeader(t.appearance.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("p", { class: "hint" }, t.appearance.hint),
      h("ul", { class: "rows" }, pages.map(([path, iconName, label]) => h("li", {},
        h("a", { class: "row row--link", href: `${APPEARANCE}/${path}` },
          h("span", { class: "row__icon" }, icon(iconName)),
          h("span", { class: "row__name" }, label),
          h("span", { class: "row__chevron" }, icon("next"))))))));
}

// Apariencia → Pantalla de inicio.
export async function viewAppearanceHome() {
  const { settings, now } = await loadSettings();
  const status = saveStatus();
  const look = await homeLookPanel({ look: settings.home, picture: now.background_url, status, onReset: viewAppearanceHome });
  render(pageHeader(t.appearance.home, status), h("main", { class: "page" }, look));
}

// Apariencia → Camino de misiones.
export async function viewAppearanceMissions() {
  const { settings } = await loadSettings();
  const status = saveStatus();
  const look = await routeLookPanel({ look: settings.route, status, onReset: viewAppearanceMissions });
  render(pageHeader(t.appearance.missions, status), h("main", { class: "page" }, look));
}
