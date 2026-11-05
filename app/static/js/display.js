// How this tablet shows the app (Configurar → Pantalla): which home screen (the
// kids or the clock), and the rest mode. Kept on the device, not with the family's
// data: one tablet in the living room may rest and another not. Browser storage can
// be missing (private mode): then the defaults.

const KEY = "missionboard.display";
const DEFAULTS = { screen: "kids", open: "last", rest: true, restMinutes: 5, clockTheme: "light" };

export function display() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || "{}") };
  } catch {
    return { ...DEFAULTS };
  }
}

export function setDisplay(changes) {
  const next = { ...display(), ...changes };
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // not kept: it lasts until the page is loaded again
  }
  return next;
}

// The home screen to show now: the last one chosen, or the one the parents fixed.
export function homeScreen() {
  const { open, screen } = display();
  return open === "last" ? screen : open;
}
