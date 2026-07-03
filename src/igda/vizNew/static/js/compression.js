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



const BORDER = getComputedStyle(document.documentElement).getPropertyValue("--border").trim();

const TEXT_SEC = getComputedStyle(document.documentElement).getPropertyValue("--text-secondary").trim();

const HUFFMAN = getComputedStyle(document.documentElement).getPropertyValue("--algo-huffman").trim();

const RLE = getComputedStyle(document.documentElement).getPropertyValue("--algo-rle").trim();

const CARD = getComputedStyle(document.documentElement).getPropertyValue("--bg-card").trim();

const SURFACE = getComputedStyle(document.documentElement).getPropertyValue("--bg-surface").trim();

const ACCENT = getComputedStyle(document.documentElement).getPropertyValue("--ws-accent").trim()

  || getComputedStyle(document.documentElement).getPropertyValue("--deep-red").trim();

const MONO = getComputedStyle(document.documentElement).getPropertyValue("--text-mono").trim();



const LEAF_COLORS = chartPalette();



document.addEventListener("DOMContentLoaded", () => {

  const rows = BENCHMARK.compression_rows || [];

  const huffman = rows.find((r) => r.algorithm === "huffman");

  const rle = rows.find((r) => r.algorithm === "rle");



  const ctx = document.getElementById("compression-chart")?.getContext("2d");

  if (ctx) {

    new Chart(ctx, {

      type: "bar",

      data: {

        labels: rows.map((r) => (r.compression_name || r.algorithm).toUpperCase()),

        datasets: [

          {

            label: "Original (B)",

            data: rows.map((r) => r.original_bytes),

            backgroundColor: SURFACE,

            borderRadius: 4,

          },

          {

            label: "Compressed (B)",

            data: rows.map((r) => r.compressed_bytes),

            backgroundColor: rows.map((r) => (r.algorithm === "huffman" ? HUFFMAN : RLE)),

            borderRadius: 4,

          },

        ],

      },

      options: {

        responsive: true,

        maintainAspectRatio: false,

        plugins: { legend: { position: "bottom", labels: { color: TEXT_SEC } } },

        scales: {

          x: { grid: { color: BORDER }, ticks: { color: TEXT_SEC } },

          y: { title: { display: true, text: "bytes", color: TEXT_SEC }, grid: { color: BORDER } },

        },

      },

    });

  }



  if (huffman?.tree_data && typeof d3 !== "undefined") {

    const container = document.getElementById("huffman-tree");

    const W = container.clientWidth || 700;

    const H = 320;

    const svg = d3.select("#huffman-tree").append("svg").attr("width", W).attr("height", H);

    const root = d3.hierarchy(huffman.tree_data);

    d3.tree().size([W - 60, H - 60])(root);



    let leafIdx = 0;

    const leafColor = () => {

      const c = LEAF_COLORS[leafIdx % LEAF_COLORS.length];

      leafIdx += 1;

      return c;

    };

    const leafColorMap = new Map();

    root.descendants().forEach((d) => {

      if (d.data.char) leafColorMap.set(d, leafColor());

    });



    svg

      .selectAll(".link")

      .data(root.links())

      .enter()

      .append("path")

      .attr("fill", "none")

      .attr("stroke", (d) => leafColorMap.get(d.target) || BORDER)

      .attr("stroke-opacity", 0.45)

      .attr("stroke-width", 1.5)

      .attr("d", d3.linkVertical().x((d) => d.x + 30).y((d) => d.y + 30));



    const node = svg

      .selectAll(".node")

      .data(root.descendants())

      .enter()

      .append("g")

      .attr("transform", (d) => `translate(${d.x + 30},${d.y + 30})`);



    node

      .append("circle")

      .attr("r", 16)

      .attr("fill", (d) => (d.data.char ? `${leafColorMap.get(d)}33` : CARD))

      .attr("stroke", (d) => (d.data.char ? leafColorMap.get(d) : ACCENT))

      .attr("stroke-width", 1.5);



    node

      .append("text")

      .attr("text-anchor", "middle")

      .attr("dy", "0.35em")

      .attr("font-size", 10)

      .attr("font-family", "JetBrains Mono, monospace")

      .attr("fill", (d) => (d.data.char ? leafColorMap.get(d) : TEXT_SEC))

      .text((d) => d.data.char || d.data.freq);

  }



  const rleCtx = document.getElementById("rle-chart")?.getContext("2d");

  if (rleCtx && rle?.run_summary) {

    const runs = Object.entries(rle.run_summary)

      .sort((a, b) => b[1] - a[1])

      .slice(0, 10);

    const palette = chartPalette();

    new Chart(rleCtx, {

      type: "bar",

      data: {

        labels: runs.map(([sym]) => `'${sym}'`),

        datasets: [

          {

            label: "Run segments",

            data: runs.map(([, v]) => v),

            backgroundColor: runs.map((_, i) => palette[i % palette.length]),

            borderRadius: 4,

          },

        ],

      },

      options: {

        indexAxis: "y",

        responsive: true,

        maintainAspectRatio: false,

        plugins: { legend: { display: false } },

        scales: {

          x: { grid: { color: BORDER } },

          y: { grid: { display: false }, ticks: { color: MONO } },

        },

      },

    });

  }

});


