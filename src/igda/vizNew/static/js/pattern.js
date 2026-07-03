function chartPalette() {

  const root = getComputedStyle(document.documentElement);

  return [

    root.getPropertyValue("--chart-1").trim(),

    root.getPropertyValue("--chart-2").trim(),

    root.getPropertyValue("--chart-3").trim(),

    root.getPropertyValue("--chart-4").trim(),

    root.getPropertyValue("--chart-5").trim(),

    root.getPropertyValue("--chart-6").trim(),

  ];

}



const ALGO_COLORS = {

  naive: getComputedStyle(document.documentElement).getPropertyValue("--algo-naive").trim(),

  kmp: getComputedStyle(document.documentElement).getPropertyValue("--algo-kmp").trim(),

  horspool: getComputedStyle(document.documentElement).getPropertyValue("--algo-horspool").trim(),

  ahocorasick: getComputedStyle(document.documentElement).getPropertyValue("--algo-ac").trim(),

  edit_distance: getComputedStyle(document.documentElement).getPropertyValue("--algo-edit").trim(),

};



const BORDER = getComputedStyle(document.documentElement).getPropertyValue("--border").trim();

const TEXT_SEC = getComputedStyle(document.documentElement).getPropertyValue("--text-secondary").trim();

const HIGHLIGHT = getComputedStyle(document.documentElement).getPropertyValue("--ws-highlight").trim()

  || getComputedStyle(document.documentElement).getPropertyValue("--amber").trim();



document.addEventListener("DOMContentLoaded", () => {

  const rows = BENCHMARK.matcher_rows || [];

  const exact = rows.filter((r) => r.match_kind === "exact");

  const ctx = document.getElementById("runtime-chart");

  if (!ctx) return;



  Chart.defaults.color = TEXT_SEC;

  Chart.defaults.borderColor = BORDER;



  const barColor = (row) =>

    row.is_best_exact ? HIGHLIGHT : ALGO_COLORS[row.algorithm] || ALGO_COLORS.kmp;



  const chart = new Chart(ctx.getContext("2d"), {

    type: "bar",

    data: {

      labels: exact.map((r) => r.algorithm_name || r.algorithm),

      datasets: [

        {

          label: "Median (ms)",

          data: exact.map((r) => r.time_ms_median),

          backgroundColor: exact.map(barColor),

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

            label: (c) => {

              const row = exact[c.dataIndex];

              return [

                `Median: ${row.time_ms_median.toFixed(2)} ms`,

                `Min: ${row.time_ms_min.toFixed(2)} ms`,

                `Max: ${row.time_ms_max.toFixed(2)} ms`,

                `Matches: ${row.match_count}`,

              ];

            },

          },

        },

      },

      scales: {

        x: { title: { display: true, text: "milliseconds" }, grid: { color: BORDER } },

        y: { grid: { display: false } },

      },

    },

  });



  document.querySelectorAll(".algo-dot").forEach((dot) => {

    dot.style.background = ALGO_COLORS[dot.dataset.algo] || ALGO_COLORS.naive;

  });



  document.getElementById("btn-median")?.addEventListener("click", () => {

    chart.data.datasets = [

      {

        label: "Median (ms)",

        data: exact.map((r) => r.time_ms_median),

        backgroundColor: exact.map(barColor),

        borderRadius: 4,

      },

    ];

    chart.update();

    document.getElementById("btn-median").classList.add("active");

    document.getElementById("btn-range").classList.remove("active");

  });



  document.getElementById("btn-range")?.addEventListener("click", () => {

    const palette = chartPalette();

    const surface = getComputedStyle(document.documentElement).getPropertyValue("--bg-surface").trim();

    chart.data.datasets = [

      {

        label: "Min",

        data: exact.map((r) => r.time_ms_min),

        backgroundColor: surface,

        borderRadius: 4,

      },

      {

        label: "Median",

        data: exact.map((r) => r.time_ms_median),

        backgroundColor: exact.map((r, i) => ALGO_COLORS[r.algorithm] || palette[i % palette.length]),

        borderRadius: 4,

      },

      {

        label: "p95",

        data: exact.map((r) => r.time_ms_p95 ?? r.time_ms_max),

        backgroundColor: exact.map((_, i) => `${palette[(i + 2) % palette.length]}88`),

        borderRadius: 4,

      },

    ];

    chart.update();

    document.getElementById("btn-range").classList.add("active");

    document.getElementById("btn-median").classList.remove("active");

  });

});


