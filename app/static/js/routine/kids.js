// The routine's kids on a side, with how their mission goes; a tap opens it over the clock.
import { avatar } from "../components/avatar.js";
import { h } from "../dom.js";
import { openMission } from "../screens/child/mission-flow.js";
import { showLanding } from "../screens/child/star-landing.js";
import { missionStyle } from "../screens/child/ring.js";
import { t } from "../texts.js";

export function kids(r) {
  // The kids on a side: their avatar in a ring that closes as their mission goes, and 3/7.
  function renderPeople() {
    const { view, data } = r.showing;
    const signing = r.showing.phaseKey === "check";
    view.people.replaceChildren(...data.people.map((person) => {
      const { mission } = person;
      const { color, soft, strong, on } = person.colors;
      // Checking the missions: whoever has not finished theirs yet beats (effects.css).
      const waiting = signing && mission && !mission.completed;
      return h("li", {},
        h("button", {
          type: "button",
          class: `routine-kid${mission?.completed ? " routine-kid--done" : ""}${waiting ? " routine-kid--waiting" : ""}`,
          // The ring of their avatar in their colour; how their mission goes, in its colour.
          style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}; ${mission ? missionStyle(mission.colors) : ""}`,
          disabled: !mission,
          onclick: () => r.openKid(person),
        },
          avatar(person.child, { size: "md", fx: "halo" }),
          h("span", { class: "routine-kid__name" }, person.child.name),
          h("span", { class: "routine-kid__progress" },
            !mission ? "" : mission.completed ? t.routine.allDone : `${mission.done}/${mission.total}`)),
        data.trial && mission && h("div", { class: "tabs routine-kid__pretend", role: "group", "aria-label": person.child.name },
          [[false, t.routine.pretendNotDone], [true, t.routine.pretendDone]].map(([done, label]) =>
            h("button", {
              type: "button", class: `tab${mission.completed === done ? " tab--on" : ""}`,
              "aria-pressed": String(mission.completed === done), onclick: () => r.pretendAll(person, done),
            }, label))));
    }), data.trial && data.people.some((p) => p.mission) ? h("li", { class: "hint routine__pretend-hint" }, t.routine.pretendHint) : "");
  }

  async function openKid(person) {
    if (r.showing.mission) return;
    r.showing.mission = { close: () => {} };
    const pretend = r.showing.data.trial ? {
      checked: new Set(r.showing.pretend.get(person.child.id)),
      onChange: (checked) => r.setPretend(person.child.id, checked),
    } : null;
    const phase = r.phaseAt(r.now());
    const wasDone = Boolean(person.mission.completed);
    const over = r.showing.view.over;
    r.showing.mission = await openMission(over, person.child.id, person.mission.id, {
      pretend,
      current: phase.kind === "part" ? phase.part.id : null, // the task going on stands out
      onClose: async (day) => {
        if (!r.showing) return;
        // Just done (not in a trial): the star lands on the child's route a moment, then back here.
        const done = day?.missions.find((m) => m.id === person.mission.id)?.state === "done";
        if (!pretend && done && !wasDone) await showLanding(over, day, person.mission.id);
        if (!r.showing) return;
        r.showing.mission = null;
        r.check(); // how the kids go, again
      },
    });
  }

  return { renderPeople, openKid };
}
