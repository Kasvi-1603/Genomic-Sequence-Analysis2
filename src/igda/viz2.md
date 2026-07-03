# IGDA — Build Frontend From Scratch
**Cursor instruction file. Read every section before writing a single file.**

---

## 0. What this project is

IGDA (Intelligent Genome & Data Anomaly Detection) is a Flask web app for a Design and Analysis of Algorithms (DAA) university lab project. It benchmarks 5 string-matching algorithms (Naive, KMP, Boyer–Moore–Horspool, Aho–Corasick, Levenshtein) and 2 compression codecs (Huffman, RLE) on genomic (FASTA) and plain text inputs. The goal is to compare algorithms empirically and find the best one for a given input.

The Python backend (`igda` package) is already complete. You are building a brand new Flask frontend — Option B from the backend docs: new Jinja2 templates calling `igda.*` directly in route handlers. No SPA, no React, no npm build step. Pure Flask + Jinja2 + vanilla JS + CDN libraries only.

**Delete or ignore any existing templates and static files. Build everything fresh.**

---

## 1. Backend integration — how to call igda

The `igda` package is already installed (`pip install -e ".[dev]"` from project root). Call it directly inside Flask route handlers.

```python
import igda
from igda import RunConfig

# List algorithms (for rendering dropdowns or metadata)
algorithms = igda.list_algorithms()        # returns AlgorithmInfo[]
algo_ids   = igda.list_algorithm_ids()     # ["naive","kmp","horspool","ahocorasick","edit_distance"]
codecs     = igda.list_compressions()      # CompressionInfo[]
codec_ids  = igda.list_compression_ids()   # ["huffman","rle"]

# Load input
text = igda.load_fasta_sequence(filepath)  # strips FASTA headers, returns string
text = igda.load_plain_text(filepath)
patterns = igda.normalize_patterns(["ATG", "TATAAA"], dedupe=True)

# Run full benchmark (all algos, all codecs, multiple trials)
config = RunConfig(
    warmup=1,
    trials=5,
    selected_algorithm_ids=[],    # empty = run all 5
    selected_compression_ids=[],  # empty = run both
    max_edits=1,                  # for edit_distance only
)
summary = igda.run_benchmark(text, patterns, config)
data = summary.as_public_dict()   # serialisable dict — pass to Jinja template

# Run single algorithm
result = igda.run_match("kmp", text, patterns)
result = igda.run_compression("huffman", text)
```

**Store results in Flask session after /run POST. All result pages read from session.**

Session keys to use:
```python
session['input_meta']          # dict: source, filename, length, patterns, max_edits
session['pattern_results']     # list of matcher result dicts
session['compression_results'] # list of codec result dicts
session['multi_n_results']     # list of {n, results} for growth chart on analysis page
```

---

## 2. New file structure to create

Create this structure inside `src/igda/viz/`:

```
src/igda/viz/
├── app_v3.py                        ← new Flask app (entrypoint)
├── static/
│   ├── css/
│   │   ├── base.css                 ← variables, reset, typography, sidebar
│   │   ├── home.css
│   │   ├── pattern.css
│   │   ├── compression.css
│   │   └── analysis.css
│   ├── js/
│   │   ├── home.js                  ← file drop, chip insert, form submit
│   │   ├── pattern.js               ← bar chart, table highlight
│   │   ├── compression.js           ← huffman tree SVG, rle chart
│   │   └── analysis.js              ← growth line chart, theory table
│   └── animations/
│       └── dna_animation.json       ← Lottie file (user will place manually)
└── templates_v3/
    ├── base.html                    ← shell: sidebar + content slot
    ├── home.html
    ├── pattern.html
    ├── compression.html
    └── analysis.html
```

---

## 3. Colour system — define as CSS variables in base.css

```css
:root {
  /* backgrounds */
  --bg-base:        #100D20;
  --bg-surface:     #1D1842;
  --bg-card:        #2A2460;
  --bg-card-hover:  #332D72;

  /* borders */
  --border:         #3D3870;
  --border-light:   #5550A0;

  /* brand / primary — rose pink */
  --primary:        #FDA1A2;
  --primary-dim:    #C4607E;
  --primary-glow:   rgba(253,161,162,0.12);

  /* semantic accents */
  --teal:           #1D9E75;   /* winner / success / best algo */
  --teal-light:     #5DCAA5;   /* teal hover */
  --amber:          #EF9F27;   /* secondary highlight, warnings */
  --deep-red:       #8E0D3C;   /* mutations / approximate matching ONLY */
  --deep-red-light: #C4365E;   /* hover state of deep-red elements */

  /* text */
  --text-primary:   #E2E0F0;
  --text-secondary: #9490C0;
  --text-tertiary:  #5A5580;
  --text-mono:      #A8D8A8;   /* DNA sequences, monospace data */

  /* algorithm colours — use consistently across ALL charts */
  --algo-naive:     #5A5580;   /* gray — baseline */
  --algo-kmp:       #FDA1A2;   /* rose pink */
  --algo-horspool:  #EF9F27;   /* amber */
  --algo-ac:        #1D9E75;   /* teal — often the winner */
  --algo-edit:      #8E0D3C;   /* deep red — approximate */
  --algo-huffman:   #1D9E75;   /* teal */
  --algo-rle:       #7F77DD;   /* muted purple */
}
```

**Never use hardcoded hex values in templates or JS — always reference these variables.**

---

## 4. Typography and dependencies

Add to `<head>` in base.html:

```html















```

Base font rules in base.css:
```css
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--bg-base);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.6;
}

code, .mono, .sequence {
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-mono);
}
```

---

## 5. Flask app — app_v3.py

```python
from flask import Flask, render_template, request, redirect, url_for, session
import igda
from igda import RunConfig
import os

app = Flask(__name__, template_folder='templates_v3', static_folder='static')
app.secret_key = 'igda-dev-secret'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/run', methods=['POST'])
def run():
    # 1. Get input text
    mode = request.form.get('input_mode', 'manual')
    if mode == 'fasta' and 'fasta_file' in request.files:
        f = request.files['fasta_file']
        tmp = f'/tmp/{f.filename}'
        f.save(tmp)
        text = igda.load_fasta_sequence(tmp)
        filename = f.filename
    else:
        text = request.form.get('manual_text', '').strip()
        filename = 'manual input'

    # 2. Limit length if requested
    prefix = request.form.get('prefix_chars', '')
    if prefix.isdigit():
        text = text[:int(prefix)]

    # 3. Get patterns
    raw_patterns = request.form.get('patterns', '')
    patterns = igda.normalize_patterns(
        [p.strip() for p in raw_patterns.split(',') if p.strip()],
        dedupe=True
    )

    # 4. Get config
    max_edits = int(request.form.get('max_edits', 1))

    # 5. Run full benchmark
    config = RunConfig(warmup=1, trials=5, selected_algorithm_ids=[], selected_compression_ids=[], max_edits=max_edits)
    summary = igda.run_benchmark(text, patterns, config)
    data = summary.as_public_dict()

    # 6. Run multi-n benchmark for growth chart (5 sizes)
    multi_n = []
    sizes = [1000, 5000, 10000, 25000, min(50000, len(text))]
    for n in sizes:
        if n > len(text):
            continue
        cfg_n = RunConfig(warmup=0, trials=3, selected_algorithm_ids=[], selected_compression_ids=[], max_edits=max_edits)
        s = igda.run_benchmark(text[:n], patterns, cfg_n)
        multi_n.append({'n': n, 'results': s.as_public_dict()})

    # 7. Store in session
    session['input_meta'] = {
        'source': mode,
        'filename': filename,
        'length': len(text),
        'patterns': patterns,
        'max_edits': max_edits,
    }
    session['benchmark'] = data
    session['multi_n'] = multi_n

    return redirect(url_for('pattern'))

@app.route('/pattern')
def pattern():
    if 'benchmark' not in session:
        return redirect(url_for('home'))
    return render_template('pattern.html',
        meta=session['input_meta'],
        benchmark=session['benchmark'])

@app.route('/compression')
def compression():
    if 'benchmark' not in session:
        return redirect(url_for('home'))
    return render_template('compression.html',
        meta=session['input_meta'],
        benchmark=session['benchmark'])

@app.route('/analysis')
def analysis():
    if 'benchmark' not in session:
        return redirect(url_for('home'))
    return render_template('analysis.html',
        meta=session['input_meta'],
        benchmark=session['benchmark'],
        multi_n=session.get('multi_n', []))

if __name__ == '__main__':
    app.run(debug=True, port=5002)
```

---

## 6. base.html — shell template

Fixed 240px sidebar + scrollable main content. Sidebar has navigation, wizard progress, and input metadata display.

```html



  
  
  IGDA — {% block title %}{% endblock %}
  
  
  {% block css %}{% endblock %}



  
    
      IGDA
      Genomic anomaly detection
    

    
      
         Home
      
      
         Pattern matching
      
      
         Compression
      
      
         Analysis
      
    

    
    
      {% set steps = ['home','pattern','compression','analysis'] %}
      {% set step_labels = ['Input','Matching','Compression','Analysis'] %}
      {% for s in steps %}
      
        
        {{ step_labels[loop.index0] }}
      
      {% endfor %}
    

    
    {% if session.get('input_meta') %}
    
      Input loaded
      {{ session.input_meta.filename }}
      {{ "{:,}".format(session.input_meta.length) }} chars
      {{ session.input_meta.patterns | length }} pattern(s)
    
    {% endif %}
  

  
    {% block content %}{% endblock %}
  

  {% block js %}{% endblock %}


```

### Sidebar CSS (in base.css):

```css
.sidebar {
  position: fixed;
  top: 0; left: 0;
  width: 240px;
  height: 100vh;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 24px 16px;
  overflow-y: auto;
  z-index: 100;
}

.sidebar-brand {
  margin-bottom: 32px;
}
.brand-name {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: var(--primary);
  letter-spacing: 0.05em;
}
.brand-sub {
  display: block;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 32px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
  border-left: 3px solid transparent;
}
.nav-item:hover {
  background: var(--bg-card);
  color: var(--text-primary);
}
.nav-item.active {
  background: var(--bg-card);
  color: var(--primary);
  border-left-color: var(--primary);
  font-weight: 500;
}
.nav-item.disabled {
  opacity: 0.35;
  pointer-events: none;
}
.nav-item .ti { font-size: 16px; }

/* Wizard progress */
.sidebar-progress {
  margin-bottom: 24px;
  padding: 0 4px;
}
.progress-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 0;
}
.progress-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--border);
  flex-shrink: 0;
  transition: background 0.2s, border-color 0.2s;
}
.progress-step.done .progress-dot {
  background: var(--primary-dim);
  border-color: var(--primary-dim);
}
.progress-step.current .progress-dot {
  background: var(--primary);
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}
.progress-label {
  font-size: 11px;
  color: var(--text-tertiary);
}
.progress-step.current .progress-label { color: var(--primary); }
.progress-step.done .progress-label { color: var(--text-secondary); }

/* Input meta */
.sidebar-meta {
  margin-top: auto;
  padding: 12px;
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
}
.meta-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  margin-bottom: 6px;
}
.meta-value {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

/* Main content offset */
.main-content {
  margin-left: 240px;
  padding: 40px 48px;
  min-height: 100vh;
  max-width: 1140px;
}
```

---

## 7. home.html

**Purpose:** Load input, enter patterns, trigger analysis. DNA animation is the hero element.

```html
{% extends "base.html" %}
{% block title %}Home{% endblock %}
{% block css %}

{% endblock %}

{% block content %}


  
  
    
    
    
  

  IGDA
  Intelligent Genome & Data Anomaly Detection
  
    Benchmark 5 string-matching algorithms and 2 compression codecs on your genomic
    or text data. Find the fastest, most efficient algorithm for your input — automatically.
  





  

    
    
      
         FASTA / .txt file
      
      
         Manual text
      
    
    

    
    
      
        
        Drop .fasta or .txt file here
        or browse
        
        
      
      
        Limit to first
        
        characters (leave blank for full file)
      
    

    
    
      
      One sequence. Multiple sequences: use FASTA mode.
    

    
    

    
    
      
        Patterns to search
        (comma-separated)
      
      
      
        Quick add:
        {% for motif in ['ATG', 'TAA', 'TGA', 'TATAAA', 'GCGC', 'AAAA'] %}
        {{ motif }}
        {% endfor %}
      
    

    
    

    
    
      Max edit distance
        (for approximate / mutation matching)
      
      
        {% for v in [0, 1, 2, 3] %}
        
          <input type="radio" name="max_edits" value="{{ v }}" {% if v == 1 %}checked{% endif %}>
          {{ v }}
          {% if v == 0 %}exact only
          {% elif v == 1 %}SNPs
          {% elif v == 2 %}small indels
          {% elif v == 3 %}multiple variants
          {% endif %}
        
        {% endfor %}
      
    

    
    
      Analyse 
    
    
      
      Running benchmark across 5 matchers + 2 codecs...
    

  




  
    
    
      5 matchers race
      Naive, KMP, Horspool, Aho–Corasick, Levenshtein
    
  
  
    
    
      2 codecs compared
      Huffman coding vs Run-Length Encoding
    
  
  
    
    
      Fully automatic
      All algorithms run on identical input
    
  

{% endblock %}

{% block js %}

{% endblock %}
```

### home.js behaviour

```javascript
// Mode tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const mode = btn.dataset.mode;
    document.getElementById('input_mode').value = mode;
    document.getElementById('panel-fasta').classList.toggle('hidden', mode !== 'fasta');
    document.getElementById('panel-manual').classList.toggle('hidden', mode !== 'manual');
  });
});

// File drop zone
const dz = document.getElementById('dropzone');
const fi = document.getElementById('fasta_file');
const fn = document.getElementById('fasta-filename');

dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
dz.addEventListener('drop', e => {
  e.preventDefault();
  dz.classList.remove('drag-over');
  fi.files = e.dataTransfer.files;
  fn.textContent = fi.files[0]?.name || '';
  fn.style.display = 'block';
});
fi.addEventListener('change', () => {
  fn.textContent = fi.files[0]?.name || '';
  fn.style.display = fi.files.length ? 'block' : 'none';
});

// Motif chips
document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const ta = document.getElementById('patterns-input');
    const current = ta.value.trim();
    const motif = chip.dataset.motif;
    ta.value = current ? `${current}, ${motif}` : motif;
  });
});

// Loading state on submit
document.getElementById('analyse-form').addEventListener('submit', () => {
  document.getElementById('analyse-btn').classList.add('hidden');
  document.getElementById('loading').classList.remove('hidden');
});

// CSS DNA fallback — generate helix strands if Lottie fails
function buildDnaFallback() {
  const container = document.getElementById('dna-fallback');
  if (!container) return;
  for (let i = 0; i < 20; i++) {
    const strand = document.createElement('div');
    strand.className = 'dna-strand';
    strand.style.cssText = `
      left: ${i * 13}px;
      height: ${40 + Math.sin(i * 0.5) * 30}px;
      animation-delay: ${i * 0.09}s;
    `;
    container.appendChild(strand);
  }
}
buildDnaFallback();
```

---

## 8. pattern.html

**Purpose:** Show the 5-algorithm race results. All matchers have run; display winner, bar chart, detail table, complexity table, match location strip.

Pass this data from Flask: `benchmark` dict (from `summary.as_public_dict()`), `meta` dict.

**Template structure:**

```html
{% extends "base.html" %}
{% block title %}Pattern matching{% endblock %}
{% block css %}

{% endblock %}

{% block content %}


  Pattern matching results
  
    {{ meta.filename }} · {{ "{:,}".format(meta.length) }} chars ·
    {{ meta.patterns | join(', ') }} · 5 trials
  




  
  {% set exact = benchmark.best_exact_matcher %}
  
     Best exact matcher
    {{ exact.algorithm }}
    
      {{ "%.2f"|format(exact.time_ms_median) }}ms median ·
      {{ exact.match_count }} matches
    
  

  
  {% set approx = benchmark.best_approx_matcher %}
  {% if approx %}
  
     Best approx matcher
    {{ approx.algorithm }}
    
      {{ "%.2f"|format(approx.time_ms_median) }}ms median ·
      {{ approx.match_count }} matches (incl. near-matches)
    
  
  {% endif %}




  
    Runtime comparison
    
      Median
      Min / Max / p95
    
  
  
  
    Approximate matcher (EditDistance) shown on separate scale — O(n·m²) makes it
    significantly slower by design.
  




  Detailed results
  
    
      
        Algorithm
        Type
        Median (ms)
        Min
        Max
        p95
        Matches
      
    
    
      {% for row in benchmark.matcher_rows %}
      
        
          
          {{ row.algorithm }}
          {% if row.is_best_exact or row.is_best_approx %}
            ★ best
          {% endif %}
        
        
          {% if row.match_kind == 'approximate' %}
            approximate
          {% else %}
            exact
          {% endif %}
        
        
          {{ "%.2f"|format(row.time_ms_median) }}
        
        {{ "%.2f"|format(row.time_ms_min) }}
        {{ "%.2f"|format(row.time_ms_max) }}
        {{ "%.2f"|format(row.time_ms_p95) }}
        {{ row.match_count }}
      
      {% endfor %}
    
  
  * Approximate matches include near-matches within edit distance {{ meta.max_edits }}.




  Theoretical complexity
  
    
      AlgorithmTime complexitySpaceBest for
    
    
      NaiveO(n·m·t)O(1)Baseline / tiny inputs
      KMPO(n·t + Σm)O(m)Linear scan, no backtrack
      Boyer–Moore–HorspoolO(n·m) worst, sublinear avgO(|Σ|)Long patterns, large alphabets
      Aho–CorasickO(n + m + z)O(m)Many patterns, one pass
      EditDistanceO(n·m²)O(m)Mutation-tolerant search
    
  



{% if benchmark.match_positions %}

  Match locations
  {% for pattern, positions in benchmark.match_positions.items() %}
  
    {{ pattern }}
    
      {% for pos in positions[:20] %}
      {{ pos }}
      {% endfor %}
      {% if positions | length > 20 %}
      +{{ positions | length - 20 }} more
      {% endif %}
    
  
  {% endfor %}

{% endif %}



  
    Next: Compression 
  

{% endblock %}

{% block js %}


  const BENCHMARK = {{ benchmark | tojson }};
  const META = {{ meta | tojson }};
  const ALGO_COLORS = {
    naive:        '#5A5580',
    kmp:          '#FDA1A2',
    horspool:     '#EF9F27',
    ahocorasick:  '#1D9E75',
    edit_distance:'#8E0D3C',
  };

{% endblock %}
```

### pattern.js — Chart.js bar chart

```javascript
// Horizontal bar chart — exact matchers
// EditDistance on a separate chart with its own scale

document.addEventListener('DOMContentLoaded', () => {
  const rows = BENCHMARK.matcher_rows || [];
  const exact = rows.filter(r => r.match_kind === 'exact');
  const approx = rows.filter(r => r.match_kind === 'approximate');

  const ctx = document.getElementById('runtime-chart').getContext('2d');

  Chart.defaults.color = '#9490C0';
  Chart.defaults.borderColor = '#3D3870';

  const chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: exact.map(r => r.algorithm),
      datasets: [{
        label: 'Median (ms)',
        data: exact.map(r => r.time_ms_median),
        backgroundColor: exact.map(r =>
          (r.is_best_exact ? '#1D9E75' : ALGO_COLORS[r.algorithm] || '#FDA1A2')
        ),
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const row = exact[ctx.dataIndex];
              return [
                `Median: ${row.time_ms_median.toFixed(2)}ms`,
                `Min: ${row.time_ms_min.toFixed(2)}ms`,
                `Max: ${row.time_ms_max.toFixed(2)}ms`,
                `Matches: ${row.match_count}`,
              ];
            }
          }
        }
      },
      scales: {
        x: { title: { display: true, text: 'milliseconds' }, grid: { color: '#3D3870' } },
        y: { grid: { display: false } }
      }
    }
  });

  // Colour the algo-dot spans in the table
  document.querySelectorAll('.algo-dot').forEach(dot => {
    dot.style.background = ALGO_COLORS[dot.dataset.algo] || '#5A5580';
  });

  // Toggle median / range
  document.getElementById('btn-median').addEventListener('click', () => {
    chart.data.datasets[0].data = exact.map(r => r.time_ms_median);
    chart.update();
    document.getElementById('btn-median').classList.add('active');
    document.getElementById('btn-range').classList.remove('active');
  });
  document.getElementById('btn-range').addEventListener('click', () => {
    chart.data.datasets = [
      { label: 'Min',    data: exact.map(r => r.time_ms_min),    backgroundColor: '#3D3870', borderRadius: 4 },
      { label: 'Median', data: exact.map(r => r.time_ms_median), backgroundColor: exact.map(r => ALGO_COLORS[r.algorithm] || '#FDA1A2'), borderRadius: 4 },
      { label: 'p95',    data: exact.map(r => r.time_ms_p95),    backgroundColor: '#5550A0', borderRadius: 4 },
    ];
    chart.update();
    document.getElementById('btn-range').classList.add('active');
    document.getElementById('btn-median').classList.remove('active');
  });
});
```

---

## 9. compression.html

**Purpose:** Show Huffman vs RLE results. Codec cards, comparison bar chart, Huffman code table, Huffman tree visualisation, RLE run chart.

**Key template elements:**

```html
{% extends "base.html" %}
{% block title %}Compression{% endblock %}
{% block css %}

{% endblock %}

{% block content %}

  Compression results
  Huffman coding vs Run-Length Encoding · same input




  {% for codec in benchmark.compression_rows %}
  
    {% if codec.is_best %}★ Best compression{% endif %}
    {{ codec.algorithm | upper }}
    
      {{ "%.1f"|format(codec.percent_saved) }}% saved
    
    
      
        Original
        {{ "{:,}".format(codec.original_bytes) }} B
      
      
        Compressed
        {{ "{:,}".format(codec.compressed_bytes) }} B
      
      
        Time
        {{ "%.2f"|format(codec.time_ms_median) }}ms
      
    
  
  {% endfor %}




  Bytes saved comparison
  



{% set huffman = benchmark.compression_rows | selectattr('algorithm','equalto','huffman') | first %}
{% if huffman and huffman.codebook %}

  Huffman code table
  
    
      SymbolFrequencyCodeBitsFrequency bar
    
    
      {% for symbol, code in huffman.codebook.items() | sort(attribute='1') %}
      
        {{ symbol }}
        {{ huffman.frequencies.get(symbol, 0) }}
        {{ code }}
        {{ code | length }}
        
          
        
      
      {% endfor %}
    
  




  Huffman tree
  

{% endif %}



  RLE — run distribution
  




  Theoretical complexity
  
    AlgorithmTimeSpaceBest for
    
      HuffmanO(n + k log k)O(k)Skewed symbol frequencies (AT-rich DNA)
      RLEO(n)O(r) runsHomopolymer runs (AAAAAAA…)
    
  



  
     Back
  
  
    Next: Analysis 
  

{% endblock %}

{% block js %}


  const BENCHMARK = {{ benchmark | tojson }};

{% endblock %}
```

### compression.js — Huffman tree with D3

```javascript
document.addEventListener('DOMContentLoaded', () => {
  const rows = BENCHMARK.compression_rows || [];
  const huffman = rows.find(r => r.algorithm === 'huffman');
  const rle     = rows.find(r => r.algorithm === 'rle');

  // Compression comparison bar chart
  const ctx = document.getElementById('compression-chart')?.getContext('2d');
  if (ctx) {
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: rows.map(r => r.algorithm.toUpperCase()),
        datasets: [
          {
            label: 'Original (B)',
            data: rows.map(r => r.original_bytes),
            backgroundColor: '#3D3870',
            borderRadius: 4,
          },
          {
            label: 'Compressed (B)',
            data: rows.map(r => r.compressed_bytes),
            backgroundColor: rows.map(r => r.algorithm === 'huffman' ? '#1D9E75' : '#7F77DD'),
            borderRadius: 4,
          }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } },
        scales: {
          x: { grid: { color: '#3D3870' } },
          y: { title: { display: true, text: 'bytes' }, grid: { color: '#3D3870' } }
        }
      }
    });
  }

  // Huffman tree with D3
  if (huffman?.tree_data) {
    const container = document.getElementById('huffman-tree');
    const W = container.clientWidth || 700, H = 320;
    const svg = d3.select('#huffman-tree')
      .append('svg').attr('width', W).attr('height', H);

    const root = d3.hierarchy(huffman.tree_data);
    const treeLayout = d3.tree().size([W - 60, H - 60]);
    treeLayout(root);

    svg.selectAll('.link')
      .data(root.links()).enter()
      .append('path').attr('class','link')
      .attr('fill','none').attr('stroke','#3D3870').attr('stroke-width',1.5)
      .attr('d', d3.linkVertical().x(d => d.x + 30).y(d => d.y + 30));

    const node = svg.selectAll('.node')
      .data(root.descendants()).enter()
      .append('g').attr('transform', d => `translate(${d.x+30},${d.y+30})`);

    node.append('circle').attr('r', 18)
      .attr('fill', d => d.data.char ? '#1D1842' : '#2A2460')
      .attr('stroke', d => d.data.char ? '#FDA1A2' : '#3D3870')
      .attr('stroke-width', 1.5);

    node.append('text').attr('text-anchor','middle').attr('dy','0.35em')
      .attr('font-size', 11).attr('font-family','JetBrains Mono, monospace')
      .attr('fill', d => d.data.char ? '#FDA1A2' : '#9490C0')
      .text(d => d.data.char || d.data.freq);
  }

  // RLE run chart
  const rleCtx = document.getElementById('rle-chart')?.getContext('2d');
  if (rleCtx && rle?.run_summary) {
    const runs = Object.entries(rle.run_summary).slice(0, 10);
    new Chart(rleCtx, {
      type: 'bar',
      data: {
        labels: runs.map(([sym]) => `'${sym}'`),
        datasets: [{
          label: 'Run occurrences',
          data: runs.map(([,v]) => v),
          backgroundColor: '#7F77DD',
          borderRadius: 4,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#3D3870' } },
          y: { grid: { display: false } }
        }
      }
    });
  }
});
```

---

## 10. analysis.html

**Purpose:** Synthesise everything. Overall verdict, runtime growth chart across multiple n values, theory vs empirical table, when-to-use guidance cards, input characteristics.

```html
{% extends "base.html" %}
{% block title %}Analysis{% endblock %}
{% block css %}

{% endblock %}

{% block content %}

  Analysis & verdict
  Based on your input: {{ "{:,}".format(meta.length) }} chars · {{ meta.patterns | length }} patterns




  Overall verdict
  
    
      Best exact matcher
      
        
        {{ benchmark.best_exact_matcher.algorithm }}
      
    
    
      Best approximate matcher
      
        
        EditDistance
      
    
    
      Best compression
      
        
        {{ benchmark.best_compression.algorithm | upper }}
      
    
  
  
    For {{ meta.length | round(-3) | int | string }}-char input with {{ meta.patterns | length }} pattern(s):
    use {{ benchmark.best_exact_matcher.algorithm }} for exact motif search.
    Switch to EditDistance when mutations or sequencing errors are expected.
  




  Runtime vs input length
  Each algorithm benchmarked at 5 input sizes — shows empirical growth rate
  




  Theory vs empirical
  
    
      AlgorithmTheoretical timeActual (ms)Speedup vs Naive
    
    
      {% set naive_time = benchmark.matcher_rows | selectattr('algorithm','equalto','naive') | map(attribute='time_ms_median') | first | default(1) %}
      {% for row in benchmark.matcher_rows %}
      
        {{ row.algorithm }}
        
          {% if row.algorithm == 'naive' %}O(n·m·t)
          {% elif row.algorithm == 'kmp' %}O(n·t + Σm)
          {% elif row.algorithm == 'horspool' %}O(n·m) avg sublinear
          {% elif row.algorithm == 'ahocorasick' %}O(n + m + z)
          {% elif row.algorithm == 'edit_distance' %}O(n·m²)
          {% endif %}
        
        
          {{ "%.2f"|format(row.time_ms_median) }}
        
        
          {% set ratio = naive_time / row.time_ms_median if row.time_ms_median > 0 else 1 %}
          
            {{ "%.1f"|format(ratio) }}×
          
        
      
      {% endfor %}
    
  




  When to use which algorithm
  
    
      Naive
      Debugging, tiny inputs
      Baseline. Never the best in production but simplest to verify correctness against.
    
    
      KMP
      Linear, predictable
      Guaranteed O(n+m) per pattern. Good when you have one pattern and need consistent performance.
    
    
      Horspool
      Long patterns, large alphabet
      Sublinear in practice on DNA (4-symbol alphabet). Skips characters aggressively on mismatch.
    
    
      Aho–Corasick
      Multiple patterns at once
      Single O(n) pass finds all patterns simultaneously. The right choice for 3+ patterns on long sequences.
    
    
      EditDistance
      Mutations, variants, errors
      Finds near-matches within max_edits. SNP detection (1 edit), small indels (2 edits). Slow but necessary.
    
  




  Input characteristics
  
    
      Length
      {{ "{:,}".format(meta.length) }}
    
    
      Patterns
      {{ meta.patterns | join(', ') }}
    
    
      Max edit distance
      {{ meta.max_edits }}
    
    
      Source
      {{ meta.source }}
    
  




  
     Run again with new input
  

{% endblock %}

{% block js %}


  const BENCHMARK = {{ benchmark | tojson }};
  const MULTI_N   = {{ multi_n | tojson }};
  const ALGO_COLORS = {
    naive:        '#5A5580',
    kmp:          '#FDA1A2',
    horspool:     '#EF9F27',
    ahocorasick:  '#1D9E75',
    edit_distance:'#8E0D3C',
  };

{% endblock %}
```

### analysis.js — Growth line chart

```javascript
document.addEventListener('DOMContentLoaded', () => {
  const ctx = document.getElementById('growth-chart')?.getContext('2d');
  if (!ctx || !MULTI_N.length) return;

  const algoIds = ['naive','kmp','horspool','ahocorasick','edit_distance'];
  const ns = MULTI_N.map(d => d.n);

  const datasets = algoIds.map(id => ({
    label: id,
    data: MULTI_N.map(d => {
      const row = (d.results.matcher_rows || []).find(r => r.algorithm === id);
      return row ? parseFloat(row.time_ms_median.toFixed(3)) : null;
    }),
    borderColor: ALGO_COLORS[id],
    backgroundColor: ALGO_COLORS[id] + '22',
    tension: 0.3,
    borderWidth: id === 'ahocorasick' ? 2.5 : 1.5,
    pointRadius: 4,
    pointHoverRadius: 6,
    fill: false,
  }));

  new Chart(ctx, {
    type: 'line',
    data: { labels: ns.map(n => n.toLocaleString()), datasets },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(2)}ms`
          }
        }
      },
      scales: {
        x: { title: { display: true, text: 'input length (chars)' }, grid: { color: '#3D3870' } },
        y: { title: { display: true, text: 'median time (ms)' }, grid: { color: '#3D3870' } }
      }
    }
  });
});
```

---

## 11. Shared CSS patterns (add to base.css)

```css
/* Cards */
.chart-card, .table-card, .match-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}

.card-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 16px;
}

/* Page header */
.page-header { margin-bottom: 32px; }
.page-title { font-size: 24px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.page-sub { font-size: 13px; color: var(--text-secondary); }

/* Tables */
.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.results-table th {
  text-align: left;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
}
.results-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  color: var(--text-secondary);
}
.results-table tr:hover td { background: var(--bg-card-hover); }
.row-winner td { color: var(--text-primary); }
.row-winner td:first-child { border-left: 3px solid var(--teal); }
.row-approx td:first-child { border-left: 3px solid var(--deep-red); }
.num { text-align: right; font-family: 'JetBrains Mono', monospace; }
.num-best { color: var(--teal-light) !important; font-weight: 500; }

/* Badges */
.badge-winner {
  display: inline-block; font-size: 10px; padding: 2px 6px;
  border-radius: 4px; background: rgba(29,158,117,0.15);
  color: var(--teal-light); margin-left: 6px; font-weight: 500;
}
.badge-exact {
  font-size: 11px; padding: 2px 6px; border-radius: 4px;
  background: rgba(253,161,162,0.1); color: var(--primary);
}
.badge-approx {
  font-size: 11px; padding: 2px 6px; border-radius: 4px;
  background: rgba(142,13,60,0.2); color: var(--deep-red-light);
}

/* Buttons */
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 12px 24px; border-radius: 8px;
  background: var(--primary); color: #100D20;
  font-size: 14px; font-weight: 600; text-decoration: none;
  border: none; cursor: pointer; transition: background 0.15s;
}
.btn-primary:hover { background: var(--primary-dim); color: var(--text-primary); }
.btn-secondary {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 12px 24px; border-radius: 8px;
  background: transparent; color: var(--text-secondary);
  font-size: 14px; text-decoration: none;
  border: 1px solid var(--border); cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.btn-secondary:hover { border-color: var(--border-light); color: var(--text-primary); }

/* Page nav */
.page-nav { display: flex; justify-content: flex-end; gap: 12px; margin-top: 32px; }

/* Loading spinner */
.spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
.hidden { display: none !important; }

/* Section divider */
.section-divider { height: 1px; background: var(--border); margin: 20px 0; }
```

---

## 12. Build order for Cursor

Build in this exact order — each step depends on the previous:

1. `base.css` — variables and reset (no template yet, just the CSS file)
2. `app_v3.py` — Flask routes skeleton with session handling
3. `base.html` — sidebar shell, test it renders with a dummy route
4. `home.html` + `home.css` + `home.js` — test form POST to /run works end-to-end
5. `pattern.html` + `pattern.css` + `pattern.js` — test chart renders with real data
6. `compression.html` + `compression.css` + `compression.js` — test huffman tree + rle chart
7. `analysis.html` + `analysis.css` + `analysis.js` — test growth chart with multi_n data
8. Final pass: mobile responsiveness (sidebar collapse at 900px)

---

## 13. Important notes for Cursor

- **Never use hardcoded hex colours in templates or JS.** Always reference CSS variables.
- **The `igda` package is already installed.** Do not reimplement any algorithm logic.
- **All charts use Chart.js 4.x** loaded from CDN. No npm install.
- **D3 is only for the Huffman tree SVG.** All other charts are Chart.js.
- **The Lottie player has an `onerror` fallback** — always include the CSS fallback helix `#dna-fallback` div alongside the lottie-player element.
- **Use `session.get()` with defaults** — result pages should gracefully redirect to home if session is empty, not crash.
- **`benchmark.as_public_dict()`** returns a dict — check the actual keys by printing it during development. The template variable names above assume a reasonable structure; adjust field names to match the actual dict.
- **Run the app with** `python src/igda/viz/app_v3.py` from the project root with the venv active.
- **Flask secret key** — change `'igda-dev-secret'` to a real random key before any deployment.
- **Test data** — use `data/raw/genomic_sample.txt` as the test FASTA file. Patterns: `ATG,TATAAA,GCGC`.

---

*End of build instructions. Start with step 1 in section 12.*