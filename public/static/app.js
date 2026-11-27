/**
 * ReviewSense - Client Application Logic (Upgraded Executive Theme)
 */

let currentSessionId = "sample";
let currentDashboardData = null;
let currentDetectedCols = null;
let currentUploadedId = null;
let currentAllColumns = [];

// Chart.js instances registry
let charts = {};

// Table state
let allTableRows = [];
let filteredTableRows = [];
let currentPage = 1;
const rowsPerPage = 10;

// Setup Chart.js Global Dark Theme Defaults
function configureChartDefaults() {
  if (typeof Chart === "undefined") return;
  Chart.defaults.color = "#94a3b8";
  Chart.defaults.font.family = "'Plus Jakarta Sans', -apple-system, sans-serif";
  Chart.defaults.font.size = 11;
  Chart.defaults.plugins.tooltip.backgroundColor = "rgba(13, 17, 39, 0.95)";
  Chart.defaults.plugins.tooltip.titleColor = "#ffffff";
  Chart.defaults.plugins.tooltip.bodyColor = "#cbd5e1";
  Chart.defaults.plugins.tooltip.borderColor = "rgba(168, 85, 247, 0.4)";
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.plugins.tooltip.boxPadding = 6;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.color = "#cbd5e1";
}

document.addEventListener("DOMContentLoaded", () => {
  configureChartDefaults();
  initEventListeners();
  initScrollAnimations();
  loadSampleDataset();
});

// --------------------------------------------------------------------------
// Scroll & Fluid Flow Animations
// --------------------------------------------------------------------------

function initScrollAnimations() {
  const progressBar = document.getElementById("scroll-progress");
  const header = document.querySelector(".app-header");

  window.addEventListener("scroll", () => {
    // Scroll progress bar
    const winScroll = document.documentElement.scrollTop || document.body.scrollTop;
    const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = height > 0 ? (winScroll / height) * 100 : 0;
    if (progressBar) progressBar.style.width = `${scrolled}%`;

    // Header blur state
    if (header) {
      if (winScroll > 20) {
        header.classList.add("scrolled");
      } else {
        header.classList.remove("scrolled");
      }
    }
  });

  // IntersectionObserver for scroll-reveal sections
  const revealElements = document.querySelectorAll(".reveal-on-scroll");
  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("revealed");
        // Trigger counter animation if summary cards entered
        if (entry.target.id === "summary-cards") {
          triggerStatCounters();
        }
        obs.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.12,
    rootMargin: "0px 0px -40px 0px"
  });

  revealElements.forEach(el => observer.observe(el));
}

function triggerStatCounters() {
  if (!currentDashboardData || !currentDashboardData.summary_cards) return;
  const cards = currentDashboardData.summary_cards;

  animateNumber("card-total-reviews", 0, cards.total_reviews || 0, 1000, false);
  animateNumber("card-pct-positive", 0, cards.pct_positive || 0, 1000, true);
  animateNumber("card-pct-neutral", 0, cards.pct_neutral || 0, 1000, true);
  animateNumber("card-pct-negative", 0, cards.pct_negative || 0, 1000, true);
  if (cards.avg_rating) {
    animateFloat("card-avg-rating", 0, cards.avg_rating, 1000, " / 5");
  }
}

function animateNumber(elementId, start, end, duration, isPercentage = false) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3); // cubic ease out
    const currentVal = Math.round(start + (end - start) * ease);

    el.textContent = isPercentage ? `${currentVal.toFixed(1)}%` : currentVal.toLocaleString();

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      el.textContent = isPercentage ? `${end}%` : end.toLocaleString();
    }
  }

  requestAnimationFrame(update);
}

function animateFloat(elementId, start, end, duration, suffix = "") {
  const el = document.getElementById(elementId);
  if (!el) return;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const currentVal = (start + (end - start) * ease).toFixed(2);

    el.textContent = `${currentVal}${suffix}`;

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      el.textContent = `${end}${suffix}`;
    }
  }

  requestAnimationFrame(update);
}

// --------------------------------------------------------------------------
// Event Listeners
// --------------------------------------------------------------------------

function initEventListeners() {
  // Use Sample Dataset Button
  const btnSample = document.getElementById("btn-sample-data");
  if (btnSample) {
    btnSample.addEventListener("click", () => {
      loadSampleDataset();
    });
  }

  // Export CSV Button
  const btnExportCsv = document.getElementById("btn-export-csv");
  if (btnExportCsv) {
    btnExportCsv.addEventListener("click", () => {
      if (!currentSessionId) {
        alert("Please analyze a dataset first.");
        return;
      }
      window.location.href = `/api/export_csv?session_id=${encodeURIComponent(currentSessionId)}`;
    });
  }

  // Export Dashboard Snapshot Button
  const btnExportDash = document.getElementById("btn-export-dashboard");
  if (btnExportDash) {
    btnExportDash.addEventListener("click", exportDashboardSnapshot);
  }

  // Toggle Detected Columns Box
  const btnToggleCols = document.getElementById("btn-toggle-columns");
  const colsBox = document.getElementById("columns-config-box");
  if (btnToggleCols && colsBox) {
    btnToggleCols.addEventListener("click", () => {
      colsBox.classList.toggle("open");
    });
  }

  // Re-run Analysis Button
  const btnRerun = document.getElementById("btn-rerun-analysis");
  if (btnRerun) {
    btnRerun.addEventListener("click", runCustomAnalysis);
  }

  // Try a Review Box
  const btnPredictSingle = document.getElementById("btn-predict-single");
  const inputSingle = document.getElementById("single-review-text");
  if (btnPredictSingle && inputSingle) {
    btnPredictSingle.addEventListener("click", predictSingleReview);
    inputSingle.addEventListener("keypress", (e) => {
      if (e.key === "Enter") predictSingleReview();
    });
  }

  // File Upload & Drag-and-Drop
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");

  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
      }
    });
  }

  // Table Search and Filters
  const searchInput = document.getElementById("table-search");
  const filterSent = document.getElementById("filter-sentiment");
  const filterCat = document.getElementById("filter-category");

  if (searchInput) searchInput.addEventListener("input", applyTableFilters);
  if (filterSent) filterSent.addEventListener("change", applyTableFilters);
  if (filterCat) filterCat.addEventListener("change", applyTableFilters);

  // Pagination Controls
  const btnPrev = document.getElementById("btn-page-prev");
  const btnNext = document.getElementById("btn-page-next");
  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        renderTablePage();
      }
    });
  }
  if (btnNext) {
    btnNext.addEventListener("click", () => {
      const maxPage = Math.ceil(filteredTableRows.length / rowsPerPage) || 1;
      if (currentPage < maxPage) {
        currentPage++;
        renderTablePage();
      }
    });
  }
}

// --------------------------------------------------------------------------
// API Calls & Data Loading
// --------------------------------------------------------------------------

async function loadSampleDataset() {
  try {
    updateCleaningStatus("Loading built-in sample dataset (1,000 reviews)...");
    const res = await fetch("/api/sample");
    if (!res.ok) throw new Error("Failed to load sample dataset");
    const data = await res.json();
    
    currentSessionId = data.session_id;
    currentUploadedId = null;
    currentDetectedCols = data.detected_columns;
    currentAllColumns = data.detected_columns.all_columns || [];
    currentDashboardData = data.dashboard;

    updateFileStatus(data.filename, data.cleaning_summary);
    populateDetectedColumnsUI(currentDetectedCols, currentAllColumns);
    renderDashboard(data.dashboard);
    triggerStatCounters();
  } catch (err) {
    console.error("Error loading sample dataset:", err);
    alert("Could not load sample dataset: " + err.message);
  }
}

async function handleFileUpload(file) {
  try {
    updateCleaningStatus(`Uploading ${file.name}...`);
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Upload failed");
    }

    const data = await res.json();
    currentUploadedId = data.upload_id;
    currentSessionId = data.upload_id;
    currentAllColumns = data.columns;
    currentDetectedCols = data.detected_columns;

    // Show Detected Columns Box
    const colsBox = document.getElementById("columns-config-box");
    if (colsBox) colsBox.classList.add("open");

    populateDetectedColumnsUI(currentDetectedCols, currentAllColumns);
    updateCleaningStatus(`Uploaded ${file.name} (${data.total_rows} rows). Running analysis...`);

    await runCustomAnalysis();
  } catch (err) {
    console.error("Upload error:", err);
    alert("Error uploading file: " + err.message);
    updateCleaningStatus("Upload failed.");
  }
}

async function runCustomAnalysis() {
  if (!currentUploadedId && currentSessionId !== "sample") {
    alert("Please upload a file or use the sample dataset.");
    return;
  }

  const textCol = document.getElementById("select-col-text")?.value;
  const labelCol = document.getElementById("select-col-label")?.value || null;
  const ratingCol = document.getElementById("select-col-rating")?.value || null;
  const dateCol = document.getElementById("select-col-date")?.value || null;
  
  const catSelects = document.querySelectorAll(".select-cat-col");
  const catCols = Array.from(catSelects).map(s => s.value).filter(v => v && v !== "__none__");

  const columnMapping = {
    text_column: textCol,
    label_column: labelCol === "__none__" ? null : labelCol,
    rating_column: ratingCol === "__none__" ? null : ratingCol,
    date_column: dateCol === "__none__" ? null : dateCol,
    categorical_columns: catCols,
    numeric_columns: currentDetectedCols?.numeric_columns || []
  };

  try {
    updateCleaningStatus("Running AI sentiment analysis across all unique reviews...");
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        upload_id: currentUploadedId || "sample",
        column_mapping: columnMapping
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Analysis failed");
    }

    const data = await res.json();
    currentSessionId = data.session_id;
    currentDetectedCols = data.detected_columns;
    currentDashboardData = data.dashboard;

    updateFileStatus(data.filename, data.cleaning_summary);
    renderDashboard(data.dashboard);
    triggerStatCounters();
    
    document.getElementById("summary-cards")?.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    console.error("Analysis error:", err);
    alert("Analysis failed: " + err.message);
  }
}

async function predictSingleReview() {
  const input = document.getElementById("single-review-text");
  const text = input ? input.value.trim() : "";
  if (!text) return;

  const btn = document.getElementById("btn-predict-single");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.innerHTML = `<span style="display:inline-block; animation:spin 1s linear infinite;">⏳</span> Predicting...`;
    btn.disabled = true;
  }

  try {
    const res = await fetch("/api/predict_single", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error("Inference error");
    const data = await res.json();

    const badge = document.getElementById("single-sentiment-badge");
    const confText = document.getElementById("single-confidence-text");
    const meterPos = document.getElementById("meter-pos");
    const meterNeu = document.getElementById("meter-neu");
    const meterNeg = document.getElementById("meter-neg");

    const scorePos = document.getElementById("score-pos");
    const scoreNeu = document.getElementById("score-neu");
    const scoreNeg = document.getElementById("score-neg");

    const sent = data.sentiment.toLowerCase();
    const confPct = Math.round(data.confidence * 1000) / 10;
    const posPct = Math.round((data.scores.positive || 0) * 1000) / 10;
    const neuPct = Math.round((data.scores.neutral || 0) * 1000) / 10;
    const negPct = Math.round((data.scores.negative || 0) * 1000) / 10;

    badge.className = `sentiment-badge badge-${sent}`;
    badge.textContent = sent.toUpperCase();
    confText.textContent = `Confidence: ${confPct}%`;

    meterPos.style.width = `${posPct}%`;
    meterNeu.style.width = `${neuPct}%`;
    meterNeg.style.width = `${negPct}%`;

    scorePos.textContent = `${posPct}%`;
    scoreNeu.textContent = `${neuPct}%`;
    scoreNeg.textContent = `${negPct}%`;

    // Rotate Dial Gauge Needle (Matching Logo aesthetic)
    const needle = document.getElementById("gauge-needle-group");
    if (needle) {
      if (sent === "positive") {
        needle.style.transform = "rotate(52deg)";
      } else if (sent === "negative") {
        needle.style.transform = "rotate(-52deg)";
      } else {
        needle.style.transform = "rotate(0deg)";
      }
    }
  } catch (err) {
    console.error("Single prediction error:", err);
  } finally {
    if (btn) {
      btn.innerHTML = origHtml;
      btn.disabled = false;
    }
  }
}

// --------------------------------------------------------------------------
// UI Rendering & Updates
// --------------------------------------------------------------------------

function updateFileStatus(filename, cleaningSummary) {
  const badge = document.getElementById("active-file-badge");
  const text = document.getElementById("cleaning-summary-text");
  if (badge) badge.textContent = `Loaded: ${filename}`;
  
  if (text && cleaningSummary) {
    const total = cleaningSummary.total_rows || 0;
    const removed = cleaningSummary.rows_removed || 0;
    const missing = Object.values(cleaningSummary.missing_values_per_col || {}).reduce((a, b) => a + b, 0);
    text.innerHTML = `Cleaning: <strong>${total.toLocaleString()}</strong> total rows &bull; <strong>${removed}</strong> removed &bull; <strong>${missing}</strong> missing values`;
  }
}

function updateCleaningStatus(msg) {
  const text = document.getElementById("cleaning-summary-text");
  if (text) text.textContent = msg;
}

function populateDetectedColumnsUI(detected, allCols) {
  const container = document.getElementById("columns-mapping-fields");
  if (!container) return;
  container.innerHTML = "";

  const createSelectGroup = (id, labelText, selectedValue, allowNone = false) => {
    const wrap = document.createElement("div");
    wrap.className = "col-field-group";

    const label = document.createElement("label");
    label.textContent = labelText;
    wrap.appendChild(label);

    const select = document.createElement("select");
    select.id = id;

    if (allowNone) {
      const optNone = document.createElement("option");
      optNone.value = "__none__";
      optNone.textContent = "-- None / Not in dataset --";
      select.appendChild(optNone);
    }

    allCols.forEach(col => {
      const opt = document.createElement("option");
      opt.value = col;
      opt.textContent = col;
      if (col === selectedValue) opt.selected = true;
      select.appendChild(opt);
    });

    if (allowNone && !selectedValue) {
      select.value = "__none__";
    }

    wrap.appendChild(select);
    return wrap;
  };

  container.appendChild(createSelectGroup("select-col-text", "Review Text Column", detected.text_column, false));
  container.appendChild(createSelectGroup("select-col-label", "Actual Sentiment Label", detected.label_column, true));
  container.appendChild(createSelectGroup("select-col-rating", "Star Rating Column", detected.rating_column, true));
  container.appendChild(createSelectGroup("select-col-date", "Date / Timestamp Column", detected.date_column, true));

  const catCols = detected.categorical_columns || [];
  catCols.slice(0, 3).forEach((c, idx) => {
    const group = createSelectGroup(`select-cat-${idx}`, `Categorical Column #${idx+1}`, c, true);
    group.querySelector("select").classList.add("select-cat-col");
    container.appendChild(group);
  });
}

// --------------------------------------------------------------------------
// Dashboard Rendering
// --------------------------------------------------------------------------

function renderDashboard(data) {
  if (!data) return;

  // 1. Top Summary Cards
  const cards = data.summary_cards;
  if (cards) {
    document.getElementById("card-total-reviews").textContent = (cards.total_reviews || 0).toLocaleString();
    document.getElementById("card-pct-positive").textContent = `${cards.pct_positive}%`;
    document.getElementById("card-count-positive").textContent = `${(cards.positive_count || 0).toLocaleString()} reviews`;

    document.getElementById("card-pct-neutral").textContent = `${cards.pct_neutral}%`;
    document.getElementById("card-count-neutral").textContent = `${(cards.neutral_count || 0).toLocaleString()} reviews`;

    document.getElementById("card-pct-negative").textContent = `${cards.pct_negative}%`;
    document.getElementById("card-count-negative").textContent = `${(cards.negative_count || 0).toLocaleString()} reviews`;

    const ratingCard = document.getElementById("card-rating-wrapper");
    if (cards.avg_rating !== null && cards.avg_rating !== undefined) {
      ratingCard.style.display = "flex";
      document.getElementById("card-avg-rating").textContent = `${cards.avg_rating} / 5`;
    } else {
      ratingCard.style.display = "none";
    }
  }

  // 2. Charts
  renderSentimentDistChart(data.sentiment_distribution);
  renderCategoricalCharts(data.categorical_charts);
  renderRatingChart(data.rating_chart);
  renderTrendChart(data.trend_chart);
  renderTopCategoriesChart(data.top_categories_chart);
  renderHeatmap(data.heatmap_chart);
  renderConfusionMatrix(data.confusion_chart);
  renderKeywords(data.keywords_chart);
  renderNumericCharts(data.numeric_charts);

  // 3. AI Insights
  renderAiInsights(data.ai_insights);

  // 4. Review Explorer Table
  populateReviewTable(data.table_rows, data.display_columns);
}

// --------------------------------------------------------------------------
// Individual Chart Renderers with Glowing Dark Theme Palettes
// --------------------------------------------------------------------------

function destroyChart(key) {
  if (charts[key]) {
    charts[key].destroy();
    delete charts[key];
  }
}

function renderSentimentDistChart(data) {
  const box = document.getElementById("chart-box-sentiment");
  if (!data) { box.style.display = "none"; return; }
  box.style.display = "flex";

  destroyChart("sentiment-dist");
  const ctx = document.getElementById("chart-sentiment-dist").getContext("2d");
  charts["sentiment-dist"] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.labels,
      datasets: [{
        data: data.counts,
        backgroundColor: ["#10b981", "#6366f1", "#f43f5e"],
        borderWidth: 2,
        borderColor: "rgba(13, 17, 39, 0.9)",
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw.toLocaleString()} (${data.percentages[ctx.dataIndex]}%)`
          }
        }
      },
      cutout: "64%"
    }
  });

  document.getElementById("takeaway-sentiment-dist").textContent = data.takeaway || "";
}

function renderCategoricalCharts(catCharts) {
  const box0 = document.getElementById("chart-box-categorical-0");
  const box1 = document.getElementById("chart-box-categorical-1");

  if (!catCharts || catCharts.length === 0) {
    box0.style.display = "none";
    box1.style.display = "none";
    return;
  }

  // 1st Categorical Chart
  if (catCharts[0]) {
    box0.style.display = "flex";
    document.getElementById("title-cat-0").textContent = `2. Sentiment by ${catCharts[0].column}`;
    destroyChart("cat-0");
    const ctx0 = document.getElementById("chart-cat-0").getContext("2d");
    charts["cat-0"] = new Chart(ctx0, {
      type: "bar",
      data: {
        labels: catCharts[0].categories,
        datasets: [
          { label: "Positive %", data: catCharts[0].series.positive, backgroundColor: "#10b981", borderRadius: 4 },
          { label: "Neutral %", data: catCharts[0].series.neutral, backgroundColor: "#6366f1", borderRadius: 4 },
          { label: "Negative %", data: catCharts[0].series.negative, backgroundColor: "#f43f5e", borderRadius: 4 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true, grid: { color: "rgba(255, 255, 255, 0.05)" } },
          y: { stacked: true, max: 100, ticks: { callback: v => v + "%" }, grid: { color: "rgba(255, 255, 255, 0.05)" } }
        },
        plugins: { legend: { position: "top" } }
      }
    });
    document.getElementById("takeaway-cat-0").textContent = catCharts[0].takeaway || "";
  } else {
    box0.style.display = "none";
  }

  // 2nd Categorical Chart
  if (catCharts[1]) {
    box1.style.display = "flex";
    document.getElementById("title-cat-1").textContent = `3. Sentiment by ${catCharts[1].column}`;
    destroyChart("cat-1");
    const ctx1 = document.getElementById("chart-cat-1").getContext("2d");
    charts["cat-1"] = new Chart(ctx1, {
      type: "bar",
      data: {
        labels: catCharts[1].categories,
        datasets: [
          { label: "Positive %", data: catCharts[1].series.positive, backgroundColor: "#10b981", borderRadius: 4 },
          { label: "Neutral %", data: catCharts[1].series.neutral, backgroundColor: "#6366f1", borderRadius: 4 },
          { label: "Negative %", data: catCharts[1].series.negative, backgroundColor: "#f43f5e", borderRadius: 4 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true, grid: { color: "rgba(255, 255, 255, 0.05)" } },
          y: { stacked: true, max: 100, ticks: { callback: v => v + "%" }, grid: { color: "rgba(255, 255, 255, 0.05)" } }
        },
        plugins: { legend: { position: "top" } }
      }
    });
    document.getElementById("takeaway-cat-1").textContent = catCharts[1].takeaway || "";
  } else {
    box1.style.display = "none";
  }
}

function renderRatingChart(data) {
  const box = document.getElementById("chart-box-rating");
  if (!data) { box.style.display = "none"; return; }
  box.style.display = "flex";

  destroyChart("rating");
  const ctx = document.getElementById("chart-rating").getContext("2d");
  charts["rating"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{
        label: "Reviews",
        data: data.counts,
        backgroundColor: "#fbbf24",
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, grid: { color: "rgba(255, 255, 255, 0.05)" } }
      }
    }
  });

  document.getElementById("takeaway-rating").textContent = data.takeaway || "";
}

function renderTrendChart(data) {
  const box = document.getElementById("chart-box-trend");
  if (!data) { box.style.display = "none"; return; }
  box.style.display = "flex";

  destroyChart("trend");
  const ctx = document.getElementById("chart-trend").getContext("2d");
  charts["trend"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.periods,
      datasets: [
        { label: "Positive %", data: data.positive, borderColor: "#10b981", backgroundColor: "rgba(16, 185, 129, 0.12)", fill: true, tension: 0.35, pointBackgroundColor: "#10b981", pointRadius: 4 },
        { label: "Neutral %", data: data.neutral, borderColor: "#818cf8", tension: 0.35, pointBackgroundColor: "#818cf8", pointRadius: 3 },
        { label: "Negative %", data: data.negative, borderColor: "#f43f5e", backgroundColor: "rgba(244, 63, 94, 0.12)", fill: true, tension: 0.35, pointBackgroundColor: "#f43f5e", pointRadius: 4 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: "rgba(255, 255, 255, 0.05)" } },
        y: { min: 0, max: 100, ticks: { callback: v => v + "%" }, grid: { color: "rgba(255, 255, 255, 0.05)" } }
      },
      plugins: { legend: { position: "top" } }
    }
  });

  document.getElementById("takeaway-trend").textContent = data.takeaway || "";
}

function renderTopCategoriesChart(data) {
  const box = document.getElementById("chart-box-top-categories");
  if (!data) { box.style.display = "none"; return; }
  box.style.display = "flex";

  destroyChart("top-categories");
  const ctx = document.getElementById("chart-top-categories").getContext("2d");
  charts["top-categories"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.positive_labels,
      datasets: [
        { label: "Positive Volume", data: data.positive_counts, backgroundColor: "#10b981", borderRadius: 5 },
        { label: "Negative Volume", data: data.negative_counts, backgroundColor: "#f43f5e", borderRadius: 5 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      plugins: { legend: { position: "top" } },
      scales: {
        x: { beginAtZero: true, grid: { color: "rgba(255, 255, 255, 0.05)" } },
        y: { grid: { display: false } }
      }
    }
  });

  document.getElementById("takeaway-top-categories").textContent = data.takeaway || "";
}

function renderHeatmap(data) {
  const box = document.getElementById("chart-box-heatmap");
  const container = document.getElementById("heatmap-render-area");
  if (!data || !container) { box.style.display = "none"; return; }
  box.style.display = "flex";

  document.getElementById("title-heatmap").textContent = data.title;
  let html = `<table class="matrix-table"><thead><tr><th>${data.col_y_name} \\ ${data.col_x_name}</th>`;
  data.x_labels.forEach(x => { html += `<th>${x}</th>`; });
  html += `</tr></thead><tbody>`;

  const maxVal = Math.max(...data.matrix.flat(), 1);

  data.y_labels.forEach((y, rowIdx) => {
    html += `<tr><td style="font-weight:600; text-align:left; color:#c4b5fd;">${y}</td>`;
    data.x_labels.forEach((x, colIdx) => {
      const val = data.matrix[rowIdx][colIdx] || 0;
      const intensity = (val / maxVal).toFixed(2);
      const bg = val === 0 ? "rgba(255, 255, 255, 0.02)" : `rgba(244, 63, 94, ${Math.max(0.18, intensity * 0.85)})`;
      const textColor = intensity > 0.4 ? "#ffffff" : "#fca5a5";
      html += `<td style="background-color:${bg}; color:${textColor};" title="${val} negative reviews on ${y} - ${x}">${val}</td>`;
    });
    html += `</tr>`;
  });

  html += `</tbody></table>`;
  container.innerHTML = html;
  document.getElementById("takeaway-heatmap").textContent = data.takeaway || "";
}

function renderConfusionMatrix(data) {
  const box = document.getElementById("chart-box-confusion");
  const container = document.getElementById("confusion-render-area");
  if (!data || !container) { box.style.display = "none"; return; }
  box.style.display = "flex";

  document.getElementById("confusion-acc-badge").textContent = `${data.accuracy}% Accuracy`;

  let html = `<table class="matrix-table"><thead><tr><th>Actual \\ Predicted</th>`;
  data.labels.forEach(l => { html += `<th>${l}</th>`; });
  html += `</tr></thead><tbody>`;

  data.labels.forEach((act, rowIdx) => {
    html += `<tr><td style="font-weight:600; text-align:left; color:#c4b5fd;">${act}</td>`;
    data.labels.forEach((pred, colIdx) => {
      const val = data.matrix[rowIdx][colIdx] || 0;
      const isDiag = rowIdx === colIdx;
      const bg = isDiag ? "rgba(16, 185, 129, 0.28)" : (val > 0 ? "rgba(244, 63, 94, 0.22)" : "rgba(255, 255, 255, 0.02)");
      const color = isDiag ? "#34d399" : (val > 0 ? "#fb7185" : "#64748b");
      html += `<td style="background-color:${bg}; color:${color};" title="${act} -> ${pred}: ${val}">${val}</td>`;
    });
    html += `</tr>`;
  });

  html += `</tbody></table>`;
  container.innerHTML = html;
  document.getElementById("takeaway-confusion").textContent = data.takeaway || "";
}

function renderKeywords(data) {
  const box = document.getElementById("chart-box-keywords");
  if (!data) { box.style.display = "none"; return; }
  box.style.display = "flex";

  const praisesList = document.getElementById("praises-tag-list");
  const complaintsList = document.getElementById("complaints-tag-list");
  praisesList.innerHTML = "";
  complaintsList.innerHTML = "";

  (data.praises || []).forEach(p => {
    const el = document.createElement("div");
    el.className = "tag-item";
    el.innerHTML = `<span class="tag-term" style="color:#34d399;">${p.term}</span><span class="tag-count">${p.count}</span>`;
    praisesList.appendChild(el);
  });

  (data.complaints || []).forEach(c => {
    const el = document.createElement("div");
    el.className = "tag-item";
    el.innerHTML = `<span class="tag-term" style="color:#fb7185;">${c.term}</span><span class="tag-count">${c.count}</span>`;
    complaintsList.appendChild(el);
  });

  document.getElementById("takeaway-keywords").textContent = data.takeaway || "";
}

function renderNumericCharts(numericList) {
  const box = document.getElementById("chart-box-numeric");
  if (!numericList || numericList.length === 0) {
    box.style.display = "none";
    return;
  }
  box.style.display = "flex";

  const item = numericList[0];
  document.getElementById("title-numeric").textContent = `10. Average ${item.column} vs Sentiment`;

  destroyChart("numeric");
  const ctx = document.getElementById("chart-numeric").getContext("2d");
  charts["numeric"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: item.labels,
      datasets: [{
        label: `Mean ${item.column}`,
        data: item.averages,
        backgroundColor: ["#10b981", "#6366f1", "#f43f5e"],
        borderRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, grid: { color: "rgba(255, 255, 255, 0.05)" } }
      }
    }
  });

  document.getElementById("takeaway-numeric").textContent = item.takeaway || "";
}

// --------------------------------------------------------------------------
// AI Insights Section
// --------------------------------------------------------------------------

function renderAiInsights(insights) {
  if (!insights) return;

  document.getElementById("insight-overall-sentence").textContent = insights.overall_sentence || "";
  document.getElementById("insight-best-performer").textContent = insights.best_performer || "N/A";
  document.getElementById("insight-worst-performer").textContent = insights.worst_performer || "N/A";
  document.getElementById("insight-label-mismatch").textContent = insights.label_mismatch || "N/A";

  document.getElementById("insight-top-praises").textContent = (insights.top_3_praises || []).join(", ") || "None";
  document.getElementById("insight-top-complaints").textContent = (insights.top_3_complaints || []).join(", ") || "None";

  const recList = document.getElementById("insight-recommendations-list");
  recList.innerHTML = "";
  (insights.recommendations || []).forEach(rec => {
    const li = document.createElement("li");
    li.textContent = rec;
    recList.appendChild(li);
  });
}

// --------------------------------------------------------------------------
// Review Explorer Table
// --------------------------------------------------------------------------

function populateReviewTable(rows, displayCols) {
  allTableRows = rows || [];
  filteredTableRows = [...allTableRows];
  currentPage = 1;

  const filterCat = document.getElementById("filter-category");
  if (filterCat) {
    filterCat.innerHTML = `<option value="all">All Segments / Platforms</option>`;
    const candidateCol = displayCols.find(c => ["Window", "Platform", "Category", "_derived_category"].includes(c));
    if (candidateCol) {
      const distinctVals = [...new Set(allTableRows.map(r => r[candidateCol]).filter(Boolean))];
      distinctVals.forEach(val => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.textContent = val;
        filterCat.appendChild(opt);
      });
      filterCat.parentElement.style.display = "block";
    } else {
      filterCat.parentElement.style.display = "none";
    }
  }

  const theadRow = document.getElementById("table-head-row");
  theadRow.innerHTML = `
    <th>#</th>
    <th>Review</th>
    <th>Predicted Sentiment</th>
    <th>Confidence</th>
  `;

  const extraCols = displayCols.filter(c => !c.startsWith("_")).slice(0, 3);
  extraCols.forEach(col => {
    const th = document.createElement("th");
    th.textContent = col;
    theadRow.appendChild(th);
  });

  renderTablePage();
}

function applyTableFilters() {
  const searchTerm = (document.getElementById("table-search")?.value || "").toLowerCase().trim();
  const sentimentVal = document.getElementById("filter-sentiment")?.value || "all";
  const catVal = document.getElementById("filter-category")?.value || "all";

  filteredTableRows = allTableRows.filter(row => {
    if (searchTerm && !row.review.toLowerCase().includes(searchTerm)) {
      return false;
    }
    if (sentimentVal !== "all" && row.predicted_sentiment.toLowerCase() !== sentimentVal) {
      return false;
    }
    if (catVal !== "all") {
      const matchesAnyCol = Object.values(row).some(v => v === catVal);
      if (!matchesAnyCol) return false;
    }
    return true;
  });

  currentPage = 1;
  renderTablePage();
}

function renderTablePage() {
  const tbody = document.getElementById("table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  const total = filteredTableRows.length;
  const startIdx = (currentPage - 1) * rowsPerPage;
  const endIdx = Math.min(startIdx + rowsPerPage, total);
  const pageItems = filteredTableRows.slice(startIdx, endIdx);

  if (pageItems.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4" style="color: #64748b;">No matching reviews found.</td></tr>`;
  } else {
    const extraThs = Array.from(document.querySelectorAll("#table-head-row th")).slice(4);
    const extraColNames = extraThs.map(th => th.textContent);

    pageItems.forEach((row, idx) => {
      const tr = document.createElement("tr");
      const sent = row.predicted_sentiment.toLowerCase();
      const confPct = Math.round(row.confidence * 100);

      let extraTds = "";
      extraColNames.forEach(colName => {
        const val = row[colName] !== undefined && row[colName] !== null ? row[colName] : "—";
        extraTds += `<td>${val}</td>`;
      });

      tr.innerHTML = `
        <td style="color:#64748b; font-family:'JetBrains Mono',monospace;">${startIdx + idx + 1}</td>
        <td class="review-text-cell">${escapeHtml(row.review)}</td>
        <td><span class="sentiment-badge badge-${sent}">${sent}</span></td>
        <td class="confidence-bar-cell">${confPct}%</td>
        ${extraTds}
      `;
      tbody.appendChild(tr);
    });
  }

  const maxPage = Math.ceil(total / rowsPerPage) || 1;
  document.getElementById("pagination-info").textContent = total > 0 
    ? `Showing ${startIdx + 1} to ${endIdx} of ${total.toLocaleString()} entries`
    : "No entries to display";
  document.getElementById("page-indicator").textContent = `Page ${currentPage} of ${maxPage}`;

  document.getElementById("btn-page-prev").disabled = currentPage <= 1;
  document.getElementById("btn-page-next").disabled = currentPage >= maxPage;
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// --------------------------------------------------------------------------
// Export Dashboard as Image / Snapshot
// --------------------------------------------------------------------------

function exportDashboardSnapshot() {
  const element = document.getElementById("printable-dashboard");
  if (!element || typeof html2canvas === "undefined") {
    window.print();
    return;
  }

  const btn = document.getElementById("btn-export-dashboard");
  const origText = btn.innerHTML;
  btn.innerHTML = "Generating Image...";
  btn.disabled = true;

  html2canvas(element, {
    scale: 2,
    useCORS: true,
    backgroundColor: "#080914"
  }).then(canvas => {
    const link = document.createElement("a");
    link.download = `ReviewSense_Dashboard_${new Date().toISOString().slice(0, 10)}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
    btn.innerHTML = origText;
    btn.disabled = false;
  }).catch(err => {
    console.error("Export dashboard error:", err);
    window.print();
    btn.innerHTML = origText;
    btn.disabled = false;
  });
}
