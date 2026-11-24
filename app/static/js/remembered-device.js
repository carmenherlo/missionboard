// A parent's phone that remembers the parent code (padres-movil.html, the short way):
// kept in this browser only, so the app opens in the parents' zone without asking.
// Never on the children's tablet. Browser storage can be missing (private mode): then nothing is kept.

const KEY = "missionboard.parentCode";

export function rememberedCode() {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

// code: the one to keep, or null to forget this device.
export function rememberCode(code) {
  try {
    if (code) localStorage.setItem(KEY, code);
    else localStorage.removeItem(KEY);
  } catch {
    // not kept: the code is asked again next time
  }
}
