document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const mode = btn.dataset.mode;
    document.getElementById("input_mode").value = mode;
    document.getElementById("panel-fasta").classList.toggle("hidden", mode !== "fasta");
    document.getElementById("panel-manual").classList.toggle("hidden", mode !== "manual");
  });
});

const dz = document.getElementById("dropzone");
const fi = document.getElementById("fasta_file");
const fn = document.getElementById("fasta-filename");

if (dz && fi) {
  dz.addEventListener("click", () => fi.click());
  dz.addEventListener("dragover", (e) => {
    e.preventDefault();
    dz.classList.add("drag-over");
  });
  dz.addEventListener("dragleave", () => dz.classList.remove("drag-over"));
  dz.addEventListener("drop", (e) => {
    e.preventDefault();
    dz.classList.remove("drag-over");
    fi.files = e.dataTransfer.files;
    showFilename();
  });
  fi.addEventListener("change", showFilename);
}

function showFilename() {
  if (!fn || !fi) return;
  const name = fi.files[0]?.name || "";
  fn.textContent = name;
  fn.classList.toggle("hidden", !name);
}

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const ta = document.getElementById("patterns-input");
    if (!ta) return;
    const current = ta.value.trim();
    const motif = chip.dataset.motif;
    ta.value = current ? `${current}, ${motif}` : motif;
  });
});

document.getElementById("analyse-form")?.addEventListener("submit", () => {
  document.getElementById("analyse-btn")?.classList.add("hidden");
  document.getElementById("loading")?.classList.remove("hidden");
});
