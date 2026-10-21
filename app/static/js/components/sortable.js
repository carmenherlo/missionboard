// Reorder the items of a list by dragging their handle (finger or mouse).
// Items need data-id and a ".drag-handle"; elsewhere, swiping still scrolls.
// The dragged item follows the pointer and the others slide out of its way.
// onEnd(ids) is called with the new order when it changed.

const SLIDE_MS = 150;

export function sortable(list, { onEnd }) {
  const ids = () => [...list.children].map((el) => el.dataset.id);

  // Animate siblings from where they were to where they are now (FLIP).
  function slide(items, before) {
    for (const el of items) {
      const dy = before.get(el) - el.getBoundingClientRect().top;
      if (!dy) continue;
      el.style.transition = "none";
      el.style.transform = `translateY(${dy}px)`;
      requestAnimationFrame(() => {
        el.style.transition = `transform ${SLIDE_MS}ms ease`;
        el.style.transform = "";
      });
    }
  }

  list.addEventListener("pointerdown", (event) => {
    const handle = event.target.closest(".drag-handle");
    if (!handle || !list.contains(handle)) return;
    const item = handle.closest("[data-id]");
    event.preventDefault();
    const before = ids().join();
    // Where inside the item it was grabbed, so it does not jump under the finger.
    const grabOffset = event.clientY - item.getBoundingClientRect().top;
    item.classList.add("is-dragging");
    item.style.transition = "none";

    function follow(clientY) {
      item.style.transform = "";
      const naturalTop = item.getBoundingClientRect().top;
      item.style.transform = `translateY(${clientY - grabOffset - naturalTop}px)`;
    }

    // Listen on the whole window: the pointer soon leaves the small handle.
    function move(e) {
      if (e.pointerId !== event.pointerId) return;
      const others = [...list.children].filter((el) => el !== item);
      const next = others.find((el) => {
        const box = el.getBoundingClientRect();
        return e.clientY < box.top + box.height / 2;
      });
      const moved = next ? item.nextElementSibling !== next : list.lastElementChild !== item;
      if (moved) {
        const tops = new Map(others.map((el) => [el, el.getBoundingClientRect().top]));
        if (next) list.insertBefore(item, next);
        else list.append(item);
        slide(others, tops);
      }
      follow(e.clientY);
    }

    function end(e) {
      if (e.pointerId !== event.pointerId) return;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      // Settle into its slot smoothly.
      item.style.transition = `transform ${SLIDE_MS}ms ease`;
      item.style.transform = "";
      item.classList.remove("is-dragging");
      if (ids().join() !== before) onEnd(ids());
    }

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  });
}
