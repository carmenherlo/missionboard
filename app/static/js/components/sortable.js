// Reorder the items of a list by dragging their handle (finger or mouse).
// Items need data-id and a ".drag-handle"; elsewhere, swiping still scrolls.
// The dragged item follows the pointer and the others slide out of its way.
// onEnd(ids) is called with the new order when it changed.
// trash (rutinas-7): { label, onDrop(id) }: while dragging, a bin at the bottom of the
// screen; let go over it and the item is dropped (onDrop), instead of moved.
// group (a step and its tasks): () => the lists it can go to; each one takes it while the
// pointer is over it or over its closest [data-drop-zone]. onPlace(id, list, position)
// instead of onEnd. Lists can be nested: a handle belongs to its nearest item only.
import { h } from "../dom.js";
import { icon } from "../icons.js";

const SLIDE_MS = 150;

export function sortable(list, { onEnd, onPlace = null, group = null, trash = null }) {
  const ids = () => [...list.children].filter((el) => el.dataset.id).map((el) => el.dataset.id); // not the songs' heads

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
    if (item.parentElement !== list) return; // the handle of an item in a list inside
    event.preventDefault();
    const home = list;
    let current = list;
    const before = ids().join();
    // Where inside the item it was grabbed, so it does not jump under the finger.
    const grabOffset = event.clientY - item.getBoundingClientRect().top;
    item.classList.add("is-dragging");
    item.style.transition = "none";
    const order = [...list.children]; // to put it back, if it goes to the bin
    const bin = trash && h("div", { class: "trash", "aria-hidden": "true" }, icon("trash"), h("span", {}, trash.label));
    if (bin) document.body.append(bin);
    const overBin = (e) => {
      if (!bin) return false;
      const box = bin.getBoundingClientRect();
      return e.clientX >= box.left && e.clientX <= box.right && e.clientY >= box.top - 12 && e.clientY <= box.bottom;
    };

    function follow(clientY) {
      item.style.transform = "";
      const naturalTop = item.getBoundingClientRect().top;
      item.style.transform = `translateY(${clientY - grabOffset - naturalTop}px)`;
    }

    // Listen on the whole window: the pointer soon leaves the small handle.
    function move(e) {
      if (e.pointerId !== event.pointerId) return;
      if (group) {
        current = group().find((other) => {
          const box = (other.closest("[data-drop-zone]") ?? other).getBoundingClientRect();
          return e.clientY >= box.top && e.clientY <= box.bottom;
        }) ?? current;
      }
      const others = [...current.children].filter((el) => el !== item);
      const next = others.find((el) => {
        const box = el.getBoundingClientRect();
        return e.clientY < box.top + box.height / 2;
      });
      const moved = item.parentElement !== current
        || (next ? item.nextElementSibling !== next : current.lastElementChild !== item);
      if (moved) {
        const tops = new Map(others.map((el) => [el, el.getBoundingClientRect().top]));
        if (next) current.insertBefore(item, next);
        else current.append(item);
        slide(others, tops);
      }
      follow(e.clientY);
      bin?.classList.toggle("trash--hot", overBin(e));
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
      const dropped = overBin(e);
      bin?.remove();
      if (dropped) {
        home.replaceChildren(...order);
        trash.onDrop(item.dataset.id);
        return;
      }
      if (onPlace) {
        if (current !== home || ids().join() !== before) {
          onPlace(item.dataset.id, current, [...current.children].indexOf(item));
        }
        return;
      }
      if (ids().join() !== before) onEnd(ids());
    }

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  });
}
