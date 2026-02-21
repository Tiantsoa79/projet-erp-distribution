/**
 * Page Pipeline ETL
 */
const PipelinePage = {
  pollInterval: null,

  render() {
    return `
      <div class="page-header">
        <h1>Pipeline ETL</h1>
        <p>Extraction des donnees ERP via API REST, transformation et chargement dans le Data Warehouse</p>
      </div>

      <div class="pipeline-controls">
        <button id="btn-run" class="btn btn-success" onclick="PipelinePage.run(false)">
          &#9654; Lancer le pipeline
        </button>
        <button id="btn-force" class="btn btn-secondary" onclick="PipelinePage.run(true)">
          &#8635; Forcer le rechargement
        </button>
        <span id="pipeline-status" class="status-badge status-idle">Pret</span>
      </div>

      <div class="results-grid" style="grid-template-columns:1fr 1fr;">
        <div class="result-card success">
          <h4>Mode intelligent</h4>
          <p style="color:var(--text-secondary);font-size:13px;line-height:1.7;">
            Le pipeline detecte automatiquement les changements dans les donnees source.
            S'il n'y a aucune modification, les etapes de transformation et chargement
            sont ignorees pour gagner du temps. Utilisez <strong>Forcer</strong> pour
            tout recharger malgre l'absence de changement.
          </p>
        </div>
        <div class="result-card">
          <h4>Flux ETL</h4>
          <div style="font-size:13px;line-height:2.2;color:var(--text-secondary);">
            <div style="display:flex;flex-direction:column;align-items:center;gap:2px;">
              <span style="background:#dcfce7;padding:4px 14px;border-radius:6px;color:#166534;font-weight:600;">1. Extract (API ERP REST)</span>
              <span style="color:var(--text-secondary);">&#8595;</span>
              <span style="background:#dbeafe;padding:4px 14px;border-radius:6px;color:#1e40af;font-weight:600;">2. Transform (nettoyage, conformation)</span>
              <span style="color:var(--text-secondary);">&#8595;</span>
              <span style="background:#f3e8ff;padding:4px 14px;border-radius:6px;color:#7e22ce;font-weight:600;">3. Load (dimensions + faits DWH)</span>
              <span style="color:var(--text-secondary);">&#8595;</span>
              <span style="background:#fef3c7;padding:4px 14px;border-radius:6px;color:#92400e;font-weight:600;">4. Analyse + Rapport</span>
            </div>
          </div>
        </div>
      </div>

      <div class="chart-card">
        <h3>Console d'execution</h3>
        <div id="pipeline-terminal" class="terminal">En attente de lancement...\n\nCliquez sur "Lancer le pipeline" pour demarrer le processus ETL.\nLe pipeline se connecte a l'API ERP, extrait les donnees, les transforme et les charge dans le Data Warehouse.</div>
      </div>
    `;
  },

  async run(force) {
    const btnRun = document.getElementById('btn-run');
    const btnForce = document.getElementById('btn-force');
    btnRun.disabled = true;
    btnForce.disabled = true;
    PipelinePage.setStatus('running');

    const term = document.getElementById('pipeline-terminal');
    term.textContent =
      'Pipeline ETL en cours d\'execution...\n\n' +
      'Le processus effectue les operations suivantes :\n' +
      '  1. Authentification aupres du gateway ERP (JWT)\n' +
      '  2. Extraction des donnees (clients, produits, commandes, fournisseurs)\n' +
      '  3. Detection des changements (checksums MD5)\n' +
      '  4. Transformation et nettoyage des donnees\n' +
      '  5. Chargement dans le Data Warehouse (schema etoile)\n' +
      '  6. Generation du rapport analytique\n\n' +
      'Temps estime : 1-3 minutes\n' +
      'Vous pouvez naviguer dans les autres sections pendant l\'execution.\n\n' +
      '--- Logs du pipeline ---\n';

    try {
      await API.runPipeline(force);
      PipelinePage.startPolling();
    } catch (err) {
      PipelinePage.setStatus('error');
      term.textContent = 'Erreur: ' + err.message;
      btnRun.disabled = false;
      btnForce.disabled = false;
    }
  },

  startPolling() {
    if (this.pollInterval) clearInterval(this.pollInterval);
    this.pollInterval = setInterval(async () => {
      try {
        const data = await API.getPipelineStatus();
        const term = document.getElementById('pipeline-terminal');
        if (term && data.output) {
          term.textContent = data.output;
          term.scrollTop = term.scrollHeight;
        }
        if (!data.running) {
          clearInterval(PipelinePage.pollInterval);
          PipelinePage.pollInterval = null;
          PipelinePage.setStatus(data.status);
          const btnRun = document.getElementById('btn-run');
          const btnForce = document.getElementById('btn-force');
          if (btnRun) btnRun.disabled = false;
          if (btnForce) btnForce.disabled = false;
        }
      } catch (e) { /* ignore polling errors */ }
    }, 1500);
  },

  setStatus(status) {
    const el = document.getElementById('pipeline-status');
    if (!el) return;
    const labels = { idle: 'Pret', running: 'En cours...', success: 'Termine', error: 'Erreur' };
    el.textContent = labels[status] || status;
    el.className = `status-badge status-${status}`;
  },

  destroy() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  },
};
