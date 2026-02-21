/**
 * Page Data Mining
 */
const MiningPage = {
  pollInterval: null,

  render() {
    return `
      <div class="page-header">
        <h1>Data Mining</h1>
        <p>Analyses avancees : segmentation clients, detection d'anomalies, analyse RFM</p>
      </div>

      <div class="mining-controls">
        <button id="btn-run-all" class="btn btn-primary" onclick="MiningPage.run('all', false)">
          &#9654; Lancer toutes les analyses
        </button>
        <button id="btn-run-quick" class="btn btn-secondary" onclick="MiningPage.run('all', true)">
          &#9889; Mode rapide
        </button>
        <div class="analysis-buttons">
          <button class="btn btn-outline btn-sm" onclick="MiningPage.run('exploratory', false)">Exploratoire</button>
          <button class="btn btn-outline btn-sm" onclick="MiningPage.run('clustering', false)">Clustering</button>
          <button class="btn btn-outline btn-sm" onclick="MiningPage.run('anomaly', false)">Anomalies</button>
          <button class="btn btn-outline btn-sm" onclick="MiningPage.run('rfm', false)">RFM</button>
        </div>
        <span id="mining-status" class="status-badge status-idle">Pret</span>
      </div>

      <div class="chart-card">
        <h3>Console d'execution</h3>
        <div id="mining-terminal" class="terminal">En attente de lancement...\n\nCliquez sur "Lancer toutes les analyses" pour demarrer le Data Mining.\nLes resultats (clusters, anomalies, RFM) s'afficheront automatiquement.</div>
      </div>

      <div id="mining-results"></div>
    `;
  },

  async run(analysis, quick) {
    const btnRunAll = document.getElementById('btn-run-all');
    const btnRunQuick = document.getElementById('btn-run-quick');
    if (btnRunAll) btnRunAll.disabled = true;
    if (btnRunQuick) btnRunQuick.disabled = true;

    MiningPage.setStatus('running');
    document.getElementById('mining-results').innerHTML = '';

    const term = document.getElementById('mining-terminal');
    const label = analysis === 'all' ? 'Toutes les analyses' : analysis;
    const mode = quick ? 'Rapide (echantillon)' : 'Complet';
    term.textContent =
      'Data Mining en cours d\'execution...\n\n' +
      'Analyse  : ' + label + '\n' +
      'Mode     : ' + mode + '\n' +
      'Temps estime : ' + (quick ? '1-3 min' : '3-10 min') + '\n\n' +
      'Vous pouvez naviguer dans les autres sections en attendant.\n\n' +
      '--- Logs ---\n';

    try {
      await API.runMining(analysis, quick);
      MiningPage.startPolling();
    } catch (err) {
      MiningPage.setStatus('error');
      term.textContent = 'Erreur: ' + err.message;
      if (btnRunAll) btnRunAll.disabled = false;
      if (btnRunQuick) btnRunQuick.disabled = false;
    }
  },

  startPolling() {
    if (this.pollInterval) clearInterval(this.pollInterval);
    this.pollInterval = setInterval(async () => {
      try {
        const data = await API.getMiningStatus();
        const term = document.getElementById('mining-terminal');
        if (term && data.output) {
          term.textContent = data.output;
          term.scrollTop = term.scrollHeight;
        }
        if (!data.running) {
          clearInterval(MiningPage.pollInterval);
          MiningPage.pollInterval = null;
          MiningPage.setStatus(data.status);
          if (data.status === 'success') MiningPage.loadResults();
          const btnRunAll = document.getElementById('btn-run-all');
          const btnRunQuick = document.getElementById('btn-run-quick');
          if (btnRunAll) btnRunAll.disabled = false;
          if (btnRunQuick) btnRunQuick.disabled = false;
        }
      } catch (e) { /* ignore */ }
    }, 2000);
  },

  setStatus(status) {
    const el = document.getElementById('mining-status');
    if (!el) return;
    const labels = { idle: 'Pret', running: 'En cours...', success: 'Termine', error: 'Erreur' };
    el.textContent = labels[status] || status;
    el.className = `status-badge status-${status}`;
  },

  async loadResults() {
    const container = document.getElementById('mining-results');
    if (!container) return;

    let html = '';
    let hasResults = false;

    // --- Clustering ---
    try {
      const data = await API.getMiningClusters();
      if (data.clusters && data.clusters.length > 0) {
        hasResults = true;
        html += '<h3 style="margin:28px 0 16px;font-size:18px;font-weight:600;">Segmentation clients (K-Means)</h3>';
        html += '<div class="results-grid">';
        for (const c of data.clusters) {
          html += `
            <div class="result-card">
              <h4>Cluster ${c.cluster_id}</h4>
              <p style="font-weight:600;color:var(--info);margin-bottom:8px;">${MiningPage.esc(c.profile)}</p>
              <div class="summary-item"><strong>${c.n_customers}</strong> clients (${c.percentage.toFixed(1)}%)</div>
              <div class="summary-item">CA moyen : <strong>${c.avg_ca_total.toFixed(2)} EUR</strong></div>
              <div class="summary-item">Commandes moy. : <strong>${c.avg_nb_commandes.toFixed(1)}</strong></div>
            </div>`;
        }
        html += '</div>';
      }
    } catch (e) { /* pas de donnees clustering */ }

    // --- Anomalies ---
    try {
      const data = await API.getMiningAnomalies();
      if (data.n_anomalies != null) {
        hasResults = true;
        html += '<h3 style="margin:28px 0 16px;font-size:18px;font-weight:600;">Detection d\'anomalies (Isolation Forest)</h3>';
        html += '<div class="results-grid">';

        // Stats globales
        html += `
          <div class="result-card warning">
            <h4>Resume</h4>
            <div class="summary-item"><strong>${data.total_transactions}</strong> transactions analysees</div>
            <div class="summary-item"><strong>${data.n_anomalies}</strong> anomalies detectees (${data.anomaly_rate.toFixed(2)}%)</div>
            <div class="summary-item">CA moyen normal : <strong>${data.stats.avg_amount_normal.toFixed(2)} EUR</strong></div>
            <div class="summary-item">CA moyen anomalie : <strong>${data.stats.avg_amount_anomaly.toFixed(2)} EUR</strong></div>
          </div>`;

        // Types d'anomalies
        if (data.anomaly_types && data.anomaly_types.length > 0) {
          html += '<div class="result-card danger"><h4>Types d\'anomalies</h4>';
          for (const t of data.anomaly_types) {
            html += `<div class="summary-item"><strong>${MiningPage.esc(t.type)}</strong> : ${t.count} occurrences<br><small style="color:var(--text-secondary)">${MiningPage.esc(t.description)}</small></div>`;
          }
          html += '</div>';
        }

        // Top anomalies
        if (data.anomalies && data.anomalies.length > 0) {
          html += '<div class="result-card" style="grid-column:1/-1;"><h4>Top transactions anormales</h4>';
          html += '<table><thead><tr><th>Commande</th><th>Client</th><th>Montant</th><th>Pays</th><th>Score</th></tr></thead><tbody>';
          for (const a of data.anomalies.slice(0, 15)) {
            html += `<tr>
              <td>${MiningPage.esc(a.order_id)}</td>
              <td>${MiningPage.esc(a.customer_name)}</td>
              <td class="text-right">${a.sales_amount.toFixed(2)} EUR</td>
              <td>${MiningPage.esc(a.country)}</td>
              <td class="text-right">${a.anomaly_score.toFixed(3)}</td>
            </tr>`;
          }
          html += '</tbody></table></div>';
        }
        html += '</div>';
      }
    } catch (e) { /* pas de donnees anomalies */ }

    // --- RFM ---
    try {
      const data = await API.getMiningRFM();
      if (data.segments && data.segments.length > 0) {
        hasResults = true;
        html += '<h3 style="margin:28px 0 16px;font-size:18px;font-weight:600;">Segmentation RFM (Recence, Frequence, Montant)</h3>';
        html += '<div class="results-grid">';
        for (const s of data.segments) {
          const color = MiningPage.rfmColor(s.segment);
          html += `
            <div class="result-card ${color}">
              <h4>${MiningPage.esc(s.segment)}</h4>
              <div class="summary-item"><strong>${s.n_customers}</strong> clients (${s.percentage.toFixed(1)}%)</div>
              <div class="summary-item">CA moyen : <strong>${s.avg_monetary.toFixed(2)} EUR</strong></div>
              <div class="summary-item">Frequence moy. : <strong>${s.avg_frequency.toFixed(1)}</strong></div>
              <div class="summary-item">Recence moy. : <strong>${s.avg_recency.toFixed(0)} jours</strong></div>
            </div>`;
        }
        html += '</div>';

        // Recommandations RFM
        if (data.recommendations && data.recommendations.length > 0) {
          html += '<div class="table-card"><h3>Recommandations par segment</h3>';
          html += '<table><thead><tr><th>Segment</th><th>Clients</th><th>CA moyen</th><th>Action recommandee</th></tr></thead><tbody>';
          for (const r of data.recommendations) {
            html += `<tr>
              <td><strong>${MiningPage.esc(r.segment)}</strong></td>
              <td class="text-center">${r.n_customers}</td>
              <td class="text-right">${r.avg_monetary.toFixed(2)} EUR</td>
              <td>${MiningPage.esc(r.recommendation)}</td>
            </tr>`;
          }
          html += '</tbody></table></div>';
        }
      }
    } catch (e) { /* pas de donnees RFM */ }

    // --- Rapport HTML ---
    try {
      const report = await API.getMiningResults();
      if (report && report.report_path) {
        html += `
          <div class="chart-card" style="text-align:center;margin-top:24px;">
            <h3>Rapport complet</h3>
            <p style="color:var(--text-secondary);margin:12px 0;">Rapport HTML detaille genere par le Data Mining</p>
            <button class="btn btn-primary" onclick="window.open('${report.report_path}', '_blank')">
              Ouvrir le rapport complet
            </button>
          </div>`;
      }
    } catch (e) { /* pas de rapport */ }

    if (!hasResults) {
      html = '<div class="chart-card" style="text-align:center;padding:40px;margin-top:20px;"><p style="color:var(--text-secondary)">Aucun resultat disponible. Lancez une analyse pour generer des resultats.</p></div>';
    }

    container.innerHTML = html;
  },

  rfmColor(segment) {
    const map = {
      'Champions': 'success',
      'Clients fideles': 'success',
      'Clients potentiels': '',
      'Nouveaux clients': '',
      'Clients a risque': 'warning',
      'Clients perdus': 'danger',
    };
    return map[segment] || '';
  },

  esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  },

  destroy() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  },
};
