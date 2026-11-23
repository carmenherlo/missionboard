// A phone shows the children's screens sideways, as a tablet (16/11): in full screen,
// Android's Chrome locks it sideways (no browser can lock it otherwise); never in the
// parents' zone. No sign asking to turn it (taken out 23/11: it got in the way).
const PHONE = 600; // px: the shorter side of a phone is below this (a tablet's is not)

const isPhone = () => Math.min(screen.width, screen.height) < PHONE;
const inParents = () => location.hash.startsWith("#/parents");

function lockSideways() {
  const orientation = screen.orientation;
  if (!orientation?.lock || !isPhone()) return;
  if (document.fullscreenElement && !inParents()) orientation.lock("landscape").catch(() => {});
  else orientation.unlock?.();
}

export function startTurnPhone() {
  const zone = () => {
    document.body.classList.toggle("in-parents", inParents());
    lockSideways();
  };
  window.addEventListener("hashchange", zone);
  document.addEventListener("fullscreenchange", lockSideways);
  zone();
}
