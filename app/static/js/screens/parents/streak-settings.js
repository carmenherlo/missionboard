// Configurar → Rachas (rachas.html, 13/11): the week of fuel tanks. On or off, which days
// count and what fills a tank, the day the parents give the prize (it closes the week),
// the prize and, if they want, a smaller one for a few tanks. Saved on the spot.
import { api } from "../../api.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { WEEKDAYS } from "./mission-summary.js";
import { featurePanel, featureSwitch, loadSettings, saveFeatures, saveSettings, settingStepper } from "./settings-parts.js";

export async function viewStreakSettings() {
  const [{ settings, features }, images] = await Promise.all([loadSettings(), api("GET", "api/settings/week-prizes")]);
  const status = saveStatus();
  // Each prize's picture (13/11): what the child sees when the rocket lands. Saved on the spot.
  const picker = (which) => imagePicker({
    initial: images[which],
    onChange: (choice) => saveImageChoice(choice, {
      patch: (ref) => status.track(api("PATCH", `api/settings/week-prizes/${which}`, { json: { image: ref } })),
      upload: (file) => status.track(api("PUT", `api/settings/week-prizes/${which}/photo`, { body: file, contentType: file.type })),
    }).catch(() => {}),
  });
  const [prizePicture, secondPicture] = await Promise.all([picker("prize"), picker("second")]);
  let week = settings.streak_week;
  const save = (changes) => {
    week = { ...week, ...changes };
    saveSettings(status, { streak_week: week });
    draw();
  };

  const tabs = (options, current, onPick) => h("div", { class: "tabs" }, options.map(([value, label]) => h("button", {
    type: "button", class: `tab${current === value ? " tab--on" : ""}`, "aria-pressed": String(current === value),
    onclick: () => onPick(value),
  }, current === value && icon("check"), label)));
  const chip = (day, on, onclick) => h("button", {
    type: "button", class: `chip chip--day${on ? " chip--on" : ""}`, "aria-pressed": String(on),
    "aria-label": t.dayNames[day], title: t.dayNames[day], onclick,
  }, t.days[day]);
  const text = (value, label, onSave) => h("label", {}, label, h("input", {
    type: "text", maxlength: 40, value, placeholder: t.settings.streakPrizePlaceholder,
    onchange: (e) => onSave(e.target.value.trim()),
  }));

  let rule = settings.streak_rule;
  const box = h("div", { class: "stack" });
  function draw() {
    // The week starts the day after the prize day.
    const start = WEEKDAYS[(WEEKDAYS.indexOf(week.prize_day) + 1) % 7];
    const first = [...Array(7).keys()].map((n) => WEEKDAYS[(WEEKDAYS.indexOf(start) + n) % 7]).find((d) => week.days.includes(d));
    box.replaceChildren(
      panel(t.settings.streakDaysTitle,
        h("div", { class: "chips chips--days" }, WEEKDAYS.map((day) => chip(day, week.days.includes(day), () => {
          const days = week.days.includes(day) ? week.days.filter((d) => d !== day) : [...week.days, day];
          if (days.length) save({ days: WEEKDAYS.filter((d) => days.includes(d)) });
        }))),
        h("p", { class: "hint" }, t.settings.streakDaysHint),
        h("p", { class: "setting__label" }, t.settings.streakCounts),
        tabs([["all", t.settings.streakAll], ["any", t.settings.streakAny]], rule, (value) => {
          rule = value;
          saveSettings(status, { streak_rule: value });
          draw();
        }),
        h("p", { class: "hint" }, t.settings.streakHint)),
      panel(t.settings.streakPrizeTitle,
        h("p", { class: "setting__label" }, t.settings.streakPrizeDay),
        h("div", { class: "chips chips--days" }, WEEKDAYS.map((day) => chip(day, week.prize_day === day, () => save({ prize_day: day })))),
        h("p", { class: "hint" }, t.settings.streakWeekIs(t.dayNames[first || start], t.dayNames[week.prize_day])),
        text(week.prize, t.settings.streakPrizeText, (value) => save({ prize: value })),
        h("p", { class: "hint" }, t.settings.streakPrizeHint),
        h("p", { class: "setting__label" }, t.settings.streakPrizeImage),
        prizePicture.element),
      panel(t.settings.streakSecondTitle,
        h("label", { class: "toggle" }, h("input", {
          type: "checkbox", checked: week.second_on, onchange: (e) => save({ second_on: e.target.checked }),
        }), t.settings.streakSecondOn),
        week.second_on && settingStepper({
          label: t.settings.streakSecondMin, value: week.second_min, min: 1, max: 7,
          onChange: (n) => { week = { ...week, second_min: n }; saveSettings(status, { streak_week: week }); },
        }),
        week.second_on && text(week.second, t.settings.streakSecondText, (value) => save({ second: value })),
        week.second_on && h("p", { class: "setting__label" }, t.settings.streakPrizeImage),
        week.second_on && secondPicture.element,
        h("p", { class: "hint" }, t.settings.streakNoneHint)));
  }
  draw();

  render(
    parentsHeader(h("span", { class: "title-line" }, t.config.streaks, status.element), { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        featurePanel(t.settings.streaksTitle, featureSwitch({
          on: features.streaks, onText: t.settings.streaksOn, offText: t.settings.streaksOff,
          onChange: (on) => saveFeatures(status, { streaks: on }),
        })),
        box)));
}
