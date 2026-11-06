import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

export function daysText(days) {
  if (days.length === WEEKDAYS.length) return t.missions.everyDay;
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
  if (!schedule) return t.missions.alwaysOpen;
  return schedule.end ? t.missions.range(schedule.start, schedule.end) : t.missions.from(schedule.start);
}

// [L M X J V] [7:00–9:00] [6 tareas · 14 pasos]
export function missionPills(mission) {
  const steps = mission.tasks.reduce((sum, task) => sum + task.steps.length, 0);
  const size = [t.missions.tasks(mission.tasks.length), steps > 0 && t.missions.steps(steps)].filter(Boolean).join(" · ");
  const { routine } = mission;
  return [
    routine && h("span", { class: "pill pill--routine" }, mission.image_url && h("img", { src: mission.image_url, alt: "" }),
      routine.manual ? t.missions.routineByHand
        : routine.anchor === "end" ? t.missions.routineEnds(routine.end.replace(/^0/, ""))
        : t.missions.routineStarts(routine.start.replace(/^0/, ""))),
    h("span", { class: "pill" }, daysText(mission.days)),
    mission.schedule
      ? h("span", { class: "pill" }, icon("clock"), scheduleText(mission.schedule))
      : h("span", { class: "pill pill--muted" }, scheduleText(mission.schedule)),
    h("span", { class: "pill pill--muted" }, size),
  ];
}

export { WEEKDAYS };
