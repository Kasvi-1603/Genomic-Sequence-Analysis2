/**
 * Client-side benchmark session UI persistence (localStorage) + workspace attach.
 */
(function () {
  const LOG = "[BenchmarkSession]";
  const UI_KEY = "igda_benchmark_ui";
  const WID_KEY = "igda_workspace_id";

  function log(msg, detail) {
    if (detail !== undefined) {
      console.log(LOG, msg, detail);
    } else {
      console.log(LOG, msg);
    }
  }

  function readUi() {
    try {
      return JSON.parse(localStorage.getItem(UI_KEY) || "{}");
    } catch {
      return {};
    }
  }

  function writeUi(partial) {
    const next = { ...readUi(), ...partial, savedAt: new Date().toISOString() };
    localStorage.setItem(UI_KEY, JSON.stringify(next));
    log("Saving UI state", partial);
  }

  function saveScroll() {
    writeUi({ scrollPosition: window.scrollY });
  }

  function restoreScroll() {
    const ui = readUi();
    if (typeof ui.scrollPosition === "number" && ui.scrollPosition > 0) {
      window.scrollTo(0, ui.scrollPosition);
      log("Restored scroll position", ui.scrollPosition);
    }
  }

  function rememberWorkspaceId() {
    const wid = window.BENCHMARK_WORKSPACE_ID;
    if (!wid) return;
    localStorage.setItem(WID_KEY, wid);
    log("Saved workspace id", wid);
  }

  function attachWorkspaceIfNeeded() {
    const stored = localStorage.getItem(WID_KEY);
    const server = window.BENCHMARK_WORKSPACE_ID;
    if (!stored || (server && stored === server)) return;
    fetch("/api/session/attach", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: stored }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) log("Restored previous session via attach", stored);
      })
      .catch(() => {});
  }

  function hydrateUploadForm() {
    const state = window.UPLOAD_STATE;
    if (!state || typeof state !== "object") return;

    log("Hydrating upload form from server session");

    const mode = state.input_mode || "fasta";
    const modeInput = document.getElementById("input_mode");
    if (modeInput) modeInput.value = mode;

    document.querySelectorAll(".tab-btn").forEach((btn) => {
      const active = btn.dataset.mode === mode;
      btn.classList.toggle("active", active);
    });
    document.getElementById("panel-fasta")?.classList.toggle("hidden", mode !== "fasta");
    document.getElementById("panel-manual")?.classList.toggle("hidden", mode !== "manual");

    const patterns = document.getElementById("patterns-input");
    if (patterns && state.patterns) patterns.value = state.patterns;

    const prefix = document.getElementById("prefix_chars");
    if (prefix && state.prefix_chars != null && state.prefix_chars !== "") {
      prefix.value = state.prefix_chars;
    }

    const manual = document.getElementById("manual_text");
    if (manual && state.manual_text) manual.value = state.manual_text;

    const maxEdits = state.max_edits;
    if (maxEdits != null) {
      const radio = document.querySelector(`input[name="max_edits"][value="${maxEdits}"]`);
      if (radio) radio.checked = true;
    }

    const files = state.uploaded_files || [];
    if (files.length && mode === "fasta") {
      const fn = document.getElementById("fasta-filename");
      const meta = files[0];
      if (fn && meta.name) {
        fn.textContent = `${meta.name} (session — choose a new file only to replace)`;
        fn.classList.remove("hidden");
      }
    }

    const ui = readUi();
    if (ui.activeTab && ui.activeTab !== mode) {
      const tab = document.querySelector(`.tab-btn[data-mode="${ui.activeTab}"]`);
      tab?.click();
    }
  }

  function saveUploadDraftToServer() {
    const wid = window.BENCHMARK_WORKSPACE_ID || localStorage.getItem(WID_KEY);
    if (!wid && !window.SESSION_RESTORED) return;

    const body = {
      input_mode: document.getElementById("input_mode")?.value,
      patterns: document.getElementById("patterns-input")?.value,
      prefix_chars: document.getElementById("prefix_chars")?.value,
      max_edits: document.querySelector('input[name="max_edits"]:checked')?.value,
      manual_text: document.getElementById("manual_text")?.value?.slice(0, 8000),
    };

    fetch("/api/session/upload-draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) log("Saving upload draft to server");
      })
      .catch(() => {});
  }

  function bindUploadAutosave() {
    const form = document.getElementById("analyse-form");
    if (!form) return;

    let timer;
    const debounced = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const mode = document.getElementById("input_mode")?.value;
        writeUi({
          activeTab: mode,
          patterns: document.getElementById("patterns-input")?.value,
          prefix_chars: document.getElementById("prefix_chars")?.value,
          max_edits: document.querySelector('input[name="max_edits"]:checked')?.value,
        });
        saveUploadDraftToServer();
      }, 400);
    };

    form.addEventListener("input", debounced);
    form.addEventListener("change", debounced);
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        writeUi({ activeTab: btn.dataset.mode });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    rememberWorkspaceId();
    attachWorkspaceIfNeeded();
    hydrateUploadForm();
    bindUploadAutosave();
    restoreScroll();
    if (window.SESSION_RESTORED) log("Restored previous session");
  });

  window.addEventListener("beforeunload", saveScroll);

  window.BenchmarkSession = { log, writeUi, readUi };
})();
