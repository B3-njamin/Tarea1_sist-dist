const API = "http://localhost:8000";
let historyData = [];
let chartInstance = null;

// ============================================================
// CONFIGURACIÓN
// ============================================================
async function applyConfig() {
  const policy   = document.getElementById("cfg-policy").value;
  const memory   = parseInt(document.getElementById("cfg-memory").value);
  const ttl      = parseInt(document.getElementById("cfg-ttl").value);
  const msg      = document.getElementById("cfg-msg");
  try {
    const res = await fetch(`${API}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy, memory_mb: memory, ttl }),
    });
    const data = await res.json();
    msg.className = "mt-2 text-center fw-semibold text-success";
    msg.textContent = "✅ Configuración aplicada correctamente";
    loadConfig();
  } catch (e) {
    msg.className = "mt-2 text-center fw-semibold text-danger";
    msg.textContent = "❌ Error al aplicar configuración";
  }
}

async function loadConfig() {
  try {
    const res  = await fetch(`${API}/api/config`);
    const data = await res.json();
    const policyNames = {
      "allkeys-lfu": "LFU", "allkeys-lru": "LRU"
    };
    document.getElementById("current-config-display").innerHTML = `
      <ul class="list-unstyled mb-0">
        <li>🔁 <strong>Política:</strong> ${policyNames[data.policy] || data.policy}</li>
        <li>💾 <strong>Memoria:</strong> ${data.memory_mb} MB</li>
        <li>⏱️ <strong>TTL:</strong> ${data.ttl === 0 ? "Sin caché (hit rate 0%)" : data.ttl + " segundos"}</li>
      </ul>`;
    document.getElementById("cfg-policy").value = data.policy;
    document.getElementById("cfg-memory").value = data.memory_mb;
    document.getElementById("cfg-ttl").value    = data.ttl;
  } catch (e) { /* servidor no disponible aún */ }
}

// ============================================================
// MÉTRICAS EN VIVO
// ============================================================
async function updateLive() {
  try {
    const res  = await fetch(`${API}/api/stats`);
    const data = await res.json();
    document.getElementById("live-total").textContent   = data.total;
    document.getElementById("live-hits").textContent    = data.hits;
    document.getElementById("live-misses").textContent  = data.misses;
    document.getElementById("live-hitrate").textContent = data.hit_rate + "%";
    document.getElementById("live-p50").textContent     = data.latency_p50 + "ms";
    document.getElementById("live-p95").textContent     = data.latency_p95 + "ms";
  } catch (e) { /* servidor no disponible aún */ }
}

// ============================================================
// HISTORIAL
// ============================================================
async function loadHistory() {
  try {
    const res  = await fetch(`${API}/api/history`);
    historyData = await res.json();
    const tbody = document.getElementById("history-body");
    if (historyData.length === 0) {
      tbody.innerHTML = `<tr><td colspan="13" class="text-center text-muted">Sin experimentos aún</td></tr>`;
      return;
    }
    const policyNames = {
      "allkeys-lfu": "LFU", "allkeys-lru": "LRU", "allkeys-random": "FIFO"
    };
    tbody.innerHTML = historyData.map(e => `
      <tr>
        <td>${e.id}</td>
        <td>${e.timestamp.split("T")[1].split(".")[0]}</td>
        <td><span class="badge bg-${e.distribution === "zipf" ? "primary" : "secondary"}">${e.distribution}</span></td>
        <td>${policyNames[e.policy] || e.policy}</td>
        <td>${e.memory_mb}</td>
        <td>${e.ttl_seconds === 0 ? "∞" : e.ttl_seconds}</td>
        <td>${e.n_queries}</td>
        <td><strong>${(e.hit_rate * 100).toFixed(1)}%</strong></td>
        <td>${e.throughput}</td>
        <td>${e.latency_p50}</td>
        <td>${e.latency_p95}</td>
        <td>${e.eviction_rate}</td>
        <td>${e.cache_efficiency}</td>
      </tr>`).join("");
    populateTTLSelector();
  } catch (e) { /* servidor no disponible */ }
}

async function clearHistory() {
  if (!confirm("¿Borrar todo el historial?")) return;
  await fetch(`${API}/api/history`, { method: "DELETE" });
  loadHistory();
}

// ============================================================
// GRÁFICOS
// ============================================================
function populateTTLSelector() {
  const ttls = [...new Set(historyData.map(e => e.ttl_seconds))].sort((a, b) => a - b);
  const sel  = document.getElementById("fix-ttl");
  const prev = sel.value;
  sel.innerHTML = `<option value="all">Todos</option>` + ttls.map(t => `<option value="${t}">${t === 0 ? "Sin TTL" : t + "s"}</option>`).join("");
  sel.value = prev;
}

function updateFixedSelectors() {
  const x = document.getElementById("graph-x").value;
  document.getElementById("fix-policy-col").style.display = x === "policy" ? "none" : "";
  document.getElementById("fix-memory-col").style.display = x === "memory_mb" ? "none" : "";
  document.getElementById("fix-ttl-col").style.display    = x === "ttl_seconds" ? "none" : "";
}

function renderChart() {
  const xVar   = document.getElementById("graph-x").value;
  const yVar   = document.getElementById("graph-y").value;
  const dist   = document.getElementById("graph-dist").value;
  const fixPol = document.getElementById("fix-policy").value;
  const fixMem = document.getElementById("fix-memory").value;
  const fixTTL = document.getElementById("fix-ttl").value;

  let filtered = historyData;
  if (dist   !== "all") filtered = filtered.filter(e => e.distribution === dist);
  if (xVar !== "policy"     && fixPol !== "all") filtered = filtered.filter(e => e.policy     === fixPol);
  if (xVar !== "memory_mb"  && fixMem !== "all") filtered = filtered.filter(e => e.memory_mb  == fixMem);
  if (xVar !== "ttl_seconds" && fixTTL !== "all") filtered = filtered.filter(e => e.ttl_seconds == fixTTL);

  // Agrupar por X y promediar Y
  const groups = {};
  for (const e of filtered) {
    const key = e[xVar];
    if (!groups[key]) groups[key] = [];
    groups[key].push(e[yVar]);
  }

  const labels = Object.keys(groups).sort((a, b) => {
    if (!isNaN(a) && !isNaN(b)) return Number(a) - Number(b);
    return String(a).localeCompare(String(b));
  });
  const values = labels.map(k => {
    const arr = groups[k];
    return arr.reduce((s, v) => s + v, 0) / arr.length;
  });

  const yLabels = {
    hit_rate: "Hit Rate", throughput: "Throughput (req/s)",
    latency_p50: "Latencia p50 (ms)", latency_p95: "Latencia p95 (ms)",
    eviction_rate: "Eviction Rate (ev/min)", cache_efficiency: "Cache Efficiency"
  };
  const xLabels = { ttl_seconds: "TTL (s)", policy: "Política", memory_mb: "Memoria (MB)" };

  if (chartInstance) chartInstance.destroy();
  const ctx = document.getElementById("mainChart").getContext("2d");
  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: yLabels[yVar] || yVar,
        data: values,
        backgroundColor: "rgba(13,110,253,0.7)",
        borderColor: "rgba(13,110,253,1)",
        borderWidth: 1,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "top" },
        title: {
          display: true,
          text: `${yLabels[yVar]} por ${xLabels[xVar]}${dist !== "all" ? " — Distribución: " + dist : ""}`,
        }
      },
      scales: {
        x: { title: { display: true, text: xLabels[xVar] } },
        y: { title: { display: true, text: yLabels[yVar] }, beginAtZero: true }
      }
    }
  });
}

// ============================================================
// INICIALIZACIÓN
// ============================================================
loadConfig();
loadHistory();
setInterval(updateLive, 1000);
setInterval(loadHistory, 5000);
updateFixedSelectors();
