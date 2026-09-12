const COLORS = { teal: "#1F6F5C", gold: "#B98C2E", fail: "#A8432F", ink: "#1C2321", line: "#DAD6CB" };

google.charts.load("current", { packages: ["geochart", "table"] });

fetch("output.json")
  .then((r) => r.json())
  .then((data) => {
    google.charts.setOnLoadCallback(() => render(data));
  });

function render(data) {
  renderOverview(data);
  renderDescriptive(data);
  renderProbability(data);
  renderSampling(data);
  renderCharts(data);
  renderTable(data);
}

/* ---------------------------------------------------------- helpers */
function statBlock(label, value, unit) {
  return `<div class="stat-block"><div class="label">${label}</div>
    <div class="value">${value}${unit ? ` <small>${unit}</small>` : ""}</div></div>`;
}

/* ---------------------------------------------------- 1. Overview */
function renderOverview(data) {
  const el = document.getElementById("overview-cards");
  el.innerHTML =
    statBlock("Students", data.meta.n_students) +
    statBlock("Subjects tracked", data.meta.subjects.length) +
    statBlock("Semesters", data.meta.semesters.length) +
    statBlock("Missing marks imputed", data.missing_value_treatment.marks_missing_before) +
    statBlock("Pass mark threshold", data.meta.pass_mark) +
    statBlock("Analytics types applied", "Descriptive, Predictive, Prescriptive");
}

/* ------------------------------------------------- 2. Descriptive */
function renderDescriptive(data) {
  const subjectSelect = document.getElementById("subjectSelect");
  const semesterSelect = document.getElementById("semesterSelect");
  data.meta.subjects.forEach((s) => subjectSelect.add(new Option(s, s)));
  data.meta.semesters.forEach((s) => semesterSelect.add(new Option("Semester " + s, s)));

  function update() {
    const sub = subjectSelect.value;
    const sem = "sem" + semesterSelect.value;
    const stats = data.descriptive_stats[sem][sub];
    document.getElementById("descriptive-cards").innerHTML =
      statBlock("Mean", stats.mean) +
      statBlock("Median", stats.median) +
      statBlock("Std Deviation", stats.std_dev) +
      statBlock("Q1 / Q3", `${stats.q1} / ${stats.q3}`) +
      statBlock("Variation (max-min)", stats.max_minus_min) +
      statBlock("Skewness / Kurtosis", `${stats.skewness} / ${stats.kurtosis}`);
  }
  subjectSelect.addEventListener("change", update);
  semesterSelect.addEventListener("change", update);
  update();

  drawColumnChart("semTrendCanvas", data.meta.semesters.map((s) => "Sem " + s),
    data.semester_averages, COLORS.teal, "Avg mark");
}

/* -------------------------------------------------- 3. Probability */
function renderProbability(data) {
  const pp = data.probability.pass_probability_per_subject;
  drawBarSVG("passProbSvg", Object.keys(pp), Object.values(pp), COLORS.teal, true);

  const pmf = data.probability.binomial.pmf_k_subjects_passed;
  drawBarSVG("binomialSvg", Object.keys(pmf).map((k) => k + " passed"), Object.values(pmf), COLORS.gold, false);

  const b = data.probability.bayes_theorem;
  document.getElementById("bayesPanel").innerHTML = `
    <strong>Bayes&rsquo; theorem &mdash; city vs. passing all Sem-1 subjects</strong>
    <table style="margin-top:10px;">
      <tr><td>P(pass all Sem-1 subjects)</td><td class="num">${b["P(pass_all_sem1)"]}</td></tr>
      <tr><td>P(city = Vapi)</td><td class="num">${b["P(city=Vapi)"]}</td></tr>
      <tr><td>P(pass all Sem-1 | city = Vapi)</td><td class="num">${b["P(pass_all_sem1 | city=Vapi)"]}</td></tr>
      <tr><td>P(city = Vapi | pass all Sem-1) &mdash; via Bayes&rsquo; theorem</td>
          <td class="num">${b["P(city=Vapi | pass_all_sem1) [via Bayes]"]}</td></tr>
    </table>`;
}

/* --------------------------------------------- 4. Sampling / CLT */
function renderSampling(data) {
  const s = data.sampling_estimation;
  document.getElementById("sampling-cards").innerHTML =
    statBlock("Population mean", s.population_mean) +
    statBlock("Population std dev", s.population_std_dev) +
    statBlock("Mean of sample means (CLT)", s.clt_demo.mean_of_sample_means) +
    statBlock("Std dev of sample means", s.clt_demo.std_dev_of_sample_means) +
    statBlock("MLE estimate (mu, sigma^2)", `${s.mle_estimate.estimated_mu}, ${s.mle_estimate.estimated_sigma_squared}`) +
    statBlock("Required sample size (95% CI, ±3)", s.required_sample_size_95pct_ci_pm3marks);

  drawHistogram("cltCanvas", s.clt_demo.histogram.bins, s.clt_demo.histogram.counts, COLORS.gold);
}

/* ---------------------------------------------- 5&7. Visualizations */
function renderCharts(data) {
  drawPieSVG("genderPieSvg", data.gender_distribution);

  const rows = Object.entries(data.city_distribution).map(([city, count]) => [city, count]);
  const table = google.visualization.arrayToDataTable([["City", "Students"], ...rows]);
  const chart = new google.visualization.GeoChart(document.getElementById("geo_chart_div"));
  chart.draw(table, {
    region: "IN",
    resolution: "provinces",
    colorAxis: { colors: ["#E8E4D6", COLORS.teal] },
    backgroundColor: "transparent",
  });
}

/* -------------------------------------------------- 6. Tabular data */
function renderTable(data) {
  const subs = data.meta.subjects, sems = data.meta.semesters;
  const thead = document.querySelector("#studentsTable thead");
  const tbody = document.querySelector("#studentsTable tbody");

  let headerRow = "<tr><th>Enrollment No.</th><th>Name</th><th>Gender</th><th>City</th>";
  sems.forEach((s) => subs.forEach((sub) => (headerRow += `<th>S${s}-${sub}</th>`)));
  headerRow += "</tr>";
  thead.innerHTML = headerRow;

  tbody.innerHTML = data.students_table
    .map((row) => {
      let cells = `<td>${row.enrollment_no}</td><td>${row.name}</td><td>${row.gender}</td><td>${row.city}</td>`;
      sems.forEach((s) =>
        subs.forEach((sub) => {
          const v = row[`sem${s}_${sub}`];
          const cls = v < data.meta.pass_mark ? "mark-fail" : "mark-pass";
          cells += `<td class="num ${cls}">${v}</td>`;
        })
      );
      return `<tr>${cells}</tr>`;
    })
    .join("");
}

/* ============================================================
   Chart primitives — hand-built on Canvas / SVG (no library)
   ============================================================ */

function drawColumnChart(canvasId, labels, values, color, yLabel) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height, pad = 46;
  ctx.clearRect(0, 0, W, H);

  const max = Math.max(...values) * 1.15;
  const barW = (W - pad * 2) / values.length * 0.6;
  const gap = (W - pad * 2) / values.length;

  ctx.strokeStyle = COLORS.line;
  ctx.beginPath();
  ctx.moveTo(pad, H - pad);
  ctx.lineTo(W - 20, H - pad);
  ctx.stroke();

  values.forEach((v, i) => {
    const x = pad + i * gap + (gap - barW) / 2;
    const h = ((H - pad * 2) * v) / max;
    const y = H - pad - h;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, barW, h);
    ctx.fillStyle = COLORS.ink;
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(labels[i], x + barW / 2, H - pad + 16);
    ctx.fillText(v.toFixed(1), x + barW / 2, y - 6);
  });
}

function drawHistogram(canvasId, bins, counts, color) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height, pad = 46;
  ctx.clearRect(0, 0, W, H);

  const max = Math.max(...counts) * 1.15;
  const barW = (W - pad * 2) / counts.length * 0.85;
  const gap = (W - pad * 2) / counts.length;

  ctx.strokeStyle = COLORS.line;
  ctx.beginPath();
  ctx.moveTo(pad, H - pad);
  ctx.lineTo(W - 20, H - pad);
  ctx.stroke();

  counts.forEach((c, i) => {
    const x = pad + i * gap + (gap - barW) / 2;
    const h = ((H - pad * 2) * c) / max;
    const y = H - pad - h;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, barW, h);
    if (i % 2 === 0) {
      ctx.fillStyle = COLORS.ink;
      ctx.font = "10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(bins[i], x + barW / 2, H - pad + 14);
    }
  });
  ctx.fillStyle = COLORS.ink;
  ctx.font = "12px sans-serif";
  ctx.textAlign = "left";
  ctx.fillText("x-axis: sample mean value  |  y-axis: frequency out of 500 samples", pad, 20);
}

function drawBarSVG(svgId, labels, values, color, asPercent) {
  const svg = document.getElementById(svgId);
  const W = 420, H = 260, pad = 40;
  const max = Math.max(...values) * 1.2 || 1;
  const barH = (H - pad * 2) / labels.length * 0.6;
  const gap = (H - pad * 2) / labels.length;

  let content = `<line x1="${pad}" y1="${pad}" x2="${pad}" y2="${H - pad}" stroke="${COLORS.line}"/>`;
  labels.forEach((label, i) => {
    const y = pad + i * gap + (gap - barH) / 2;
    const w = ((W - pad - 60) * values[i]) / max;
    const display = asPercent ? Math.round(values[i] * 100) + "%" : values[i];
    content += `
      <text x="4" y="${y + barH / 2 + 4}" font-size="11" fill="${COLORS.ink}">${label}</text>
      <rect x="${pad}" y="${y}" width="${w}" height="${barH}" fill="${color}" rx="2"/>
      <text x="${pad + w + 6}" y="${y + barH / 2 + 4}" font-size="11" fill="${COLORS.ink}">${display}</text>`;
  });
  svg.innerHTML = content;
}

function drawPieSVG(svgId, distribution) {
  const svg = document.getElementById(svgId);
  const entries = Object.entries(distribution);
  const total = entries.reduce((a, [, v]) => a + v, 0);
  const cx = 130, cy = 130, r = 100;
  const colors = [COLORS.teal, COLORS.gold, COLORS.fail];

  let angle = -Math.PI / 2;
  let content = "";
  entries.forEach(([label, value], i) => {
    const slice = (value / total) * Math.PI * 2;
    const x1 = cx + r * Math.cos(angle), y1 = cy + r * Math.sin(angle);
    angle += slice;
    const x2 = cx + r * Math.cos(angle), y2 = cy + r * Math.sin(angle);
    const large = slice > Math.PI ? 1 : 0;
    content += `<path d="M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z"
      fill="${colors[i % colors.length]}" stroke="#fff" stroke-width="2"/>`;
  });

  let legend = "";
  entries.forEach(([label, value], i) => {
    legend += `<rect x="0" y="${240 + i * 0}" width="0" height="0"/>`; // placeholder unused
  });

  let labels = "";
  entries.forEach(([label, value], i) => {
    labels += `<circle cx="10" cy="${20 + i * 18}" r="5" fill="${colors[i % colors.length]}"/>
      <text x="22" y="${24 + i * 18}" font-size="12" fill="${COLORS.ink}">${label}: ${value} (${Math.round(value / total * 100)}%)</text>`;
  });

  svg.innerHTML = `<g transform="translate(0,10)">${content}</g><g transform="translate(0,0)">${labels}</g>`;
}
