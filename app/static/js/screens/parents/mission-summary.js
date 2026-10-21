import { t } from "../../texts.js";

const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

export function daysText(days) {
  if (days.length === WEEKDAYS.length) return t.childMissions.everyDay;
  return WEEKDAYS.filter((d) => days.includes(d)).map((d) => t.days[d]).join(" ");
}

export function scheduleText(schedule) {
  if (!schedule) return t.childMissions.alwaysOpen;
  return schedule.end
    ? t.childMissions.range(schedule.start, schedule.end)
    : t.childMissions.from(schedule.start);
}

// "L M X J V · 07:00–08:15 · 6 pasos"
export function missionSummary(mission) {
  return [daysText(mission.days), scheduleText(mission.schedule), t.childMissions.steps(mission.steps.length)]
    .join(" · ");
}

export { WEEKDAYS };
