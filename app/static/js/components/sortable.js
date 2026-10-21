// Reorder the items of a list by dragging their handle (finger or mouse).
// Items need data-id and a ".drag-handle"; elsewhere, swiping still scrolls.
// onEnd(ids) is called with the new order when it changed.

export function sortable(list, { onEnd }) {
  const ids = () => [...list.children].map((el) => el.dataset.id);

  list.addEventListener("pointerdown", (event) => {
    const handle = event.target.closest(".drag-handle");
    if (!handle || !list.contains(handle)) return;
    const item = handle.closest("[data-id]");
    event.preventDefault();
    item.classList.add("is-dragging");
    const before = ids().join();

    // Listen on the whole window: the pointer soon leaves the small handle.
    function move(e) {
      if (e.pointerId !== event.pointerId) return;
      const others = [...list.children].filter((el) => el !== item);
      const next = others.find((el) => {
        const box = el.getBoundingClientRect();
        return e.clientY < box.top + box.height / 2;
      });
      if (next) {
        if (item.nextElementSibling !== next) list.insertBefore(item, next);
      } else if (list.lastElementChild !== item) {
        list.append(item);
      }
    }

    function end(e) {
      if (e.pointerId !== event.pointerId) return;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      item.classList.remove("is-dragging");
      if (ids().join() !== before) onEnd(ids());
    }

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  });
}
