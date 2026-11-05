import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

export function daysText(days) {
  if (days.length === WEEKDAYS.length) return t.childMissions.everyDay;
  return WEEKDAYS.filter((d) => days.includes(d)).map((d) => t.days[d]).join(" ");
}

// The active days in words: "De lunes a viernes", "lunes, miércoles y viernes"…
export function daysLongText(days) {
  const sorted = WEEKDAYS.filter((d) => days.includes(d));
  const key = sorted.join();
  if (key === WEEKDAYS.join()) return t.missionEdit.daysSummary.all;
  if (key === WEEKDAYS.slice(0, 5).join()) return t.missionEdit.daysSummary.weekdays;
  if (key === WEEKDAYS.slice(5).join()) return t.missionEdit.daysSummary.weekend;
  const names = sorted.map((d) => t.dayNames[d]);
  const text = names.length > 1 ? `${names.slice(0, -1).join(", ")} y ${names.at(-1)}` : names[0];
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function scheduleText(schedule) {
  if (!schedule) return t.childMissions.alwaysOpen;
  return schedule.end
    ? t.childMissions.range(schedule.start, schedule.end)
    : t.childMissions.from(schedule.start);
}

// "en la rutina Mañana · 6:35–7:30" (rutinas-8): its days and hours are the routine's.
export function routineText(routine) {
  return t.childMissions.inRoutine(routine.name, routineHours(routine));
}

// "6:45–7:40" (as the routines say their times), or "se lanza a mano".
export function routineHours(routine) {
  const short = (time) => time.replace(/^0/, "");
  return routine.manual ? t.childMissions.byHand : t.childMissions.range(short(routine.start), short(routine.end));
}

// [L M X J V] [07:00–08:15] [6 pasos]; in a routine: [🌅 en la rutina Mañana · 6:35–7:30] [6 pasos]
export function missionPills(mission) {
  if (mission.routines?.length) {
    return [
      ...mission.routines.map((r) => h("span", { class: "pill pill--routine" },
        h("img", { src: r.image_url, alt: "" }), routineText(r))),
      h("span", { class: "pill pill--muted" }, t.childMissions.steps(mission.steps.length)),
    ];
  }
  return [
    h("span", { class: "pill" }, daysText(mission.days)),
    mission.schedule
      ? h("span", { class: "pill" }, icon("clock"), scheduleText(mission.schedule))
      : h("span", { class: "pill pill--muted" }, scheduleText(mission.schedule)),
    h("span", { class: "pill pill--muted" }, t.childMissions.steps(mission.steps.length)),
  ];
}

export { WEEKDAYS };
