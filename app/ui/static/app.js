const state = {
  overview: null,
  projects: [],
  findings: [],
  runs: [],
  rules: [],
};

const titles = {
  overview: "Overview",
  projects: "Projects",
  findings: "Issues",
  runs: "Review Runs",
  rules: "Rules",
  setup: "Setup",
};

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindRulesForm();
  bindFilters();
  document.getElementById("refresh-button").addEventListener("click", loadAll);
  document.getElementById("webhook-url").textContent = `${location.origin}/api/github/webhook`;
  document.getElementById("health-url").textContent = `${location.origin}/api/healthz`;
  loadAll();
});

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      const view = button.dataset.view;
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(view).classList.add("active");
      document.getElementById("page-title").textContent = titles[view];
    });
  });
}

function bindRulesForm() {
  document.getElementById("rules-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = document.getElementById("rules-message");
    try {
      const repository = document.getElementById("rules-repository").value.trim();
      const rules = JSON.parse(document.getElementById("rules-json").value);
      await request("/api/dashboard/rules", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_full_name: repository, rules }),
      });
      message.textContent = "Rules saved.";
      await loadRules();
    } catch (error) {
      message.textContent = error.message;
    }
  });
}

function bindFilters() {
  document.getElementById("severity-filter").addEventListener("change", renderFindings);
  document.getElementById("finding-search").addEventListener("input", renderFindings);
}

async function loadAll() {
  await Promise.all([loadOverview(), loadProjects(), loadFindings(), loadRuns(), loadRules()]);
  await checkApiStatus();
}

async function loadOverview() {
  state.overview = await request("/api/dashboard/overview");
  renderOverview();
}

async function loadProjects() {
  state.projects = await request("/api/dashboard/projects");
  renderProjects();
}

async function loadFindings() {
  state.findings = await request("/api/dashboard/findings");
  renderFindings();
}

async function loadRuns() {
  state.runs = await request("/api/dashboard/runs");
  renderRuns();
}

async function loadRules() {
  state.rules = await request("/api/dashboard/rules");
  renderRules();
}

async function checkApiStatus() {
  const dot = document.getElementById("api-status");
  try {
    await request("/api/healthz");
    dot.classList.add("ok");
  } catch {
    dot.classList.remove("ok");
  }
}

function renderOverview() {
  const overview = state.overview;
  const gate = overview.quality_gate;
  document.getElementById("quality-gate").innerHTML = `<span class="badge ${gate}">${gate}</span>`;
  document.getElementById("total-projects").textContent = overview.totals.projects;
  document.getElementById("total-runs").textContent = overview.totals.review_runs;
  document.getElementById("total-findings").textContent = overview.totals.findings;
  renderBars("severity-bars", overview.severity, severityColor);
  renderBars("status-bars", overview.status, () => "#0f6b62");
  renderCategories(overview.categories);
}

function renderBars(containerId, values, colorFn) {
  const container = document.getElementById(containerId);
  const entries = Object.entries(values || {});
  if (!entries.length) {
    container.innerHTML = `<div class="empty">No data yet</div>`;
    return;
  }
  const max = Math.max(...entries.map(([, count]) => count), 1);
  container.innerHTML = entries
    .map(([name, count]) => {
      const width = Math.max((count / max) * 100, 4);
      return `<div class="bar-row">
        <span>${escapeHtml(name)}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${width}%;background:${colorFn(name)}"></div></div>
        <strong>${count}</strong>
      </div>`;
    })
    .join("");
}

function renderCategories(categories) {
  const container = document.getElementById("category-list");
  if (!categories.length) {
    container.innerHTML = `<div class="empty">No categories yet</div>`;
    return;
  }
  container.innerHTML = categories
    .map(
      (item) => `<div class="category-item">
        <strong>${escapeHtml(item.name)}</strong>
        <span class="muted">${item.count} findings</span>
      </div>`,
    )
    .join("");
}

function renderProjects() {
  const body = document.getElementById("projects-table");
  if (!state.projects.length) {
    body.innerHTML = `<tr><td colspan="6" class="empty">No reviewed projects yet</td></tr>`;
    return;
  }
  body.innerHTML = state.projects
    .map((project) => {
      const findings = Object.entries(project.findings || {})
        .map(([severity, count]) => `${severity}: ${count}`)
        .join(", ");
      return `<tr>
        <td>${escapeHtml(project.repository_full_name)}</td>
        <td>${project.review_runs}</td>
        <td>${escapeHtml(project.latest_status || "-")}</td>
        <td>${escapeHtml(project.latest_decision || "-")}</td>
        <td>${escapeHtml(findings || "0")}</td>
        <td>${formatDate(project.last_review_at)}</td>
      </tr>`;
    })
    .join("");
}

function renderFindings() {
  const severity = document.getElementById("severity-filter").value;
  const query = document.getElementById("finding-search").value.toLowerCase();
  const container = document.getElementById("findings-list");
  const findings = state.findings.filter((finding) => {
    const matchesSeverity = !severity || finding.severity === severity;
    const haystack = `${finding.title} ${finding.file_path} ${finding.repository_full_name}`.toLowerCase();
    return matchesSeverity && haystack.includes(query);
  });
  if (!findings.length) {
    container.innerHTML = `<div class="empty">No issues match the current filters</div>`;
    return;
  }
  container.innerHTML = findings
    .map(
      (finding) => `<article class="finding-item">
        <div class="finding-top">
          <div>
            <strong>${escapeHtml(finding.title)}</strong>
            <div class="muted">${escapeHtml(finding.repository_full_name)} #${finding.pull_request_number}</div>
          </div>
          <span class="badge ${finding.severity}">${escapeHtml(finding.severity)}</span>
        </div>
        <div>${escapeHtml(finding.description)}</div>
        <div class="muted">${escapeHtml(finding.file_path)}:${finding.line} · ${escapeHtml(finding.category)} · ${escapeHtml(finding.source)} · confidence ${Math.round(finding.confidence * 100)}%</div>
      </article>`,
    )
    .join("");
}

function renderRuns() {
  const body = document.getElementById("runs-table");
  if (!state.runs.length) {
    body.innerHTML = `<tr><td colspan="6" class="empty">No review runs yet</td></tr>`;
    return;
  }
  body.innerHTML = state.runs
    .map(
      (run) => `<tr>
        <td>${run.id}</td>
        <td>${escapeHtml(run.repository_full_name)}</td>
        <td>#${run.pull_request_number}</td>
        <td>${escapeHtml(run.status || "-")}</td>
        <td>${escapeHtml(run.decision || "-")}</td>
        <td>${formatDate(run.created_at)}</td>
      </tr>`,
    )
    .join("");
}

function renderRules() {
  const container = document.getElementById("rules-list");
  if (!state.rules.length) {
    container.innerHTML = `<div class="empty">No repository-specific rules saved yet</div>`;
    return;
  }
  container.innerHTML = state.rules
    .map(
      (rule) => `<article class="rule-item">
        <strong>${escapeHtml(rule.repository_full_name)}</strong>
        <pre>${escapeHtml(JSON.stringify(rule.rules, null, 2))}</pre>
      </article>`,
    )
    .join("");
}

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

function severityColor(name) {
  return {
    critical: "#b42318",
    high: "#d55a00",
    medium: "#b88200",
    low: "#2473b9",
  }[name] || "#0f6b62";
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
