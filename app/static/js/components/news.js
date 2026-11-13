// What is new for a child (mi-sitio.html): an order that has arrived, or one that
// arrives today and they have not read yet in their mailbox. One sign over their
// avatar, the same on the home and on their route: the picture of what is newest
// and, with more than one thing, how many. Letters will join it later.
import { h } from "../dom.js";

const FLUENT = "static/libraries/fluent";

// The notices read in the mailbox, in this tablet ("today-12"). An order that has
// arrived stops being news on the server (when they open it), not here.
const READ_KEY = "missionboard.mailRead";

function readList() {
  try {
    return JSON.parse(localStorage.getItem(READ_KEY)) || [];
  } catch {
    return [];
  }
}

export const wasRead = (orderId) => readList().includes(`today-${orderId}`);

export function markRead(orderId) {
  if (wasRead(orderId)) return;
  try {
    localStorage.setItem(READ_KEY, JSON.stringify([...readList(), `today-${orderId}`].slice(-50)));
  } catch {
    // no storage (a private window): the sign stays until it arrives, that is all
  }
}

// summary: a child's entry of GET /api/orders/summary. null: nothing new.
export function newsOf(summary) {
  if (!summary) return null;
  const arrived = summary.arrived_ids ?? [];
  const today = (summary.today ?? []).filter((id) => !wasRead(id));
  const count = arrived.length + today.length;
  return count ? { count, arrived: arrived.length > 0, picture: `${FLUENT}/package.svg` } : null;
}

// A rocket ready to take off (taller.html) is news too, the biggest: its picture goes first.
export function withRocket(news, ready) {
  if (!ready) return news;
  return { count: (news?.count ?? 0) + 1, arrived: news?.arrived ?? false, picture: `${FLUENT}/rocket.svg` };
}

// The sign over an avatar (its parent must be positioned: .news-host).
export function newsBadge(news) {
  if (!news) return null;
  return h("span", { class: "news-badge", "aria-hidden": "true" },
    h("img", { src: news.picture, alt: "" }),
    news.count > 1 && h("b", { class: "news-badge__count" }, String(news.count)));
}
