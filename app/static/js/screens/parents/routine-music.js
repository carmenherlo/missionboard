import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { sortable } from "../../components/sortable.js";
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

// A card's songs, one after the other: the ones still in the library, their names
// ("Buenos días + ¡A correr!") and how long they last together, in seconds.
export function playlist(music, songs) {
  const list = music.songs.map((id) => songs.find((s) => s.id === id)).filter(Boolean);
  return { list, name: list.map((s) => s.name).join(" + "), seconds: list.reduce((sum, s) => sum + s.seconds, 0) };
}

// The cards a song can start or end at, in order: the alarm, each part, the goal.
export function cardsOf(routine) {
  const timed = !routine.manual;
  return [
    ...(timed && routine.alarm ? [{ id: "alarm", name: t.routineMusic.alarmCard, from: routine.wake, to: routine.wake }] : []),
    ...routine.parts.map((p) => ({ id: p.id, name: p.name, from: p.start, to: p.end })),
    ...(timed && routine.goal ? [{ id: "goal", name: t.routineMusic.goalCard, from: routine.goal.at, to: routine.goal.at }] : []),
  ].map((card) => ({ ...card, label: capital(card.name) }));
}

// Where a song can start: not the alarm (04/11: the alarm rings by itself; to wake up
// to a song, no alarm and the song in the first part), nor the first part if the alarm
// rings right as it starts (both at once).
export const ringsAtFirstPart = (routine) => !routine.manual && routine.alarm && routine.alarm_before === 0;
const songCards = (routine) => cardsOf(routine).filter((c) => c.id !== "alarm"
  && !(ringsAtFirstPart(routine) && c.id === routine.parts[0].id));

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

// Each song wraps the cards it plays over, like Scratch's C blocks ("repetir"): a
// head above the card where it starts (its name, until where, and its pencil) and a
// rail down the side of its cards. The cards carry data-card: "alarm", a part's id, "goal".
export function songWraps(routineId) {
  return function draw(routine, songs, cardsBox) {
    cardsBox.querySelectorAll(".song-head").forEach((head) => head.remove());
    cardsBox.querySelectorAll(".in-song").forEach((card) => card.classList.remove("in-song", "in-song--last"));
    const cards = cardsOf(routine);
    const element = (id) => cardsBox.querySelector(`[data-card="${id}"]`);
    for (const music of routine.music) {
      const song = playlist(music, songs);
      const from = cards.findIndex((c) => c.id === music.start);
      const to = cards.findIndex((c) => c.id === (music.until ?? music.start));
      if (!song.list.length || from < 0 || to < from) continue;
      const wrapped = cards.slice(from, to + 1).map((c) => element(c.id)).filter(Boolean);
      if (!wrapped.length) continue;
      wrapped.forEach((card) => card.classList.add("in-song"));
      wrapped.at(-1).classList.add("in-song--last");
      const detail = [
        music.start === "alarm" && t.routineMusic.insteadOfAlarm,
        music.after_voice && t.routineMusic.afterVoiceTag,
        music.loud && t.routineMusic.loudTag,
        music.until ? t.routineMusic.until(cards[to].name) : t.routineMusic.once(length(song.seconds)),
      ].filter(Boolean).join(" · ");
      const first = wrapped[0];
      const head = h(first.tagName === "LI" ? "li" : "div", { class: "song-head" },
        h("a", { class: "song-head__link", href: `${ROUTINES_HREF}/${routineId}/music/${music.id}` },
          icon("music"), h("span", { class: "song-head__name" }, song.name),
          h("span", { class: "song-head__detail" }, detail),
          h("span", { class: "song-head__edit", "aria-label": t.routineMusic.edit(song.name) }, icon("edit"))));
      first.before(head);
    }
  };
}

// Under "Añadir parte": a song and where it starts (it plays once; its screen makes it longer).
const UPLOAD = "upload"; // the last choice of "Añadir": a new song, uploaded in the library

export function addSongForm(routineId, { save, status }) {
  const element = h("div", {});
  // Only "Añadir" here (05/11): uploading a new one is the last choice of the list, and
  // goes to the library (and back here).
  const library = `${ROUTINES_HREF}/songs?from=${routineId}`;
  function draw(routine, songs) {
    if (!songs.length) {
      element.replaceChildren(h("p", { class: "hint" }, t.routineMusic.noSongs),
        h("a", { class: "btn", href: library }, icon("plus"), t.routineMusic.upload));
      return;
    }
    const song = h("select", {
      "aria-label": t.routineMusic.panelSong,
      onchange: (e) => { if (e.target.value === UPLOAD) location.hash = library; },
    }, songs.map((s) => h("option", { value: s.id }, s.name)), h("option", { value: UPLOAD }, t.routineMusic.uploadOther));
    const start = h("select", { "aria-label": t.routineMusic.startsWith },
      songCards(routine).map((c) => h("option", { value: c.id }, `${t.routineMusic.startsWith}: ${c.label}`)));
    element.replaceChildren(h("div", { class: "form-actions form-actions--start" }, song, start,
      h("button", {
        type: "button", class: "btn",
        onclick: () => {
          const music = { id: null, song: song.value, start: start.value, until: null };
          const other = clashWith(routine, music);
          if (other) {
            status.fail(t.routineMusic.clash(playlist(other, songs).name));
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
      status.fail(t.routineMusic.clash(playlist(other, songs).name));
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
    const song = playlist(m, songs);
    title.textContent = song.name;
    const cards = cardsOf(routine);
    const startAt = cards.findIndex((c) => c.id === m.start);
    // The songs, one after the other: dragged to reorder, ✕ to take one out (one at least).
    const rows = h("ul", { class: "rows" }, m.songs.map((id, index) => {
      const one = songs.find((s) => s.id === id);
      return one && h("li", { class: "row row--sortable row--compact", "data-id": String(index) },
        h("span", { class: "drag-handle", "aria-label": t.childMissions.dragLabel }, icon("drag")),
        h("span", { class: "row__icon row__icon--sm" }, icon("music")),
        h("span", { class: "row__text" }, one.name,
          h("span", { class: "row__detail" }, h("span", { class: "pill pill--muted" }, length(one.seconds)))),
        h("button", { // small, so long names keep the row's width
          type: "button", class: "icon-button icon-button--ghost", "aria-label": t.songs.listen, title: t.songs.listen,
          onclick: () => {
            listening?.pause();
            listening = new Audio(one.url);
            listening.play().catch(() => {});
          },
        }, icon("play")),
        m.songs.length > 1 && h("button", {
          type: "button", class: "icon-button icon-button--ghost", "aria-label": t.routineMusic.takeOut(one.name),
          onclick: () => change({ songs: m.songs.filter((_, i) => i !== index) }),
        }, icon("close")));
    }));
    sortable(rows, { onEnd: (order) => change({ songs: order.map((i) => m.songs[Number(i)]) }) });
    const more = h("select", { "aria-label": t.routineMusic.addSong }, songs.map((s) => h("option", { value: s.id }, s.name)));
    songBox.replaceChildren(rows,
      h("div", { class: "form-actions form-actions--start" }, more,
        h("button", { type: "button", class: "btn", onclick: () => change({ songs: [...m.songs, more.value] }) },
          icon("plus"), t.routineMusic.addAfter)),
      h("p", { class: "hint" }, m.songs.length > 1 ? t.routineMusic.lastsTogether(length(song.seconds))
        : t.routineMusic.lasts(length(song.seconds))));
    const ending = m.until !== null;
    // One sentence with gaps to tap (rutinas-7): "Empieza en [ficha] y suena [una vez /
    // hasta que acabe] [ficha]"; the last gap only when it lasts up to a card.
    const startPick = h("select", { class: "pick", "aria-label": t.routineMusic.startsIn, onchange: (e) => change({ start: e.target.value }) },
      songCards(routine).map((c) => h("option", { value: c.id, selected: c.id === m.start }, cardText(c, routine))));
    const howPick = h("select", {
      class: "pick", "aria-label": t.routineMusic.ends,
      onchange: (e) => change({ until: e.target.value === "card" ? cards[startAt].id === "alarm" ? cards[startAt + 1]?.id : m.start : null }),
    },
      h("option", { value: "once", selected: !ending }, t.routineMusic.playsOnce(length(song.seconds))),
      h("option", { value: "card", selected: ending }, t.routineMusic.playsUntil));
    const untilPick = ending && h("select", { class: "pick", "aria-label": t.routineMusic.ends, onchange: (e) => change({ until: e.target.value }) },
      cards.slice(startAt).filter((c) => c.id !== "alarm").map((c) =>
        h("option", { value: c.id, selected: c.id === m.until }, cardText(c, routine, true))));
    whenBox.replaceChildren(...[
      h("p", { class: "sentence" }, t.routineMusic.startsIn, " ", startPick, " ", t.routineMusic.andPlays, " ", howPick,
        ...(untilPick ? [" ", untilPick] : [])),
      h("p", { class: "hint" }, hintOf(routine, m, song)),
      m.start === "alarm" && h("p", { class: "hint" }, t.routineMusic.hintAlarm),
      h("label", { class: "toggle" },
        h("input", { type: "checkbox", checked: m.after_voice, onchange: (e) => change({ after_voice: e.target.checked }) }),
        t.routineMusic.afterVoice),
      h("label", { class: "toggle" },
        h("input", { type: "checkbox", checked: m.loud, onchange: (e) => change({ loud: e.target.checked }) }),
        t.routineMusic.loud),
      h("p", { class: "hint" }, t.routineMusic.optionsHint),
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
        h("div", { class: "stack" }, panel(t.routineMusic.panelSongs, songBox)),
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
