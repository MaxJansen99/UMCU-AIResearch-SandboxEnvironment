const form = document.getElementById("query-form");
const modality = document.getElementById("modality");
const seriesDescription = document.getElementById("series-description");
const summary = document.getElementById("summary");
const results = document.getElementById("results");

function buildFilters() {
  const filters = [];
  if (modality.value) {
    filters.push(["Modality", "==", modality.value]);
  }
  if (seriesDescription.value.trim()) {
    filters.push(["SeriesDescription", "contains", seriesDescription.value.trim()]);
  }
  return filters;
}

function render(payload) {
  summary.innerHTML = `
    <article><span>Series</span><strong>${payload.match_count ?? 0}</strong></article>
    <article><span>Instances in Orthanc</span><strong>${payload.total_instances_in_pacs ?? "-"}</strong></article>
  `;

  const series = payload.matched_series || [];
  if (!series.length) {
    results.innerHTML = `<p class="muted">Geen resultaten.</p>`;
    return;
  }

  results.innerHTML = series.map((item) => `
    <article class="result-card">
      <strong>${item.series_description || "Serie zonder beschrijving"}</strong>
      <div>${item.modality || "-"} · ${item.instances ?? 0} instances</div>
      <small>${item.study_description || ""}</small>
    </article>
  `).join("");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  results.textContent = "Zoeken...";

  const response = await fetch("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filters: buildFilters(),
      stats_tags: ["Modality", "StudyDescription", "SeriesDescription"],
    }),
  });

  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    results.textContent = payload.error || "Query mislukt.";
    return;
  }

  render(payload);
});
