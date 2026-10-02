// Repeating medication/doctor rows for the intake form.
// Keeps field names as  medications-0-name, medications-1-name, ...  so WTForms'
// FieldList parses them, and renumbers after every add/remove so there are no gaps.
(function () {
  "use strict";

  const form = document.getElementById("medform");
  if (!form) return;

  const LIMITS = {
    medications: parseInt(form.dataset.maxMedications, 10) || 25,
    doctors: parseInt(form.dataset.maxDoctors, 10) || 10,
  };
  const NAME_RE = /^(medications|doctors)-(\d+|__i__)-/;

  const container = (kind) => document.getElementById(kind + "-rows");
  const rows = (kind) => Array.from(container(kind).querySelectorAll(":scope > fieldset"));

  function renumber(kind) {
    const list = rows(kind);
    list.forEach((row, i) => {
      row.querySelector(".row-num").textContent = list.length > 1 ? String(i + 1) : "";
      row.querySelectorAll("[name], [id], label[for]").forEach((el) => {
        for (const attr of ["name", "id", "for"]) {
          const v = el.getAttribute(attr);
          if (v && NAME_RE.test(v)) el.setAttribute(attr, v.replace(NAME_RE, `${kind}-${i}-`));
        }
      });
      // A form must keep at least one row of each kind.
      row.querySelector(".js-remove").hidden = list.length === 1;
    });
    form.querySelector(`[data-add="${kind}"]`).hidden = list.length >= LIMITS[kind];
  }

  // Show the "If Other, please explain" box only when "Other" is selected.
  function toggleOther(row) {
    const freq = row.querySelector(".js-frequency");
    const other = row.querySelector(".js-other");
    if (freq && other) other.hidden = freq.value !== "other";
  }

  function addRow(kind) {
    if (rows(kind).length >= LIMITS[kind]) return;
    const tpl = document.getElementById(kind + "-template");
    const row = tpl.content.firstElementChild.cloneNode(true);
    container(kind).appendChild(row);
    toggleOther(row);
    renumber(kind);
    row.querySelector("input, select").focus();
  }

  // ---- Event delegation: one listener each, works for rows added later ----

  form.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add]");
    if (add) {
      addRow(add.dataset.add);
      return;
    }
    const remove = e.target.closest(".js-remove");
    if (remove) {
      const row = remove.closest("fieldset");
      const kind = row.dataset.row;
      if (rows(kind).length <= 1) return;
      row.remove();
      renumber(kind);
    }
  });

  form.addEventListener("change", (e) => {
    if (e.target.matches(".js-frequency")) toggleOther(e.target.closest("fieldset"));
  });

  // ---- Initial state (also restores rows after a server-side validation error) ----
  rows("medications").forEach(toggleOther);
  renumber("doctors");
  renumber("medications");
})();
