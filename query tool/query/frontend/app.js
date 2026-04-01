const REGION_RULES = [
  { label: "Brain", keywords: ["brain", "head", "neuro", "cranium"] },
  { label: "Spine", keywords: ["spine", "cervical", "thoracic", "lumbar"] },
  { label: "Chest", keywords: ["chest", "thorax", "lung"] },
  { label: "Abdomen", keywords: ["abdomen", "abdominal", "liver"] },
  { label: "Pelvis", keywords: ["pelvis", "pelvic", "hip"] },
  { label: "Breast", keywords: ["breast", "mamma"] },
  { label: "Knee", keywords: ["knee"] },
  { label: "Shoulder", keywords: ["shoulder"] },
  { label: "Whole body", keywords: ["whole body", "wholebody"] },
];

const state = {
  series: [],
  config: {
    operators: [],
    filter_tags: [],
  },
};

const el = {
  kpiStudies: document.getElementById("kpi-studies"),
  kpiSeries: document.getElementById("kpi-series"),
  kpiImages: document.getElementById("kpi-images"),
  basicModality: document.getElementById("basic-modality"),
  basicRegion: document.getElementById("basic-region"),
  dateFrom: document.getElementById("date-from"),
  dateTo: document.getElementById("date-to"),
  addFilter: document.getElementById("add-filter"),
  filterList: document.getElementById("filter-list"),
  filterTemplate: document.getElementById("filter-template"),
  queryForm: document.getElementById("query-form"),
  recursive: document.getElementById("recursive"),
  matchesBody: document.getElementById("matches-body"),
};

function makeOption(value, label = value) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  return option;
}

function selectedValue(select) {
  return select.value;
}

function normalizeValue(operator, rawValue) {
  if (operator === "is None" || operator === "not None") {
    return null;
  }

  const trimmed = rawValue.trim();
  if (!trimmed) {
    return "";
  }

  const numeric = Number(trimmed);
  if (!Number.isNaN(numeric) && trimmed !== "") {
    return numeric;
  }

  if (trimmed.toLowerCase() === "true") {
    return true;
  }
  if (trimmed.toLowerCase() === "false") {
    return false;
  }

  return trimmed;
}

function formatDate(value) {
  if (!value || value.length !== 8) {
    return value || "-";
  }
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
}

function inputDateToDicom(value) {
  return value ? value.replaceAll("-", "") : "";
}

function inferRegion(series) {
  const explicit = (series.body_part_examined || "").trim();
  if (explicit) {
    return explicit;
  }

  const searchableText = [
    series.series_description,
    series.modality,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  const match = REGION_RULES.find((rule) =>
    rule.keywords.some((keyword) => searchableText.includes(keyword))
  );

  return match ? match.label : "Unknown";
}

function addFilterRow(initial = {}) {
  const fragment = el.filterTemplate.content.cloneNode(true);
  const row = fragment.querySelector(".filter-row");
  const tagSelect = fragment.querySelector(".filter-tag");
  const operatorSelect = fragment.querySelector(".filter-operator");
  const valueInput = fragment.querySelector(".filter-value");
  const removeButton = fragment.querySelector(".remove-filter");

  state.config.filter_tags.forEach((tag) => tagSelect.appendChild(makeOption(tag)));
  state.config.operators.forEach((operator) => operatorSelect.appendChild(makeOption(operator)));

  tagSelect.value = initial.tag || state.config.filter_tags[0] || "";
  operatorSelect.value = initial.operator || "contains";
  valueInput.value = initial.value || "";

  removeButton.addEventListener("click", () => {
    row.remove();
    if (!el.filterList.children.length) {
      addFilterRow();
    }
  });

  el.filterList.appendChild(fragment);
}

function collectAdvancedFilters() {
  return Array.from(el.filterList.querySelectorAll(".filter-row")).flatMap((row) => {
    const tag = row.querySelector(".filter-tag").value;
    const operator = row.querySelector(".filter-operator").value;
    const value = normalizeValue(operator, row.querySelector(".filter-value").value);

    if (!tag) {
      return [];
    }
    if (value === "" && operator !== "==" && operator !== "!=") {
      return [];
    }

    return [[tag, operator, value]];
  });
}

function collectBasicFilters() {
  const filters = [];
  const selectedModality = selectedValue(el.basicModality);
  const selectedRegion = selectedValue(el.basicRegion);
  const fromDate = inputDateToDicom(el.dateFrom.value);
  const toDate = inputDateToDicom(el.dateTo.value);

  if (selectedModality) {
    filters.push(["Modality", "==", selectedModality]);
  }
  if (selectedRegion) {
    filters.push(["AnatomicalRegion", "==", selectedRegion]);
  }
  if (fromDate) {
    filters.push(["StudyDate", ">=", fromDate]);
  }
  if (toDate) {
    filters.push(["StudyDate", "<=", toDate]);
  }

  return filters;
}

function renderSummary(result) {
  el.kpiStudies.textContent = result.study_count;
  el.kpiSeries.textContent = result.series_count;
  el.kpiImages.textContent = result.image_count;
}

function renderMatches(studies) {
  if (!studies.length) {
    el.matchesBody.innerHTML = `<p class="muted">Geen matches.</p>`;
    return;
  }

  el.matchesBody.innerHTML = studies
    .slice(0, 20)
    .map((study) => `
      <article class="study-card">
        <div class="meta">${formatDate(study.study_date)}</div>
        <strong>${study.study_description || "Study zonder beschrijving"}</strong>
        <div class="chip-row">${(study.modalities || []).map((modality) => `<span class="chip">${modality}</span>`).join("")}</div>
        <div class="meta">${study.series_count} series | ${study.instance_count} images</div>
        <details class="technical-details">
          <summary>Toon details</summary>
          <div class="meta uid-line">UID: <code>${study.study_instance_uid}</code></div>
          <div class="meta">${(study.sample_paths || []).join("<br>")}</div>
        </details>
      </article>
    `)
    .join("");
}

async function runQuery(event) {
  event.preventDefault();

  const response = await fetch("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filters: [...collectBasicFilters(), ...collectAdvancedFilters()],
      recursive: el.recursive.checked,
      stats_tags: [],
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    el.kpiStudies.textContent = "-";
    el.kpiSeries.textContent = "-";
    el.kpiImages.textContent = "-";
    el.matchesBody.innerHTML = `<p class="muted">${payload.detail || "Query mislukt."}</p>`;
    return;
  }

  renderSummary(payload);
  renderMatches(payload.matched_studies || []);
}

function populateBasicFilters() {
  const preferredModalities = ["", "CT", "MR", "US", "PT", "XR"];
  const regions = [...new Set(state.series.map((series) => inferRegion(series) || "Unknown"))].sort();

  el.basicModality.innerHTML = "";
  preferredModalities.forEach((modality) =>
    el.basicModality.appendChild(makeOption(modality, modality || "Alle modaliteiten"))
  );

  el.basicRegion.innerHTML = "";
  el.basicRegion.appendChild(makeOption("", "Alle regio's"));
  regions.forEach((region) => el.basicRegion.appendChild(makeOption(region, region === "Unknown" ? "Onbekend" : region)));
}

async function loadConfig() {
  const response = await fetch("/ui/config");
  state.config = await response.json();
  addFilterRow({ tag: "SeriesDescription", operator: "contains", value: "" });
}

async function loadDatasetOverview() {
  const response = await fetch("/dicom/series");
  state.series = await response.json();
  populateBasicFilters();
}

function bindEvents() {
  el.addFilter.addEventListener("click", () => addFilterRow());
  el.queryForm.addEventListener("submit", runQuery);
}

async function bootstrap() {
  bindEvents();
  await loadConfig();
  await loadDatasetOverview();
}

bootstrap();
