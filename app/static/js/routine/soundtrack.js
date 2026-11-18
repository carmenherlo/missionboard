// The routine's songs (music.js plays them): which ones are on now, the one that
// rings instead of the alarm, and "Parar música".
import { musicWindows } from "./music.js";
import { minuteOf } from "./words.js";

export function soundtrack(r) {
  // The songs (music.js): silent while out of sight, and in a trial faster than real time.
  function playMusic(time) {
    const { view, player } = r.showing;
    player.update(r.songWindows(), time, !view.layer.hidden && r.showing.speed === 1 && !r.showing.data.paused);
    view.musicButton.hidden = !player.playing();
  }

  function songWindows() {
    const { data } = r.showing;
    const all = r.parts();
    return musicWindows(data.music ?? [], {
      wake: data.manual ? all[0].from : minuteOf(data.wake), parts: all,
      goalAt: data.goal ? r.goalAt() : all.at(-1).to,
      goalFrom: r.showing.earlyGoal ?? all.at(-1).to + r.checkMinutes(), // everyone done early: its song then
    }).filter((w) => !r.showing.musicOff.has(w.id));
  }

  // How long a song still has to play from now (the goal stays on screen until it ends).
  function songLeftMs() {
    const time = r.now();
    const window = r.songWindows().filter((w) => w.from <= time + 1 / 60 && time < w.to)
      .sort((a, b) => b.from - a.from)[0]; // the latest one plays (music.js)
    return window ? (window.to - time) * 60_000 : 0;
  }

  // A song in the alarm card (older routines), or in the first part when the alarm rings
  // right as it starts (04/11: never both at once), plays instead of the "rrring".
  const alarmSong = () => (r.showing.data.music ?? []).some((m) => !r.showing.musicOff.has(m.id)
    && (m.start === "alarm" || (m.start === 0 && minuteOf(r.showing.data.wake) === r.parts()[0].from)));

  function silenceSong() {
    const playing = r.showing.player.playing();
    if (playing) r.showing.musicOff.add(playing.id);
    r.showing.player.stop();
  }

  return { playMusic, songWindows, songLeftMs, alarmSong, silenceSong };
}
