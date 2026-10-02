// "Copy subject" / "Copy body" buttons on the Client links page.
(function () {
  "use strict";

  async function copy(text, box) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      // Older browsers / non-secure contexts: select the text and use the legacy command.
      box.focus();
      box.select();
      if (!document.execCommand("copy")) throw err;
    }
  }

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".js-copy");
    if (!btn) return;
    const box = document.getElementById(btn.dataset.target);
    const status = btn.closest(".copy-group").querySelector(".copy-status");
    try {
      await copy(box.value, box);
      status.textContent = "Copied!";
    } catch (err) {
      box.select();
      status.textContent = "Press Ctrl+C to copy.";
    }
    setTimeout(() => { status.textContent = ""; }, 3000);
  });
})();
