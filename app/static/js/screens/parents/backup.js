// Configurar → Copia de seguridad: everything the family has in one file, and
// putting one back (another device, Home Assistant, or after a mistake).
import { api, apiFile, errorMessage } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export function viewBackup() {
  render(
    parentsHeader(t.backup.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "columns columns--equal" },
        downloadPanel(),
        restorePanel())));
}

function downloadPanel() {
  const error = h("p", { class: "form-error", role: "alert" });
  const button = h("button", {
    type: "button", class: "btn btn--primary",
    onclick: async () => {
      error.textContent = "";
      button.disabled = true;
      try {
        const { blob, filename } = await apiFile("api/backup");
        const url = URL.createObjectURL(blob);
        h("a", { href: url, download: filename }).click();
        URL.revokeObjectURL(url);
      } catch (err) {
        error.textContent = errorMessage(err);
      } finally {
        button.disabled = false;
      }
    },
  }, icon("download"), t.backup.download);
  return panel(t.backup.downloadTitle,
    h("p", {}, t.backup.downloadText),
    h("div", { class: "form-actions form-actions--start" }, button),
    error,
    h("p", { class: "hint" }, t.backup.downloadHint));
}

function restorePanel() {
  const box = h("div", { class: "stack stack--tight" });
  const file = h("input", { type: "file", accept: ".zip,application/zip", "aria-label": t.backup.chooseFile });
  const error = h("p", { class: "form-error", role: "alert" });

  function draw() {
    box.replaceChildren(file, h("div", { class: "form-actions form-actions--start" },
      h("button", {
        type: "button", class: "btn",
        onclick: () => {
          error.textContent = "";
          const chosen = file.files[0];
          if (!chosen) {
            error.textContent = t.backup.noFile;
            return;
          }
          box.replaceChildren(confirmBar({
            message: t.backup.confirm(chosen.name),
            detail: t.backup.confirmDetail,
            confirmLabel: t.backup.confirmYes,
            onCancel: draw,
            onConfirm: async () => {
              await api("POST", "api/backup/restore", { body: chosen, contentType: "application/zip" });
              done();
            },
          }));
        },
      }, t.backup.restore)), error);
  }

  // Everything changed, maybe the parents' code too: back to the start.
  function done() {
    box.replaceChildren(
      h("p", { class: "notice" }, t.backup.restored),
      h("a", { class: "btn btn--primary", href: "#/" }, t.backup.toHome));
  }

  draw();
  return panel(t.backup.restoreTitle, h("p", {}, t.backup.restoreText), box);
}
