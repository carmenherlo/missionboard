import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import { capital, minuteOf, shortTime } from "../../routine/words.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { routineError } from "./routine-edit.js";
import { length } from "./songs-list.js";

const ROUTINES_HREF = "#/parents/config/routines";

// The songs of a routine (rutinas-4, section 3): a lane beside its cards, like two
// Scratch scripts side by side. Each song is a bar from the card where it starts to
// the card where it ends; one at a time (one Música channel).

// The cards a song can start or end at, in order: the alarm, each part, the goal.
export function cardsOf(routine) {
  const timed = !routine.manual;
  return [
    ...(timed && routine.alarm ? [{ id: "alarm", name: t.routineMusic.alarmCard, from: routine.wake, to: routine.wake }] : []),
    ...routine.parts.map((p) => ({ id: p.id, name: p.name, from: p.start, to: p.end })),
    ...(timed && routine.goal ? [{ id: "goal", name: t.routineMusic.goalCard, from: routine.goal.at, to: routine.goal.at }] : []),
  ].map((card) => ({ ...card, label: capital(card.name) }));
}

// The other song this one would play at the same time as, if any.
export function clashWith(routine, music) {
  const order = cardsOf(routine).map((c) => c.id);
  const span = (m) => [order.indexOf(m.start), order.indexOf(m.until ?? m.start)];
  const [from, to] = span(music);
  return routine.music.find((other) => {
    if (other.id === music.id) return false;
    const [a, b] = span(other);
    return from <= b && a <= to;
  });
}

// The lane, beside `cardsBox` (whose cards carry data-card: "alarm", a part's id, "goal").
export function songLane(routineId) {
  const element = h("div", { class: "song-lane", "aria-label": t.routineMusic.lane });
  let last = null;

  function draw(routine, songs, cardsBox) {
    last = { routine, songs, cardsBox };
    const byId = Object.fromEntries(songs.map((s) => [s.id, s]));
    const cards = Object.fromEntries(cardsOf(routine).map((c) => [c.id, c]));
    const top = cardsBox.getBoundingClientRect().top;
    const place = (id) => cardsBox.querySelector(`[data-card="${id}"]`)?.getBoundingClientRect();
    element.replaceChildren(...(routine.music.length ? [] : [h("span", { class: "song-lane__empty" }, t.routineMusic.laneEmpty)]),
      ...routine.music.map((music) => {
        const song = byId[music.song];
        const from = place(music.start);
        const to = place(music.until ?? music.start);
        if (!song || !from || !to) return null;
        const detail = [
          music.start === "alarm" && t.routineMusic.insteadOfAlarm,
          music.until ? t.routineMusic.until(cards[music.until]?.name ?? "") : t.routineMusic.once(length(song.seconds)),
        ].filter(Boolean).join(" · ");
        return h("a", {
          class: `song-bar${music.until ? "" : " song-bar--once"}`,
          href: `${ROUTINES_HREF}/${routineId}/music/${music.id}`,
          style: `top: ${from.top - top}px; height: ${to.bottom - from.top}px`,
        }, h("span", { class: "song-bar__name" }, icon("music"), song.name), h("span", { class: "song-bar__detail" }, detail));
      }).filter(Boolean));
  }

  // The cards change size (a new part, the window): the bars follow them.
  const observer = new ResizeObserver(() => last && draw(last.routine, last.songs, last.cardsBox));
  return {
    element,
    draw: (routine, songs, cardsBox) => {
      observer.disconnect();
      observer.observe(cardsBox);
      requestAnimationFrame(() => draw(routine, songs, cardsBox)); // once the cards are laid out
    },
  };
}

// Under "Añadir parte": a song and where it starts (it plays once; its screen makes it longer).
export function addSongForm(routineId, { save, status }) {
  const element = h("div", {});
  function draw(routine, songs) {
    if (!songs.length) {
      element.replaceChildren(h("p", { class: "hint" }, t.routineMusic.noSongs, " ",
        h("a", { href: `${ROUTINES_HREF}/songs` }, t.routineMusic.toLibrary)));
      return;
    }
    const song = h("select", { "aria-label": t.routineMusic.panelSong }, songs.map((s) => h("option", { value: s.id }, s.name)));
    const start = h("select", { "aria-label": t.routineMusic.startsWith },
      cardsOf(routine).map((c) => h("option", { value: c.id }, `${t.routineMusic.startsWith}: ${c.label}`)));
    element.replaceChildren(h("div", { class: "form-actions form-actions--start" }, song, start,
      h("button", {
        type: "button", class: "btn",
        onclick: () => {
          const music = { id: null, song: song.value, start: start.value, until: null };
          const other = clashWith(routine, music);
          if (other) {
            status.fail(t.routineMusic.clash(songs.find((s) => s.id === other.song)?.name ?? ""));
            return;
          }
          save(api("POST", `/api/routines/${routineId}/music`, { json: { song: song.value, start: start.value } }))
            .catch(() => {});
        },
      }, icon("plus"), t.routineMusic.addSong)));
  }
  return { element, draw };
}

// A song of a routine (rutinas-4, screen 5), like Editar parte: saved on the spot.
export async function viewRoutineMusic(routineId, musicId) {
  const url = `/api/routines/${routineId}`;
  const routineHref = `${ROUTINES_HREF}/${routineId}`;
  let [routine, songs] = await Promise.all([api("GET", url), api("GET", "/api/songs")]);
  const music = () => routine.music.find((m) => m.id === musicId);
  if (!music()) {
    location.replace(routineHref);
    return;
  }
  const status = saveStatus();
  const title = h("span", {});
  const songBox = h("div", { class: "stack stack--tight" });
  const whenBox = h("div", { class: "stack stack--tight" });
  let listening = null;

  function change(fields) {
    const next = { ...music(), ...fields };
    const other = clashWith(routine, next);
    if (other) {
      status.fail(t.routineMusic.clash(songs.find((s) => s.id === other.song)?.name ?? ""));
      draw();
      return;
    }
    status.track(api("PATCH", `${url}/music/${musicId}`, { json: fields })).then((updated) => {
      routine = updated;
      draw();
    }).catch((err) => {
      status.fail(routineError(err));
      draw();
    });
  }

  function draw() {
    const m = music();
    const song = songs.find((s) => s.id === m.song);
    title.textContent = song?.name ?? "";
    const cards = cardsOf(routine);
    const startAt = cards.findIndex((c) => c.id === m.start);
    songBox.replaceChildren(
      h("div", { class: "form-actions form-actions--start" },
        h("select", { "aria-label": t.routineMusic.panelSong, onchange: (e) => change({ song: e.target.value }) },
          songs.map((s) => h("option", { value: s.id, selected: s.id === m.song }, s.name))),
        h("button", {
          type: "button", class: "btn",
          onclick: () => {
            listening?.pause();
            listening = listening ? null : new Audio(song.url);
            listening?.play().catch(() => {});
          },
        }, `▶ ${t.songs.listen}`)),
      song && h("p", { class: "hint" }, t.routineMusic.lasts(length(song.seconds))));
    const ending = m.until !== null;
    whenBox.replaceChildren(...[
      h("label", {}, t.routineMusic.startsWith,
        h("select", { onchange: (e) => change({ start: e.target.value }) },
          cards.map((c) => h("option", { value: c.id, selected: c.id === m.start }, cardText(c, routine))))),
      h("div", { class: "field" }, h("span", { class: "field__label" }, t.routineMusic.ends),
        h("div", { class: "tabs" },
          [[false, t.routineMusic.endsWithSong], [true, t.routineMusic.endsWithPart]].map(([value, label]) =>
            h("button", {
              type: "button", class: `tab${ending === value ? " tab--on" : ""}`, "aria-pressed": String(ending === value),
              onclick: () => ending !== value && change({ until: value ? cards[startAt].id === "alarm" ? cards[startAt + 1]?.id : m.start : null }),
            }, ending === value && icon("check"), label))),
        ending && h("select", { "aria-label": t.routineMusic.ends, onchange: (e) => change({ until: e.target.value }) },
          cards.slice(startAt).filter((c) => c.id !== "alarm").map((c) =>
            h("option", { value: c.id, selected: c.id === m.until }, cardText(c, routine, true))))),
      song && h("p", { class: "hint" }, hintOf(routine, m, song)),
      m.start === "alarm" && h("p", { class: "hint" }, t.routineMusic.hintAlarm),
    ].filter(Boolean));
  }

  const footer = h("div", { class: "page-footer" });
  function drawFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: confirmRemove }, t.routineMusic.remove),
      h("div", { class: "form-actions" },
        h("button", {
          type: "button", class: "btn",
          onclick: () => {
            const m = music();
            const index = routine.parts.findIndex((p) => p.id === m.start);
            tryRoutine(routineId, m.start === "goal" ? routine.parts.length - 1 : Math.max(0, index));
          },
        }, t.routineMusic.tryFromHere),
        h("a", { class: "btn btn--primary", href: routineHref }, t.common.done)));
  }
  function confirmRemove() {
    footer.replaceChildren(confirmBar({
      message: t.routineMusic.confirmRemove(title.textContent),
      confirmLabel: t.routineMusic.confirmYes,
      onCancel: drawFooter,
      onConfirm: async () => {
        await api("DELETE", `${url}/music/${musicId}`);
        location.hash = routineHref;
      },
    }));
  }

  draw();
  drawFooter();
  render(
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: routineHref, label: routine.name }),
    h("main", { class: "page" },
      h("div", { class: "columns columns--equal" },
        h("div", { class: "stack" }, panel(t.routineMusic.panelSong, songBox)),
        h("div", { class: "stack" }, panel(t.routineMusic.panelWhen, whenBox))),
      footer));
}

// "Vestirse (7:05)": when it starts, or for "hasta", when it ends.
function cardText(card, routine, end = false) {
  if (routine.manual) return card.label;
  const time = end ? card.to : card.from;
  return time ? `${card.label} (${shortTime(minuteOf(time))})` : card.label;
}

function hintOf(routine, music, song) {
  const cards = cardsOf(routine);
  const from = cards.find((c) => c.id === music.start);
  const to = cards.find((c) => c.id === music.until);
  if (routine.manual) {
    return to ? t.routineMusic.hintSpanByHand(from.label, to.label, length(song.seconds))
      : t.routineMusic.hintOnceByHand(from.label, length(song.seconds));
  }
  if (!to) return t.routineMusic.hintOnce(shortTime(minuteOf(from.from)), length(song.seconds));
  const minutes = (minuteOf(to.to) - minuteOf(from.from) + 1440) % 1440;
  return t.routineMusic.hintSpan(shortTime(minuteOf(from.from)), shortTime(minuteOf(to.to)), minutes, length(song.seconds));
}
