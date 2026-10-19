"use strict";

function renderHome() {
  const container = document.getElementById("children");
  const empty = document.createElement("p");
  empty.className = "children__empty";
  empty.textContent = "Todavía no hay niños.";
  container.replaceChildren(empty);
}

document.addEventListener("DOMContentLoaded", renderHome);
