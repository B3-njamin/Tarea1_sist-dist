const CLIENT_API = "http://localhost:8001";
let pollInterval = null;

async function runExperiment() {
  const dist     = document.querySelector('input[name="dist"]:checked').value;
  const nQueries = parseInt(document.getElementById("n-queries").value);
  const btn      = document.getElementById("run-btn");
  const msg      = document.getElementById("run-msg");

  if (isNaN(nQueries) || nQueries < 1) {
    msg.className = "mt-2 text-center fw-semibold text-danger";
    msg.textContent = "❌ Ingresa un número válido de consultas";
    return;
  }

  btn.disabled = true;
  msg.className = "mt-2 text-center fw-semibold text-secondary";
  msg.textContent = "Iniciando experimento...";

  try {
    const res  = await fetch(`${CLIENT_API}/api/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ distribution: dist, n_queries: nQueries }),
    });
    const data = await res.json();

    if (!data.ok) {
      msg.className = "mt-2 text-center fw-semibold text-danger";
      msg.textContent = "❌ " + (data.detail || "Error al iniciar");
      btn.disabled = false;
      return;
    }

    msg.textContent = "";
    document.getElementById("progress-card").style.display = "";
    document.getElementById("prog-done").style.display     = "none";
    document.getElementById("prog-dist").textContent       = `Distribución: ${dist} | ${nQueries} consultas`;
    startPolling(nQueries);

  } catch (e) {
    msg.className = "mt-2 text-center fw-semibold text-danger";
    msg.textContent = "❌ No se pudo conectar al backend del cliente";
    btn.disabled = false;
  }
}

function startPolling(total) {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(async () => {
    try {
      const res  = await fetch(`${CLIENT_API}/api/status`);
      const data = await res.json();

      const pct = total > 0 ? Math.round((data.completed / total) * 100) : 0;
      document.getElementById("prog-completed").textContent = data.completed;
      document.getElementById("prog-total").textContent     = data.total;
      document.getElementById("prog-success").textContent   = data.successful + " exitosas";
      document.getElementById("prog-errors").textContent    = data.errors + " errores";
      const bar = document.getElementById("progress-bar");
      bar.style.width   = pct + "%";
      bar.textContent   = pct + "%";
      bar.setAttribute("aria-valuenow", pct);

      if (!data.running && data.completed >= data.total && data.total > 0) {
        clearInterval(pollInterval);
        document.getElementById("prog-done").style.display = "";
        document.getElementById("run-btn").disabled        = false;
        bar.classList.remove("progress-bar-animated");
      }
    } catch (e) { /* reintenta */ }
  }, 500);
}
