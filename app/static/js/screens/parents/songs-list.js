import { api, errorMessage } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const BACK_HREF = "#/parents/config/routines";
const MAX_SONG_BYTES = 15 * 1024 * 1024;

// Configurar → Rutinas → Música (rutinas-4, screen 3; "Canciones" until 05/11): the family's songs, uploaded
// once and used in any routine. Like the prizes: a list, and a button to add.
// fromRoutine: opened from a routine's editor, "←" goes back there.
export async function viewSongsList(fromRoutine = null) {
  let songs = await api("GET", "api/songs");
  const routine = fromRoutine && await api("GET", `api/routines/${fromRoutine}`).catch(() => null);
  const back = routine ? { href: `${BACK_HREF}/${routine.id}`, label: routine.name } : { href: BACK_HREF, label: t.routines.title };
  const status = saveStatus();
  const list = h("ul", { class: "rows" });
  const actions = h("div", { class: "form-actions form-actions--start" });
  const listening = { audio: null, id: null };
  let renaming = null;

  function listen(song) {
    listening.audio?.pause();
    if (listening.id === song.id) {
      listening.audio = listening.id = null;
    } else {
      listening.audio = new Audio(song.url);
      listening.id = song.id;
      listening.audio.addEventListener("ended", () => { listening.audio = listening.id = null; draw(); });
      listening.audio.play().catch(() => {});
    }
    draw();
  }

  function draw() {
    list.replaceChildren(...songs.map((song) => song.id === renaming ? renameRow(song) : h("li", { class: "row row--compact" },
      h("span", { class: "row__icon" }, icon("music")),
      h("span", { class: "row__text" }, song.name,
        h("span", { class: "row__detail" },
          h("span", { class: "pill pill--muted" }, `${length(song.seconds)} · ${t.songs.usedIn(song.used_in)}`))),
      h("button", { type: "button", class: "btn", onclick: () => listen(song) },
        listening.id === song.id ? t.songs.pause : `▶ ${t.songs.listen}`),
      h("button", {
        type: "button", class: "icon-button icon-button--ghost", "aria-label": t.songs.rename(song.name),
        onclick: () => { renaming = song.id; draw(); },
      }, icon("edit")),
      h("button", {
        type: "button", class: "icon-button icon-button--ghost", "aria-label": t.songs.remove(song.name),
        onclick: () => confirmDelete(song),
      }, icon("trash")))));
    drawActions();
  }

  function renameRow(song) {
    const input = h("input", { type: "text", maxlength: 40, value: song.name });
    const done = async () => {
      const name = input.value.trim();
      if (name && name !== song.name) {
        const renamed = await status.track(api("PATCH", `api/songs/${song.id}`, { json: { name } })).catch(() => null);
        if (renamed) songs = songs.map((s) => (s.id === song.id ? renamed : s));
      }
      renaming = null;
      draw();
    };
    input.addEventListener("keydown", (e) => e.key === "Enter" && done());
    queueMicrotask(() => input.focus());
    return h("li", { class: "row row--add" }, input,
      h("button", { type: "button", class: "btn btn--primary", onclick: done }, t.common.done));
  }

  function confirmDelete(song) {
    actions.replaceChildren(confirmBar({
      message: t.songs.confirmDelete(song.name, song.used_in),
      confirmLabel: t.songs.confirmYes,
      onCancel: drawActions,
      onConfirm: async () => {
        await status.track(api("DELETE", `api/songs/${song.id}`)).catch(() => {});
        songs = await api("GET", "api/songs");
        draw();
      },
    }));
  }

  // The browser measures how long it lasts (the server does not read audio files).
  // .opus named too: some tablets do not file it as audio and would hide it (04/11).
  const picker = h("input", {
    type: "file", accept: "audio/*,.mp3,.m4a,.opus,.ogg,.wav", hidden: true, onchange: () => upload(picker.files[0]),
  });
  async function upload(file) {
    picker.value = "";
    if (!file) return;
    if (file.size > MAX_SONG_BYTES) {
      status.fail(t.songs.tooBig);
      return;
    }
    const seconds = await durationOf(file);
    if (!seconds) {
      status.fail(t.songs.unreadable);
      return;
    }
    const name = file.name.replace(/\.[^.]+$/, "").slice(0, 40).trim() || "Canción";
    const query = new URLSearchParams({ name, seconds: String(seconds) });
    try {
      const song = await status.track(api("POST", `api/songs?${query}`, { body: file, contentType: file.type || "audio/mpeg" }));
      songs = [...songs, song];
      draw();
    } catch (err) {
      status.fail(err?.status === 415 ? t.songs.unreadable : errorMessage(err));
    }
  }

  function drawActions() {
    actions.replaceChildren(h("button", { type: "button", class: "btn btn--primary", onclick: () => picker.click() },
      icon("plus"), t.songs.upload));
  }

  draw();
  render(
    parentsHeader(h("span", { class: "title-line" }, h("span", {}, t.songs.title), status.element),
      back),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("p", { class: "hint" }, songs.length ? t.songs.hint : t.songs.empty),
        panel(t.songs.panel(songs.length), list, actions, picker))));
}

function durationOf(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    const done = (seconds) => { URL.revokeObjectURL(url); resolve(seconds); };
    audio.addEventListener("loadedmetadata", () => done(Number.isFinite(audio.duration) ? audio.duration : 0), { once: true });
    audio.addEventListener("error", () => done(0), { once: true });
    audio.src = url;
  });
}

// 190.4 → "3:10"
export function length(seconds) {
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}
