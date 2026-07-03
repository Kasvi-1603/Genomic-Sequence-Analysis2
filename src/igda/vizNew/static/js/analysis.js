const ALGO_COLORS = {
  naive: getComputedStyle(document.documentElement).getPropertyValue("--algo-naive").trim(),
  kmp: getComputedStyle(document.documentElement).getPropertyValue("--algo-kmp").trim(),
  horspool: getComputedStyle(document.documentElement).getPropertyValue("--algo-horspool").trim(),
  ahocorasick: getComputedStyle(document.documentElement).getPropertyValue("--algo-ac").trim(),
  edit_distance: getComputedStyle(document.documentElement).getPropertyValue("--algo-edit").trim(),
};

const BORDER = getComputedStyle(document.documentElement).getPropertyValue("--border").trim();
const TEXT_SEC = getComputedStyle(document.documentElement).getPropertyValue("--text-secondary").trim();

function initGrowthChart() {
  const ctx = document.getElementById("growth-chart")?.getContext("2d");
  if (!ctx || !MULTI_N.length) return;

  const algoIds = ["naive", "kmp", "horspool", "ahocorasick", "edit_distance"];
  const ns = MULTI_N.map((d) => d.n);

  const datasets = algoIds.map((id) => ({
    label: id,
    data: MULTI_N.map((d) => {
      const row = (d.results.matcher_rows || []).find((r) => r.algorithm === id);
      return row ? parseFloat(row.time_ms_median.toFixed(3)) : null;
    }),
    borderColor: ALGO_COLORS[id],
    backgroundColor: `${ALGO_COLORS[id]}33`,
    tension: 0.3,
    borderWidth: id === "edit_distance" ? 2.5 : 2,
    pointRadius: 5,
    pointBackgroundColor: ALGO_COLORS[id],
    pointBorderColor: "#100d20",
    pointBorderWidth: 1,
    fill: false,
  }));

  new Chart(ctx, {
    type: "line",
    data: { labels: ns.map((n) => n.toLocaleString()), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true, color: TEXT_SEC } },
        tooltip: {
          callbacks: {
            label: (c) => `${c.dataset.label}: ${c.parsed.y?.toFixed(2)} ms`,
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "input length (chars)", color: TEXT_SEC },
          grid: { color: BORDER },
        },
        y: {
          title: { display: true, text: "median time (ms)", color: TEXT_SEC },
          grid: { color: BORDER },
        },
      },
    },
  });
}

function initMutationChart() {
  const ctx = document.getElementById("mut-pattern-chart");
  if (!ctx || typeof MUTATION_REPORT === "undefined" || !MUTATION_REPORT) return;

  const counts = MUTATION_REPORT.pattern_counts || {};
  const labels = Object.keys(counts);
  const values = Object.values(counts);

  if (!labels.length) {
    const card = ctx.closest(".table-card");
    if (card) card.style.display = "none";
    return;
  }

  const palette = [
    getComputedStyle(document.documentElement).getPropertyValue("--chart-1").trim(),
    getComputedStyle(document.documentElement).getPropertyValue("--chart-2").trim(),
    getComputedStyle(document.documentElement).getPropertyValue("--chart-3").trim(),
    getComputedStyle(document.documentElement).getPropertyValue("--chart-4").trim(),
  ];
  const chartColors = labels.map((_, i) => palette[i % palette.length] || "#8E0D3C");

  new Chart(ctx.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Mutation sites",
          data: values,
          backgroundColor: chartColors,
          borderRadius: 4,
          borderSkipped: false,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (c) => `${c.parsed.x} mutation site${c.parsed.x !== 1 ? "s" : ""}`,
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "number of mutation sites", color: TEXT_SEC },
          grid: { color: BORDER },
          ticks: { stepSize: 1, color: TEXT_SEC },
        },
        y: { grid: { display: false }, ticks: { color: TEXT_SEC } },
      },
    },
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initGrowthChart();
  initMutationChart();
  initMotifHeatmap();

  document.getElementById("mut-load-more")?.addEventListener("click", loadMoreMutations);
});

let mutShowing = 10;
let heatmapMode = "exact";

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function heatmapCellColor(intensity, mode) {
  const t = Math.max(0, Math.min(1, intensity));
  if (t === 0) {
    return cssVar("--bg-surface", "#1d1842");
  }
  if (mode === "exact") {
    const r = Math.round(29 + (93 - 29) * t);
    const g = Math.round(24 + (202 - 24) * t);
    const b = Math.round(66 + (165 - 66) * t);
    const a = 0.25 + 0.75 * t;
    return `rgba(${r}, ${g}, ${b}, ${a.toFixed(2)})`;
  }
  const r = Math.round(42 + (142 - 42) * t);
  const g = Math.round(36 + (13 - 36) * t);
  const b = Math.round(96 + (60 - 96) * t);
  const a = 0.2 + 0.8 * t;
  return `rgba(${r}, ${g}, ${b}, ${a.toFixed(2)})`;
}

function initMotifHeatmap() {
  const root = document.getElementById("mut-heatmap-root");
  if (!root || typeof MUTATION_REPORT === "undefined" || !MUTATION_REPORT?.heatmap) {
    return;
  }

  const btnExact = document.getElementById("heatmap-exact");
  const btnMut = document.getElementById("heatmap-mutation");

  btnExact?.addEventListener("click", () => {
    heatmapMode = "exact";
    btnExact?.classList.add("active");
    btnMut?.classList.remove("active");
    renderMotifHeatmap();
  });

  btnMut?.addEventListener("click", () => {
    if (btnMut?.disabled) return;
    heatmapMode = "mutation";
    btnMut.classList.add("active");
    btnExact?.classList.remove("active");
    renderMotifHeatmap();
  });

  renderMotifHeatmap();
}

function renderMotifHeatmap() {
  const root = document.getElementById("mut-heatmap-root");
  const heatmap = MUTATION_REPORT?.heatmap;
  if (!root || !heatmap) return;

  const layer = heatmap[heatmapMode];
  const patterns = layer?.patterns || [];
  const numBins = heatmap.num_bins;
  const binWidth = heatmap.bin_width;
  const seqLen = heatmap.sequence_length;
  const maxVal = layer?.max || 0;

  root.innerHTML = "";

  if (!patterns.length) {
    root.innerHTML = '<p class="chart-note">No patterns in this layer.</p>';
    return;
  }

  const tickStep = Math.max(1, Math.ceil(numBins / 8));
  const xHeader = document.createElement("div");
  xHeader.className = "mut-heatmap-x-header";
  xHeader.innerHTML = '<div class="mut-heatmap-x-spacer"></div>';
  const xTicks = document.createElement("div");
  xTicks.className = "mut-heatmap-x-ticks";
  xTicks.style.gridTemplateColumns = `repeat(${numBins}, minmax(8px, 1fr))`;
  for (let i = 0; i < numBins; i++) {
    const tick = document.createElement("span");
    tick.className = "mut-heatmap-x-tick";
    tick.textContent = i % tickStep === 0 || i === numBins - 1 ? `${i * binWidth}` : "";
    xTicks.appendChild(tick);
  }
  xHeader.appendChild(xTicks);
  root.appendChild(xHeader);

  patterns.forEach((pattern) => {
    const row = document.createElement("div");
    row.className = "mut-heatmap-row";

    const label = document.createElement("span");
    label.className = "mut-heatmap-row-label mono";
    label.textContent = pattern;
    row.appendChild(label);

    const cells = document.createElement("div");
    cells.className = "mut-heatmap-cells";
    cells.style.gridTemplateColumns = `repeat(${numBins}, minmax(8px, 1fr))`;

    const counts = layer.counts[pattern] || [];
    counts.forEach((count, binIdx) => {
      const cell = document.createElement("div");
      cell.className = "mut-heatmap-cell";
      cell.tabIndex = 0;
      const intensity = maxVal > 0 ? count / maxVal : 0;
      cell.style.backgroundColor = heatmapCellColor(intensity, heatmapMode);
      const start = binIdx * binWidth;
      const end = Math.min(seqLen, start + binWidth);
      const layerLabel = heatmapMode === "exact" ? "Exact hits" : "Mutation-only hits";
      cell.title = `${pattern} · ${start.toLocaleString()}–${end.toLocaleString()} · ${count} hit${count !== 1 ? "s" : ""} (${layerLabel})`;
      cell.setAttribute("aria-label", cell.title);
      cells.appendChild(cell);
    });

    row.appendChild(cells);
    root.appendChild(row);
  });

  const legendBar = document.getElementById("mut-heatmap-legend-bar");
  const legendMax = document.getElementById("mut-heatmap-legend-max");
  if (legendBar) {
    legendBar.style.background = "transparent";
    legendBar.style.display = "grid";
    legendBar.style.gridTemplateColumns = "repeat(5, 1fr)";
    legendBar.style.gap = "2px";
    legendBar.innerHTML = "";
    for (let i = 1; i <= 5; i += 1) {
      const seg = document.createElement("span");
      seg.style.height = "8px";
      seg.style.borderRadius = "2px";
      seg.style.backgroundColor = heatmapCellColor(i / 5, heatmapMode);
      legendBar.appendChild(seg);
    }
  }
  if (legendMax) {
    legendMax.textContent = maxVal > 0 ? String(maxVal) : "—";
  }
}

function loadMoreMutations() {
  const rows = document.querySelectorAll(".mut-site-row");
  const next = Math.min(mutShowing + 10, rows.length);
  for (let i = mutShowing; i < next; i++) {
    rows[i].style.display = "";
  }
  mutShowing = next;
  const showingEl = document.getElementById("mut-showing");
  if (showingEl) showingEl.textContent = String(mutShowing);
  if (mutShowing >= rows.length) {
    const wrap = document.getElementById("mut-load-more-wrap");
    if (wrap) wrap.style.display = "none";
  }
}
